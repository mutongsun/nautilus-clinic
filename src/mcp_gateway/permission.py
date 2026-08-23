"""PyCasbin 权限治理：Agent 角色对 MCP 工具的最小权限校验。

策略文件位于本包 policy/ 目录（model.conf + policy.csv），随代码一同发布。
权限模型：RBAC（角色 -> 工具 -> 动作），动作统一为 invoke，通配 * 表示全部动作。
"""

import os
from functools import lru_cache
from pathlib import Path

import casbin

from src.common.logging import get_logger

logger = get_logger(__name__)

# 策略文件默认随包发布，支持环境变量覆盖（NAUTILUS_CASBIN_MODEL / NAUTILUS_CASBIN_POLICY）
_POLICY_DIR = Path(__file__).parent / "policy"
_DEFAULT_MODEL = _POLICY_DIR / "model.conf"
_DEFAULT_POLICY = _POLICY_DIR / "policy.csv"


@lru_cache
def get_enforcer() -> casbin.Enforcer:
    """加载 Casbin 执行器（进程内单例）。

    Raises:
        FileNotFoundError: 策略文件缺失。
    """
    model_path = os.getenv("NAUTILUS_CASBIN_MODEL", str(_DEFAULT_MODEL))
    policy_path = os.getenv("NAUTILUS_CASBIN_POLICY", str(_DEFAULT_POLICY))
    enforcer = casbin.Enforcer(model_path, policy_path)
    logger.info("Casbin 权限策略已加载", extra={"model": model_path, "policy": policy_path})
    return enforcer


def check_tool_permission(agent_role: str, tool_name: str, action: str = "invoke") -> bool:
    """校验 Agent 角色是否具备工具调用权限。

    Args:
        agent_role: Agent 角色标识（如 agent-query）。
        tool_name: 工具名（如 query_inventory）。
        action: 动作，默认 invoke。

    Returns:
        True 允许调用；False 拒绝（审计记为 PERMISSION_DENIED）。
    """
    return bool(get_enforcer().enforce(agent_role, tool_name, action))


def reload_policy() -> None:
    """热加载策略文件（策略调整后无需重启网关）。"""
    get_enforcer().load_policy()
