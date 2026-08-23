"""Redis 存储：会话历史外置 + 异步任务状态（P2：进程重启不丢，多实例演进基础）。"""

import json
from typing import Any

from src.common.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)

_pool: Any = None
_TASK_TTL = 3600          # 异步任务结果保留 1 小时
_SESSION_TTL = 7 * 86400  # 会话历史保留 7 天
_SESSION_MAX = 20         # 每用户保留最近 20 条消息


def _redis() -> Any:
    """获取 Redis 连接池（懒加载单例，decode_responses 直接收 str）。"""
    global _pool
    if _pool is None:
        import redis.asyncio as aioredis

        _pool = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    return _pool


# ==================== 会话历史 ====================

async def append_session(username: str, role: str, content: str) -> None:
    """追加一条会话消息（Redis List，超出上限裁剪旧消息）。"""
    try:
        key = f"session:{username}"
        entry = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        r = _redis()
        await r.rpush(key, entry)
        await r.ltrim(key, -_SESSION_MAX, -1)
        await r.expire(key, _SESSION_TTL)
    except Exception:  # noqa: BLE001 —— 会话存储故障不阻断对话主流程
        logger.exception("会话写入失败（不影响本次对话）: user=%s", username)


async def get_session(username: str) -> list[dict[str, str]]:
    """读取用户最近会话历史（旧->新）。"""
    try:
        raw = await _redis().lrange(f"session:{username}", 0, -1)
        return [json.loads(x) for x in raw]
    except Exception:  # noqa: BLE001
        logger.exception("会话读取失败: user=%s", username)
        return []


# ==================== 异步任务 ====================

async def create_task(task_id: str) -> None:
    """创建任务记录（PENDING 状态）。"""
    await _write_task(task_id, {"status": "PENDING", "created": True})


async def set_task(task_id: str, data: dict[str, Any]) -> None:
    """更新任务状态（RUNNING / 终态 OK|PARTIAL|FAILED）。"""
    await _write_task(task_id, data)


async def get_task(task_id: str) -> dict[str, Any] | None:
    """查询任务（不存在返回 None）。"""
    try:
        raw = await _redis().get(f"task:{task_id}")
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        logger.exception("任务查询失败: task=%s", task_id)
        return None


async def _write_task(task_id: str, data: dict[str, Any]) -> None:
    """任务写入（失败仅告警：任务丢失可由前端超时兜底，不阻断服务）。"""
    try:
        await _redis().set(f"task:{task_id}", json.dumps(data, ensure_ascii=False), ex=_TASK_TTL)
    except Exception:  # noqa: BLE001
        logger.exception("任务状态写入失败: task=%s", task_id)
