"""MCP 工具注册表：集中管理工具元数据（风险等级 / 角色约束 / BPM 要求）。"""

from dataclasses import dataclass
from typing import Awaitable, Callable

from src.common.constants import ToolRiskLevel


@dataclass(frozen=True)
class ToolSpec:
    """工具规格元数据（注册时声明，运行时强制校验）。"""

    name: str
    description: str
    risk_level: ToolRiskLevel
    required_roles: frozenset[str]        # 声明式角色约束（文档化；强制校验以 Casbin 策略为准）
    bpm_required: bool = False            # 高风险写操作是否强制 BPM 审批


# 包装后的工具函数签名统一为 (params: dict, context: dict) -> dict
ToolFunc = Callable[[dict, dict], Awaitable[dict]]

# 工具注册表：name -> (ToolSpec, wrapped_fn)
TOOL_REGISTRY: dict[str, tuple[ToolSpec, ToolFunc]] = {}


def register_tool(spec: ToolSpec, fn: ToolFunc) -> None:
    """注册工具到全局注册表（重名将直接抛错，防止误覆盖）。"""
    if spec.name in TOOL_REGISTRY:
        raise ValueError(f"工具重复注册: {spec.name}")
    TOOL_REGISTRY[spec.name] = (spec, fn)


def get_registered_tools() -> dict[str, tuple[ToolSpec, ToolFunc]]:
    """获取全部已注册工具（服务端启动时统一挂载到 FastMCP）。"""
    return dict(TOOL_REGISTRY)
