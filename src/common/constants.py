"""全局常量定义：工具风险等级、Agent 角色、审计状态、工具动作。

所有跨模块共享的常量必须收敛到本文件，禁止在各业务模块内散落定义魔法值。
"""

from enum import Enum


class ToolRiskLevel(str, Enum):
    """MCP 工具风险等级。

    LOW    : 只读查询，无副作用，网关权限校验后直接执行；
    MEDIUM : 可逆写操作（状态流转、发起审批等），需审计且可回滚；
    HIGH   : 不可逆 / 资金 / 库存 / 处方类写入，强制 Conductor BPM 人工审批通过后方可执行。
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# 兼容常量风格引用（文档与代码示例统一使用）
TOOL_RISK_LOW = ToolRiskLevel.LOW
TOOL_RISK_MEDIUM = ToolRiskLevel.MEDIUM
TOOL_RISK_HIGH = ToolRiskLevel.HIGH


class AgentRole(str, Enum):
    """智能体角色（同时作为 PyCasbin 权限主体与审计中的 agent_id）。"""

    DISPATCHER = "agent-dispatcher"   # 意图调度 Agent（总控，无业务工具权限）
    QUERY = "agent-query"             # 业务查询 Agent（仅只读工具）
    APPROVAL = "agent-approval"       # 业务审批 Agent（仅审批类工具）
    OPERATOR = "agent-operator"       # 业务操作 Agent（写工具，强制 BPM 校验）


class AuditStatus(str, Enum):
    """工具调用审计结果状态。"""

    SUCCESS = "SUCCESS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    BPM_NOT_APPROVED = "BPM_NOT_APPROVED"
    BPM_PENDING = "BPM_PENDING"
    BIZ_ERROR = "BIZ_ERROR"
    TIMEOUT = "TIMEOUT"


# ==================== 用户角色与 Agent 角色映射（P2 权限落地） ====================
# 用户角色（auth_user.role）-> 允许扮演的 Agent 角色集合（服务端强制，客户端不可伪造）
# admin: 全部业务Agent / purchaser: 查询+审批+操作 / viewer: 仅只读查询

USER_ROLE_ALLOWED_AGENTS: dict[str, frozenset[str]] = {
    "admin": frozenset({
        AgentRole.QUERY.value,
        AgentRole.APPROVAL.value,
        AgentRole.OPERATOR.value,
    }),
    "purchaser": frozenset({
        AgentRole.QUERY.value,
        AgentRole.APPROVAL.value,
        AgentRole.OPERATOR.value,
    }),
    "viewer": frozenset({AgentRole.QUERY.value}),
}

# 初始种子账号（首次启动自动创建，生产环境必须立即改密）
SEED_USERS: list[tuple[str, str, str]] = [
    ("admin", "Admin@123", "admin"),
    ("purchaser", "Purchase@123", "purchaser"),
    ("viewer", "Viewer@123", "viewer"),
]


# Casbin 权限模型中的工具动作（当前所有工具统一为 invoke）
TOOL_ACTION_INVOKE = "invoke"

# 审计输出截断上限（字符），防止超大结果拖垮日志与审计表
AUDIT_OUTPUT_TRUNCATE = 4000
