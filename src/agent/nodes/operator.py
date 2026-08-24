"""业务操作 Agent：专职高风险业务写入。

严格遵循「审批通过后执行业务写入」：执行凭证（bpm_workflow_id）由审批Agent沉淀、
网关强制二次校验 Conductor 实际状态——本节点不做任何审批状态的业务判断（规则下沉）。
"""

from typing import Any

from src.agent.gateway_client import get_gateway_client
from src.agent.state import AgentState
from src.common.constants import AgentRole
from src.common.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


async def operator_node(state: AgentState) -> dict:
    """操作节点：执行采购下单 / 发药等高风险写入。"""
    instruction = state["user_instruction"]
    gateway = get_gateway_client()
    results: list[dict[str, Any]] = list(state.get("results", []))

    if "发药" in instruction:
        await _call(state, gateway, "dispense_prescription",
                    {"consultation_id": _extract_consultation_id(instruction)}, results)
    else:
        supplier = _extract_supplier(instruction) or get_settings().purchase_default_supplier
        if not supplier:
            results.append({
                "agent": "operator_agent", "tool": "create_purchase_order", "ok": False,
                "error": "缺少供应商信息：请在指令中指明供应商，或配置默认供应商 PURCHASE_DEFAULT_SUPPLIER",
            })
            return {"results": results, "plan": state["plan"][1:], "current_agent": "operator_agent"}

        items = _extract_items(state)
        if not items:
            # 独立请求（如"审批通过后执行订单"）无前期库存数据：自查库存补齐缺货明细
            items = await _fetch_low_stock_items(state, gateway, results)
        if not items:
            results.append({
                "agent": "operator_agent", "tool": "create_purchase_order", "ok": False,
                "error": "未发现低于安全水位的缺货药品，无需采购",
            })
            return {"results": results, "plan": state["plan"][1:], "current_agent": "operator_agent"}
        await _call(state, gateway, "create_purchase_order",
                    {"supplier": supplier, "items": items}, results)

    return {"results": results, "plan": state["plan"][1:], "current_agent": "operator_agent"}


async def _fetch_low_stock_items(
    state: AgentState, gateway: Any, results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """下单前自查库存（只读工具），返回低于安全水位的采购明细。"""
    from src.agent.nodes.query import _INSTRUCTION_NOISE, _MEDICINE_PATTERN

    cleaned = _INSTRUCTION_NOISE.sub("", state["user_instruction"])
    med = _MEDICINE_PATTERN.search(cleaned)
    params = {"medicine_name": med.group(1) if med else ""}
    try:
        data = await gateway.call(state, AgentRole.OPERATOR, "query_inventory", params)
        results.append({"agent": "operator_agent", "tool": "query_inventory", "ok": True, "data": data})
        rows = data.get("items", [])
    except Exception as exc:  # noqa: BLE001 —— 自查失败不阻断主流程，交由下单校验兜底
        results.append({"agent": "operator_agent", "tool": "query_inventory", "ok": False, "error": str(exc)})
        return []

    threshold = get_settings().inventory_safety_threshold
    return [
        {
            "medicine_name": r.get("medicine_name", ""),
            "quantity": max(threshold - float(r.get("stock_qty", 0)), 1),
            "unit_price": float(r.get("unit_price", 0)),
        }
        for r in rows
        if r.get("medicine_name") and float(r.get("stock_qty", 0)) < threshold
    ]


def _extract_supplier(instruction: str) -> str | None:
    """从用户指令提取供应商（如「向国药控股下单/采购/执行订单」）。"""
    import re

    match = re.search(
        r"向([\u4e00-\u9fa5A-Za-z（）()]{2,20}?)(?:下单|采购|进货|订购|执行订单)", instruction
    )
    return match.group(1) if match else None


def _extract_consultation_id(instruction: str) -> str:
    """从指令提取就诊记录ID（未提取到时使用占位值，网关/业务底座校验兜底）。"""
    import re

    match = re.search(r"(?:就诊|问诊|记录)[IDid号]*[:=\s]*([0-9]{6,})", instruction)
    return match.group(1) if match else "0000000000"


def _extract_items(state: AgentState) -> list[dict[str, Any]]:
    """组装采购明细：优先取审批发起时的明细（参数最完整），缺省按安全水位补齐。"""
    threshold = get_settings().inventory_safety_threshold
    # 审批Agent发起申请时的明细（幂等场景下与审批单严格一致，最可信）
    for item in state.get("results", []):
        if item.get("tool") == "query_inventory" and item.get("ok"):
            rows = item.get("data", {}).get("items", [])
            low = [
                {
                    "medicine_name": r.get("medicine_name", ""),
                    "quantity": max(threshold - float(r.get("stock_qty", 0)), 1),
                    "unit_price": float(r.get("unit_price", 0)),
                }
                for r in rows
                if r.get("medicine_name") and float(r.get("stock_qty", 0)) < threshold
            ]
            if low:
                return low
    return []


async def _call(state: AgentState, gateway: Any, tool_name: str,
                params: dict[str, Any], results: list[dict[str, Any]]) -> None:
    """调用写工具并收集结果（网关BPM拦截信息会如实反馈给用户）。"""
    try:
        data = await gateway.call(state, AgentRole.OPERATOR, tool_name, params)
        results.append({"agent": "operator_agent", "tool": tool_name, "ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "操作Agent工具调用失败: tool=%s trace_id=%s user_id=%s",
            tool_name, state["trace_id"], state["user_id"],
        )
        results.append({"agent": "operator_agent", "tool": tool_name, "ok": False, "error": str(exc)})
