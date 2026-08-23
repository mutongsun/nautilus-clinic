"""业务审批 Agent：专职企业风控流程（发起审批 / 状态查询 / 通过后联动）。"""

from typing import Any

from src.agent.gateway_client import get_gateway_client
from src.agent.state import AgentState
from src.common.constants import AgentRole
from src.common.logging import get_logger

logger = get_logger(__name__)


async def approval_node(state: AgentState) -> dict:
    """审批节点：发起采购审批流程，流程ID沉淀到状态池供操作Agent使用。

    若指令仅为"查询审批状态"，则转状态查询，不重复发起。
    """
    instruction = state["user_instruction"]
    gateway = get_gateway_client()
    results: list[dict[str, Any]] = list(state.get("results", []))
    updates: dict[str, Any] = {}

    # 已携带流程ID且明确是查询状态 -> 查询而非重复发起
    workflow_id = state.get("pending_workflow_id")
    if workflow_id and re_search_status(instruction):
        await _safe_call(
            state, gateway, "query_approval_status", {"workflow_id": workflow_id}, results
        )
    else:
        # 发起采购审批：明细优先取查询Agent沉淀的库存数据
        items = _extract_items_from_results(state.get("results", []))
        payload = {
            "title": f"采购申请（来自智能体·{state['trace_id']}）",
            "applicant": state["user_id"],
            "items": items,
            "remark": instruction[:200],
        }
        data = await _safe_call(
            state, gateway, "start_purchase_approval", payload, results
        )
        if data and data.get("ok") and data.get("data", {}).get("workflow_id"):
            # 流程ID沉淀：操作Agent执行高风险写入的必要凭证
            updates["pending_workflow_id"] = data["data"]["workflow_id"]

    updates.update({"results": results, "plan": state["plan"][1:], "current_agent": "approval_agent"})
    return updates


def re_search_status(instruction: str) -> bool:
    """判断指令是否为"查询审批状态"类意图（已携带流程ID时避免重复发起审批）。"""
    return any(k in instruction for k in ("状态", "进度", "通过了吗", "批准", "已通过", "驳回"))


def _extract_items_from_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从查询Agent结果中提取库存明细组装采购项（低于安全水位的缺货药品）。"""
    from src.config.settings import get_settings

    threshold = get_settings().inventory_safety_threshold
    for item in results:
        if item.get("tool") == "query_inventory" and item.get("ok"):
            rows = item.get("data", {}).get("items", [])
            low = [
                {
                    "medicine_name": r.get("medicine_name", ""),
                    "quantity": max(threshold - float(r.get("stock_qty", 0)), 1),
                    "unit_price": float(r.get("unit_price", 0)),
                }
                for r in rows
                if float(r.get("stock_qty", 0)) < threshold
            ]
            return low
    return []


async def _safe_call(state: AgentState, gateway: Any, tool_name: str,
                     params: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """调用审批类工具并收集结果（异常记录不中断）。"""
    try:
        data = await gateway.call(state, AgentRole.APPROVAL, tool_name, params)
        results.append({"agent": "approval_agent", "tool": tool_name, "ok": True, "data": data})
        return results[-1]
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "审批Agent工具调用失败: tool=%s trace_id=%s user_id=%s",
            tool_name, state["trace_id"], state["user_id"],
        )
        results.append({"agent": "approval_agent", "tool": tool_name, "ok": False, "error": str(exc)})
        return results[-1]
