"""企业级稳定性单测：幂等防重、熔断器、fastmcp 返回兼容解析（全部离线 mock）。"""

from typing import Any

import httpx
import pytest

import src.mcp_gateway.tools  # noqa: F401 —— 触发工具注册
from src.agent.gateway_client import GatewayClient
from src.common.exceptions import BizSystemUnavailable
from src.mcp_gateway.audit import AuditRecorder
from src.mcp_gateway.registry import TOOL_REGISTRY


# ==================== 幂等防重 ====================

_CTX = {
    "user_id": "u-test",
    "agent_role": "agent-operator",
    "trace_id": "trace-idem-01",
    "user_instruction": "幂等测试",
    "idempotency_key": "trace-idem-01:create_purchase_order:abc123",
}

_PARAMS = {"supplier": "测试供应商", "items": [{"medicine_name": "阿莫西林胶囊", "quantity": 8}]}


@pytest.fixture()
def audit_spy(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """审计记录 spy：捕获调用参数。"""
    calls: dict[str, Any] = {"records": []}

    async def fake_record(self: AuditRecorder, **kwargs: Any) -> None:
        calls["records"].append(kwargs)

    monkeypatch.setattr(AuditRecorder, "record", fake_record)
    return calls


async def test_idempotent_hit_reuses_cached_result(
    monkeypatch: pytest.MonkeyPatch, audit_spy: dict
) -> None:
    """同幂等键已有成功记录：直接复用结果，不再执行写操作（防重复下单）。"""

    async def fake_find(self: AuditRecorder, key: str, tool: str) -> dict | None:
        return {"tool_output": {"order_id": "PO-EXIST-001"}, "business_id": "PO-EXIST-001"}

    monkeypatch.setattr(AuditRecorder, "find_success_by_idempotency_key", fake_find)

    executed = []

    async def fake_downstream_order(params: dict, ctx: Any) -> dict:
        executed.append(1)  # 若幂等生效，此函数不应被执行
        return {"order_id": "PO-NEW"}

    _, fn = TOOL_REGISTRY["create_purchase_order"]
    # 直接替换底层诊所客户端调用（绕过 BPM 校验干扰：预先放行）
    monkeypatch.setattr(
        "src.mcp_gateway.decorator._bpm_is_approved", lambda wid: _async_ok()
    )
    # 注意 patch tools 命名空间（from-import 绑定），patch 源模块不生效
    monkeypatch.setattr(
        "src.mcp_gateway.tools.get_clinic_client", lambda: _FakeClinic(fake_downstream_order)
    )

    result = await fn(_PARAMS, dict(_CTX, bpm_workflow_id="wf-ok"))
    assert result["order_id"] == "PO-EXIST-001"       # 复用历史结果
    assert executed == []                              # 未真正下单
    assert audit_spy["records"][-1]["status"] == "SUCCESS_IDEMPOTENT_HIT"


async def test_idempotent_miss_executes_normally(monkeypatch: pytest.MonkeyPatch) -> None:
    """幂等键未命中：正常执行写操作（首单不受影响）。"""

    async def fake_find(self: AuditRecorder, key: str, tool: str) -> dict | None:
        return None

    monkeypatch.setattr(AuditRecorder, "find_success_by_idempotency_key", fake_find)
    monkeypatch.setattr("src.mcp_gateway.decorator._bpm_is_approved", lambda wid: _async_ok())

    async def fake_order(params: dict, ctx: Any) -> dict:
        return {"order_id": "PO-FIRST"}

    monkeypatch.setattr(
        "src.mcp_gateway.tools.get_clinic_client", lambda: _FakeClinic(fake_order)
    )

    _, fn = TOOL_REGISTRY["create_purchase_order"]
    result = await fn(_PARAMS, dict(_CTX, bpm_workflow_id="wf-ok"))
    assert result["order_id"] == "PO-FIRST"


async def _async_ok() -> str:
    """BPM 已批准桩。"""
    return "APPROVED"


class _FakeClinic:
    """诊所客户端桩：仅实现 create_purchase_order（返回类型与真实客户端一致）。"""

    def __init__(self, order_fn: Any) -> None:
        self._order_fn = order_fn

    async def create_purchase_order(self, order: Any) -> Any:
        from src.services.clinic_client import OrderResult

        data = await self._order_fn(order.model_dump(), None)
        return OrderResult.model_validate(data)


# ==================== 熔断器 ====================

async def test_circuit_breaker_opens_after_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """连续失败达阈值 → 熔断打开 → 后续请求快速失败（不再打下游）。"""
    from src.services.base_client import BaseHttpClient

    client = BaseHttpClient(base_url="http://fake-downstream", retry_attempts=1)
    client._breaker._threshold = 2  # 测试缩短阈值
    client._breaker._recovery = 60.0

    downstream_calls = []

    async def fail_request(*_a: Any, **_k: Any) -> httpx.Response:
        downstream_calls.append(1)
        raise httpx.ConnectError("downstream down")

    monkeypatch.setattr(client._client, "request", fail_request)

    # 前两次：真实尝试并失败（各 1 次重试已关闭）
    for _ in range(2):
        with pytest.raises(BizSystemUnavailable):
            await client._request("GET", "/x")
    assert len(downstream_calls) == 2

    # 第三次：熔断打开，快速失败，下游零调用
    with pytest.raises(BizSystemUnavailable, match="熔断中"):
        await client._request("GET", "/x")
    assert len(downstream_calls) == 2  # 未增加 → 快速失败生效


async def test_circuit_breaker_recovers_after_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    """冷却期到 → 半开探测 → 成功 → 恢复闭合。"""
    from src.services.base_client import BaseHttpClient

    client = BaseHttpClient(base_url="http://fake-downstream", retry_attempts=1)
    client._breaker._threshold = 1
    client._breaker._recovery = 0.0  # 立即冷却完毕

    calls = {"n": 0}

    async def fail_first_then_ok(*_a: Any, **_k: Any) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:          # 仅首次失败，后续（半开探测）成功
            raise httpx.ConnectError("down")
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(client._client, "request", fail_first_then_ok)

    with pytest.raises(BizSystemUnavailable):
        await client._request("GET", "/x")          # 失败 → 打开
    data = await client._request("GET", "/x")       # 冷却0s → 半开 → 探测成功 → 闭合
    assert data == {"ok": True}


# ==================== fastmcp 返回兼容解析 ====================

class _TextContent:
    """模拟 TextContent。"""

    def __init__(self, text: str) -> None:
        self.text = text


def test_parse_result_dict_data() -> None:
    """形态一：CallToolResult.data 为 dict。"""

    class R:
        data = {"order_id": "PO-1"}

    assert GatewayClient._parse_result(R()) == {"order_id": "PO-1"}


def test_parse_result_content_list_json() -> None:
    """形态二：content 列表，文本为 JSON。"""

    class R:
        data = None
        content = [_TextContent('{"workflow_id": "wf-9", "status": "PENDING"}')]

    assert GatewayClient._parse_result(R()) == {"workflow_id": "wf-9", "status": "PENDING"}


def test_parse_result_content_list_plain_text() -> None:
    """形态三：content 列表，纯文本（不可 JSON 解析）→ raw 兜底。"""

    class R:
        data = None
        content = [_TextContent("操作成功")]

    assert GatewayClient._parse_result(R()) == {"raw": ["操作成功"]}


def test_parse_result_bare_list() -> None:
    """形态四：直接返回 content 列表（无包装对象）。"""
    parsed = GatewayClient._parse_result([_TextContent('{"ok": 1}')])
    assert parsed == {"ok": 1}


def test_idempotency_key_deterministic() -> None:
    """幂等键确定性：同参数同键；参数变化即变键。"""
    k1 = GatewayClient.make_idempotency_key("t1", "create_purchase_order", {"a": 1, "b": 2})
    k2 = GatewayClient.make_idempotency_key("t1", "create_purchase_order", {"b": 2, "a": 1})
    k3 = GatewayClient.make_idempotency_key("t1", "create_purchase_order", {"a": 1, "b": 3})
    assert k1 == k2      # 键序无关
    assert k1 != k3      # 参数不同则键不同
    assert len(k1) <= 160
