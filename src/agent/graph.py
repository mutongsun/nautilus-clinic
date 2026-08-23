"""LangGraph 多智能体编排图：调度Agent中枢 + 三个专职业务Agent。

拓扑（README 5.1 角色拆分）：

    START -> dispatcher -> [query_agent | approval_agent | operator_agent] -> dispatcher -> ... -> END

- dispatcher 为唯一中枢：首轮规划任务队列，子任务执行完毕后回流；
- 路由函数按状态池 plan 队首弹出下一个子Agent，队列为空即结束；
- 单节点失败只记录结果、不中断主流程（任务容错）。
"""

from langgraph.graph import END, START, StateGraph

from src.agent.nodes.approval import approval_node
from src.agent.nodes.dispatcher import dispatcher_node
from src.agent.nodes.operator import operator_node
from src.agent.nodes.query import query_node
from src.agent.state import AgentState

_NODE_NAMES = {"query_agent", "approval_agent", "operator_agent"}

# 节点名 -> 中文角色名（最终答复展示用）
_AGENT_LABELS = {
    "query_agent": "查询Agent",
    "approval_agent": "审批Agent",
    "operator_agent": "操作Agent",
}


def _route_next(state: AgentState) -> str:
    """条件路由：弹出队首子任务；队列为空返回 END。"""
    plan = state.get("plan") or []
    return plan[0] if plan else "__end__"


def build_graph():
    """构建并编译多智能体协作图。"""
    graph = StateGraph(AgentState)
    graph.add_node("dispatcher", dispatcher_node)
    graph.add_node("query_agent", query_node)
    graph.add_node("approval_agent", approval_node)
    graph.add_node("operator_agent", operator_node)

    graph.add_edge(START, "dispatcher")
    graph.add_conditional_edges(
        "dispatcher",
        _route_next,
        {name: name for name in _NODE_NAMES} | {"__end__": END},
    )
    # 子任务执行完毕一律回流调度中枢（由路由决定继续还是结束）
    for name in _NODE_NAMES:
        graph.add_edge(name, "dispatcher")

    return graph.compile()


def compose_answer(state: AgentState) -> str:
    """汇总各子Agent执行结果，生成最终答复（面向用户的自然语言摘要）。"""
    if state.get("final_answer"):
        return state["final_answer"]

    lines: list[str] = []
    workflow_id = state.get("pending_workflow_id")
    for item in state.get("results", []):
        agent = item.get("agent", "")
        tool = item.get("tool", "")
        if item.get("ok"):
            data = item.get("data", {})
            if tool == "query_inventory":
                lines.append(f"查询Agent：共获取 {data.get('count', 0)} 条药品库存记录")
            elif tool == "query_patient":
                lines.append(f"查询Agent：共获取 {data.get('count', 0)} 条患者档案")
            elif tool == "start_purchase_approval":
                lines.append("审批Agent：采购审批流程已发起，等待人工审批")
            elif tool == "query_approval_status":
                lines.append(f"审批Agent：当前审批状态 {data.get('status', 'UNKNOWN')}")
            else:
                lines.append(f"{_AGENT_LABELS.get(agent, agent)}：{tool} 执行成功")
        else:
            err = str(item.get("error", ""))
            if "BPM_PENDING" in err:
                lines.append("操作Agent：审批仍在等待人工处理，暂不能执行写入")
            elif "BPM_NOT_APPROVED" in err:
                lines.append("操作Agent：未获审批通过（或缺少审批凭证），已拒绝执行写操作")
            elif "PERMISSION_DENIED" in err:
                lines.append(f"{_AGENT_LABELS.get(agent, agent)}：无调用权限，已被网关拦截")
            else:
                lines.append(f"{_AGENT_LABELS.get(agent, agent)}：{tool} 执行失败（{err[:120]}）")

    if workflow_id:
        lines.append(f"审批流程ID：{workflow_id}（人工审批通过后可让我继续执行订单）")
    return "\n".join(lines) if lines else "任务已处理完成。"
