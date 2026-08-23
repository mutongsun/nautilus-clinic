"""业务查询 Agent：专职只读业务，仅调用只读 MCP 工具（Casbin 零写权限）。"""

import re
from typing import Any

from src.agent.gateway_client import get_gateway_client
from src.agent.state import AgentState
from src.common.constants import AgentRole
from src.common.logging import get_logger

logger = get_logger(__name__)

# 从用户指令提取药品名的宽松规则（骨架实现：优先常见剂型结尾词，失败则查全部）
_MEDICINE_PATTERN = re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,12}?(?:胶囊|片|颗粒|口服液|丸))")
# 提取前需剥离的口语动词/助词前缀，避免污染药品名（如"查一下阿莫西林胶囊"）
_INSTRUCTION_NOISE = re.compile(r"(查一下|查询|看一下|帮我|麻烦|请|一下|的|有没有|还有)")


async def query_node(state: AgentState) -> dict:
    """查询节点：库存 / 患者档案只读查询，结果沉淀到全局状态池。"""
    instruction = state["user_instruction"]
    gateway = get_gateway_client()
    results: list[dict[str, Any]] = list(state.get("results", []))

    # 患者类查询
    if re.search(r"患者|档案|病历", instruction):
        name_match = re.search(r"(?:患者|查询|看一下)\s*([\u4e00-\u9fa5]{2,4})", instruction)
        params = {"patient_name": name_match.group(1) if name_match else " "}
        await _call_and_collect(state, gateway, "query_patient", params, results)
    # 默认库存查询（提取药品名，未命中则查全部）
    else:
        cleaned = _INSTRUCTION_NOISE.sub("", instruction)
        med = _MEDICINE_PATTERN.search(cleaned)
        params = {"medicine_name": med.group(1) if med else ""}
        await _call_and_collect(state, gateway, "query_inventory", params, results)

    # 消费队首任务，交还调度路由下一个子任务
    return {"results": results, "plan": state["plan"][1:], "current_agent": "query_agent"}


async def _call_and_collect(
    state: AgentState,
    gateway: Any,
    tool_name: str,
    params: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    """调用工具并收集结果（异常不中断整体流程，记录后继续）。"""
    try:
        data = await gateway.call(state, AgentRole.QUERY, tool_name, params)
        results.append({"agent": "query_agent", "tool": tool_name, "ok": True, "data": data})
    except Exception as exc:  # noqa: BLE001 —— 单节点失败不影响整体主流程（容错机制）
        logger.exception(
            "查询Agent工具调用失败: tool=%s trace_id=%s user_id=%s",
            tool_name, state["trace_id"], state["user_id"],
        )
        results.append({"agent": "query_agent", "tool": tool_name, "ok": False, "error": str(exc)})
