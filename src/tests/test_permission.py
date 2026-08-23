"""PyCasbin 权限策略单测：验证最小权限矩阵（离线运行，不依赖任何外部服务）。"""

from src.mcp_gateway.permission import check_tool_permission

# (角色, 工具, 是否允许) 期望矩阵——与 policy.csv 一一对应
EXPECTED = [
    # 调度Agent：零业务工具权限
    ("agent-dispatcher", "query_inventory", False),
    ("agent-dispatcher", "create_purchase_order", False),
    # 查询Agent：仅只读
    ("agent-query", "query_inventory", True),
    ("agent-query", "query_patient", True),
    ("agent-query", "query_approval_status", True),
    ("agent-query", "create_purchase_order", False),      # 只读角色禁止写工具
    ("agent-query", "start_purchase_approval", False),
    # 审批Agent：仅审批类
    ("agent-approval", "start_purchase_approval", True),
    ("agent-approval", "query_approval_status", True),
    ("agent-approval", "create_purchase_order", False),   # 审批角色禁止直接写入
    ("agent-approval", "query_inventory", False),
    # 操作Agent：写工具 + 只读
    ("agent-operator", "create_purchase_order", True),
    ("agent-operator", "dispense_prescription", True),
    ("agent-operator", "query_inventory", True),
    # 未知角色：全部拒绝
    ("agent-unknown", "query_inventory", False),
    ("", "query_inventory", False),
]


def test_permission_matrix() -> None:
    """逐条校验角色-工具权限矩阵。"""
    for role, tool, expected in EXPECTED:
        assert check_tool_permission(role, tool) is expected, (
            f"权限策略不符: {role} x {tool} 期望 {'允许' if expected else '拒绝'}"
        )
