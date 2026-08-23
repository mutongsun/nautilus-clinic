"""网关拦截管道单测：权限拒绝 / BPM 未批准 / 缺少审批凭证（核心安全语义，全部 mock 离线运行）。"""

from typing import Any

import pytest

import src.mcp_gateway.decorator as decorator_mod
import src.mcp_gateway.tools  # noqa: F401 —— 触发工具注册
from src.common.exceptions import BPMNotApprovedError, BPMPendingError, ToolPermissionDenied
from src.mcp_gateway.audit import AuditRecorder
from src.mcp_gateway.registry import TOOL_REGISTRY

# 有效调用上下文（operator 角色 + 高风险场景）
_CTX_OPERATOR = {
    "user_id": "u-test",
    "agent_role": "agent-operator",
    "trace_id": "trace-test01",
    "user_instruction": "测试创建采购订单",
}


@pytest.fixture()
def audit_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """捕获审计调用（替换 DB/日志双写，仅记录参数）。"""
    calls: list[dict[str, Any]] = []

    async def fake_record(self: AuditRecorder, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(AuditRecorder, "record", fake_record)
    return calls


async def _call_create_order(context: dict, params: dict | None = None) -> dict:
    """直接调用注册表中的 create_purchase_order 包装函数。"""
    _, fn = TOOL_REGISTRY["create_purchase_order"]
    return await fn(params or {"supplier": "测试供应商", "items": [{"medicine_name": "阿莫西林胶囊", "quantity": 10}]}, context)


async def test_permission_denied_and_audited(monkeypatch: pytest.MonkeyPatch, audit_calls: list) -> None:
    """查询角色调用高风险写工具：必须拒绝且留 PERMISSION_DENIED 审计。"""
    monkeypatch.setattr(decorator_mod, "check_tool_permission", lambda *a, **k: False)
    ctx = dict(_CTX_OPERATOR, agent_role="agent-query")

    with pytest.raises(ToolPermissionDenied):
        await _call_create_order(ctx)

    assert len(audit_calls) == 1
    assert audit_calls[0]["status"] == "PERMISSION_DENIED"
    assert audit_calls[0]["tool_name"] == "create_purchase_order"


async def test_high_risk_without_workflow_id_rejected(monkeypatch: pytest.MonkeyPatch, audit_calls: list) -> None:
    """高风险工具缺少 bpm_workflow_id：直接拒绝（防止幻觉伪造已审批上下文）。"""
    monkeypatch.setattr(decorator_mod, "check_tool_permission", lambda *a, **k: True)

    with pytest.raises(BPMNotApprovedError):
        await _call_create_order(dict(_CTX_OPERATOR, bpm_workflow_id=None))

    assert audit_calls[0]["status"] == "BPM_NOT_APPROVED"


async def test_high_risk_pending_approval_blocked(monkeypatch: pytest.MonkeyPatch, audit_calls: list) -> None:
    """审批仍在人工处理中（PENDING）：必须拦截并提示等待。"""
    monkeypatch.setattr(decorator_mod, "check_tool_permission", lambda *a, **k: True)

    async def fake_bpm(_wid: str) -> str:
        return "PENDING"

    monkeypatch.setattr(decorator_mod, "_bpm_is_approved", fake_bpm)

    with pytest.raises(BPMPendingError):
        await _call_create_order(dict(_CTX_OPERATOR, bpm_workflow_id="wf-pending-001"))

    assert audit_calls[0]["status"] == "BPM_PENDING"


async def test_high_risk_rejected_approval_blocked(monkeypatch: pytest.MonkeyPatch, audit_calls: list) -> None:
    """审批被驳回（REJECTED/UNKNOWN）：必须拦截。"""
    monkeypatch.setattr(decorator_mod, "check_tool_permission", lambda *a, **k: True)

    async def fake_bpm(_wid: str) -> str:
        return "REJECTED"

    monkeypatch.setattr(decorator_mod, "_bpm_is_approved", fake_bpm)

    with pytest.raises(BPMNotApprovedError):
        await _call_create_order(dict(_CTX_OPERATOR, bpm_workflow_id="wf-rejected-001"))


async def test_invalid_context_rejected(monkeypatch: pytest.MonkeyPatch, audit_calls: list) -> None:
    """上下文缺少必填字段：参数校验拒绝。"""
    from src.common.exceptions import ParamValidationError

    monkeypatch.setattr(decorator_mod, "check_tool_permission", lambda *a, **k: True)
    with pytest.raises(ParamValidationError):
        await _call_create_order({"user_id": "", "agent_role": "", "trace_id": ""})
