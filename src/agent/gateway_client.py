"""Agent 侧 MCP 网关客户端：统一携带 ToolContext 调用网关工具。

Agent 层禁止直连业务系统（开发规范红线 #5），全部工具调用必须经由本客户端走 MCP 协议。
写操作自动生成幂等键（trace_id+工具+参数指纹）：重试/重复点击安全，网关据此防重。
"""

import hashlib
import json
from typing import Any

from fastmcp import Client

from src.agent.state import AgentState
from src.common.constants import AgentRole, ToolRiskLevel
from src.common.logging import get_logger
from src.config.settings import get_settings
from src.mcp_gateway.registry import TOOL_REGISTRY
from src.mcp_gateway.schemas import ToolContext

logger = get_logger(__name__)


class GatewayClient:
    """MCP 网关客户端（每次调用独立建连，骨架阶段足够；规模化演进为连接池）。"""

    def __init__(self, gateway_url: str | None = None) -> None:
        self._url = gateway_url or get_settings().mcp_gateway_url

    @staticmethod
    def make_idempotency_key(trace_id: str, tool_name: str, params: dict[str, Any]) -> str:
        """生成写操作幂等键：trace_id + 工具名 + 参数指纹。

        同一链路内同参数重试命中同一键（安全复用）；不同链路/参数互不影响。
        """
        digest = hashlib.sha256(
            json.dumps(params, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
        return f"{trace_id}:{tool_name}:{digest}"[:160]

    async def call(
        self,
        state: AgentState,
        role: AgentRole,
        tool_name: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """调用网关工具。

        Args:
            state: 当前协作状态（提取用户/链路信息组装上下文）。
            role: 发起调用的子Agent角色（网关据此鉴权）。
            tool_name: 工具名。
            params: 工具入参（原始 dict，网关侧 pydantic 强校验）。

        Returns:
            工具返回的结构化结果。

        Raises:
            Exception: 网关拒绝（权限/BPM/校验）或下游异常，错误码前缀见 common.exceptions。
        """
        # 写操作自动携带幂等键（网关侧同键成功记录直接复用，防重复下单/重复审批）
        idem_key = None
        try:
            import src.mcp_gateway.tools  # noqa: F401 —— 导入触发注册（与网关同代码）

            spec, _ = TOOL_REGISTRY.get(tool_name, (None, None))
            if spec is not None and spec.risk_level is not ToolRiskLevel.LOW:
                idem_key = self.make_idempotency_key(state["trace_id"], tool_name, params)
        except Exception:  # noqa: BLE001 —— 注册表读取失败不阻断调用
            pass

        # P2 用户角色断言（服务端强制第二道防线：即使计划被绕过，角色不符也拒绝调用）
        user_role = state.get("user_role")
        if user_role:
            from src.common.constants import USER_ROLE_ALLOWED_AGENTS
            from src.common.exceptions import ToolPermissionDenied

            if role.value not in USER_ROLE_ALLOWED_AGENTS.get(user_role, frozenset()):
                logger.warning(
                    "角色越权拦截: user_role=%s 尝试以 %s 调用 %s",
                    user_role, role.value, tool_name,
                )
                raise ToolPermissionDenied(
                    f"用户角色 {user_role} 无权以 {role.value} 执行 {tool_name}"
                )

        context = ToolContext(
            user_id=state["user_id"],
            agent_role=role.value,
            trace_id=state["trace_id"],
            user_instruction=state["user_instruction"],
            bpm_workflow_id=state.get("pending_workflow_id"),
            idempotency_key=idem_key,
            client_ip=state.get("client_ip"),
        )
        async with Client(self._url) as client:
            result = await client.call_tool(
                tool_name, {"params": params, "context": context.model_dump()}
            )
            return self._parse_result(result)

    @staticmethod
    def _parse_result(result: Any) -> dict[str, Any]:
        """兼容解析 fastmcp 各版本 call_tool 返回形态。

        - CallToolResult 对象：优先取结构化输出 .data；
        - 直接返回 content 列表的版本：逐项取 .text 并尝试 JSON 反序列化。
        """
        data = getattr(result, "data", None)
        if isinstance(data, dict):
            return data
        content = getattr(result, "content", result)
        if isinstance(content, list):
            texts = [getattr(c, "text", str(c)) for c in content]
            for text in texts:  # 工具返回 dict 时服务端序列化为 JSON 文本
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except (TypeError, ValueError):
                    continue
            return {"raw": texts}
        return {"raw": [str(content)]}


_gateway_client: GatewayClient | None = None


def get_gateway_client() -> GatewayClient:
    """获取网关客户端单例。"""
    global _gateway_client
    if _gateway_client is None:
        _gateway_client = GatewayClient()
    return _gateway_client
