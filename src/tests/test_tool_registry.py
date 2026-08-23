"""工具注册表规范单测：风险等级标注 / BPM 强制声明 / 角色约束完整性（评审红线 2）。"""

import pytest

import src.mcp_gateway.tools  # noqa: F401 —— 导入即触发注册
from src.common.constants import ToolRiskLevel
from src.mcp_gateway.registry import TOOL_REGISTRY


def test_all_tools_declare_risk_level() -> None:
    """所有工具必须标注合法风险等级。"""
    assert TOOL_REGISTRY, "工具注册表为空：tools.py 未被正确导入"
    for name, (spec, _) in TOOL_REGISTRY.items():
        assert isinstance(spec.risk_level, ToolRiskLevel), f"{name} 风险等级非法"


def test_high_risk_tools_require_bpm() -> None:
    """高风险工具必须声明 bpm_required=True（一票否决项）。"""
    for name, (spec, _) in TOOL_REGISTRY.items():
        if spec.risk_level is ToolRiskLevel.HIGH:
            assert spec.bpm_required, f"高风险工具 {name} 未声明 bpm_required"


def test_every_tool_has_required_roles() -> None:
    """所有工具必须声明允许角色（最小权限文档化）。"""
    for name, (spec, _) in TOOL_REGISTRY.items():
        assert spec.required_roles, f"工具 {name} 未声明 required_roles"


def test_tool_names_unique() -> None:
    """工具名唯一（register_tool 重复注册会抛错，此处验证注册表一致性）。"""
    names = [spec.name for spec, _ in TOOL_REGISTRY.values()]
    assert len(names) == len(set(names))


def test_readonly_and_write_tools_both_exist() -> None:
    """注册表同时覆盖只读与写工具（安全分级的完整性）。"""
    risks = {spec.risk_level for spec, _ in TOOL_REGISTRY.values()}
    assert ToolRiskLevel.LOW in risks
    assert ToolRiskLevel.HIGH in risks
    assert ToolRiskLevel.MEDIUM in risks


@pytest.mark.parametrize("tool_name", ["query_inventory", "create_purchase_order"])
def test_wrapper_signature_registerable(tool_name: str) -> None:
    """注册表中工具为可调用包装函数。"""
    _, fn = TOOL_REGISTRY[tool_name]
    assert callable(fn)
