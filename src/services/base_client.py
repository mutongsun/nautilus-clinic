"""外部系统 HTTP 客户端基类：统一超时、重试、熔断、异常转译（外部请求四件套，校验在调用侧 pydantic 完成）。

所有对接外部系统（诊所 / ERP / Conductor / LLM）的客户端必须继承本类，
禁止在业务代码中直接裸调 httpx / requests。

熔断器（企业级稳定性，防止下游 HIS/ERP 故障拖垮全链路）：
    CLOSED（正常）→ 连续失败达阈值 → OPEN（快速失败，不再发请求）
    OPEN → 冷却时长到达 → HALF_OPEN（放行一次探测）
    HALF_OPEN → 探测成功 → CLOSED / 探测失败 → OPEN
"""

import time
from enum import Enum
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.common.exceptions import BizClientError, BizSystemUnavailable
from src.common.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class _BreakerState(str, Enum):
    """熔断器三态。"""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class _CircuitBreaker:
    """轻量熔断器（每下游客户端一个实例，进程内生效；分布式场景演进为 Redis 计数）。

    Args:
        name: 下游系统名（日志定位用）。
        failure_threshold: 连续失败多少次触发熔断。
        recovery_seconds: 熔断冷却时长，到期后半开探测。
    """

    def __init__(self, name: str, failure_threshold: int, recovery_seconds: float) -> None:
        self._name = name
        self._threshold = failure_threshold
        self._recovery = recovery_seconds
        self._state = _BreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    def check(self) -> None:
        """请求前检查：OPEN 且未到冷却期则快速失败（保护下游也保护自身线程）。"""
        if self._state is _BreakerState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._recovery:
                self._state = _BreakerState.HALF_OPEN
                logger.warning(
                    "熔断器半开探测: downstream=%s 冷却%.0fs已到", self._name, elapsed
                )
            else:
                raise BizSystemUnavailable(
                    f"下游 {self._name} 熔断中（冷却剩余 {self._recovery - elapsed:.0f}s），快速失败"
                )

    def record_success(self) -> None:
        """请求成功：复位闭合。"""
        if self._state is not _BreakerState.CLOSED:
            logger.info("熔断器恢复闭合: downstream=%s", self._name)
        self._state = _BreakerState.CLOSED
        self._failures = 0

    def record_failure(self) -> None:
        """请求失败：累计失败数，达阈值开闸熔断。"""
        self._failures += 1
        if self._state is _BreakerState.HALF_OPEN or self._failures >= self._threshold:
            self._state = _BreakerState.OPEN
            self._opened_at = time.monotonic()
            logger.error(
                "熔断器打开: downstream=%s 连续失败=%d 冷却=%.0fs",
                self._name, self._failures, self._recovery,
            )


class BaseHttpClient:
    """带超时 / 有限重试 / 异常转译的异步 HTTP 客户端基类。

    Args:
        base_url: 目标系统基础地址（容器内一律使用容器名，见 Docker 规范 5.1）。
        timeout: 单次请求超时秒数。
        retry_attempts: 传输类失败最大尝试次数（含首次）。
        headers: 附加请求头（如鉴权 Token）。
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        retry_attempts: int = 3,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._retry_attempts = retry_attempts
        settings = get_settings()
        self._breaker = _CircuitBreaker(
            name=base_url,
            failure_threshold=settings.breaker_failure_threshold,
            recovery_seconds=settings.breaker_recovery_seconds,
        )
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=headers or {},
        )

    async def aclose(self) -> None:
        """释放底层连接池（服务停机时调用）。"""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> Any:
        """执行带重试的 HTTP 请求并返回解析后的 JSON。

        - 传输层异常（连接失败 / 超时）：指数退避重试，最终失败转译为 BizSystemUnavailable；
        - 5xx：同样进入重试（视为下游瞬时不可用）；
        - 4xx：不重试，转译为 BizClientError（业务侧问题）。

        Raises:
            BizSystemUnavailable: 下游不可用 / 超时 / 5xx / 熔断中。
            BizClientError: 下游返回 4xx 业务错误。
        """
        self._breaker.check()  # 熔断检查：OPEN 期直接快速失败，不打下游

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._retry_attempts),
            wait=wait_exponential(multiplier=0.5),
            retry=retry_if_exception_type(BizSystemUnavailable),
            reraise=True,
        ):
            with attempt:
                try:
                    resp = await self._client.request(method, path, params=params, json=json_body)
                    self._breaker.record_success()
                except httpx.TimeoutException as exc:
                    self._breaker.record_failure()
                    raise BizSystemUnavailable(f"下游超时: {method} {path}") from exc
                except httpx.TransportError as exc:
                    self._breaker.record_failure()
                    raise BizSystemUnavailable(f"下游连接失败: {method} {path}") from exc
                if resp.status_code >= 500:
                    self._breaker.record_failure()
                    raise BizSystemUnavailable(f"下游服务异常 {resp.status_code}: {method} {path}")
                if resp.status_code >= 400:
                    # 4xx 是业务约定问题，不算下游故障，不计入熔断
                    raise BizClientError(
                        f"下游业务错误 {resp.status_code}: {method} {path} {resp.text[:500]}"
                    )
                if not resp.content:
                    return None
                try:
                    return resp.json()
                except ValueError:
                    # 部分管理接口（如 Conductor 元数据注册）返回纯文本，原样透出
                    return resp.text
        # 理论不可达（reraise=True 保证异常向上抛出）
        raise BizSystemUnavailable(f"请求失败: {method} {path}")
