"""意图调度 Agent（总控节点）：意图解析、任务拆分、分发调度、异常兜底。

职责红线：本节点不处理任何业务规则、不调用任何业务工具（Casbin 亦未授权），
只决定"谁来做、按什么顺序做"。

P2 权限落地：计划生成后按用户角色过滤（viewer 仅查询），越权子任务直接剔除。
"""

import re

from src.agent.llm import refine_plan_with_llm
from src.agent.state import AgentState
from src.common.constants import USER_ROLE_ALLOWED_AGENTS, AgentRole

# 规则侧意图识别（简单意图精准分发；复杂意图由 LLM 精化，双驱动）
_RULES: list[tuple[str, str]] = [
    (r"库存|缺货|药品|患者|档案|查询|查一下|看一下", "query_agent"),
    (r"采购|进货|申请|审批|报销", "approval_agent"),
    (r"下单|创建.*订单|发药|执行订单|出库", "operator_agent"),
]

# 计划节点名 -> Agent 角色（角色过滤用）
_NODE_TO_ROLE: dict[str, str] = {
    "query_agent": AgentRole.QUERY.value,
    "approval_agent": AgentRole.APPROVAL.value,
    "operator_agent": AgentRole.OPERATOR.value,
}

# 支持用户携带流程ID继续执行已批准订单："执行订单 workflow_id=xxx"
_WORKFLOW_ID_PATTERN = re.compile(
    r"(?:workflow[_\-=]?id|流程号|流程ID|工单号)[:=\s]*([0-9a-zA-Z\-]{6,})", re.IGNORECASE
)


def filter_plan_by_role(plan: list[str], user_role: str | None) -> list[str]:
    """按用户角色过滤任务计划（服务端强制权限，客户端不可越权）。

    Args:
        plan: 初步计划（节点名列表）。
        user_role: 用户角色；None（开发模式/脚本）不过滤。

    Returns:
        仅保留该角色被允许的 Agent 对应的子任务。
    """
    if not user_role:
        return plan
    allowed = USER_ROLE_ALLOWED_AGENTS.get(user_role, frozenset())
    return [node for node in plan if _NODE_TO_ROLE.get(node) in allowed]


def _plan_by_rules(instruction: str) -> list[str]:
    """关键词规则生成初始任务计划（去重、保序）。"""
    plan: list[str] = []
    for pattern, agent in _RULES:
        if re.search(pattern, instruction) and agent not in plan:
            plan.append(agent)
    return plan


async def dispatcher_node(state: AgentState) -> dict:
    """调度节点：首轮生成任务计划；后续轮次仅透传（由路由函数逐个弹出）。"""
    # 已规划过（含计划已清空）则不重复规划：注意不能用真值判断，
    # 否则计划消费完毕的空列表会被误判为"未规划"造成死循环
    if "plan" in state:
        return {}

    instruction = state["user_instruction"]

    # 提取用户指令中显式携带的审批流程ID（人工审批通过后继续执行的场景）
    match = _WORKFLOW_ID_PATTERN.search(instruction)
    pending_workflow_id = match.group(1) if match else None

    # 规则 + LLM 双驱动生成任务计划，再按用户角色过滤越权子任务（P2 服务端强制）
    plan = filter_plan_by_role(
        await refine_plan_with_llm(instruction, _plan_by_rules(instruction)),
        state.get("user_role"),
    )
    if not plan:
        had_any = bool(_plan_by_rules(instruction))
        if had_any and state.get("user_role"):
            updates = {"final_answer": "当前账号角色无权执行该操作，请联系管理员开通相应权限。"}
        else:
            updates = {}
        return updates

    updates: dict = {"plan": plan}
    # 补充提示文案由 compose_answer 兜底（无业务意图时给能力说明）
    if not _plan_by_rules(instruction):
        updates["final_answer"] = (
            "我是诊所业务智能体，可以帮您：查询药品库存与患者档案、"
            "发起采购审批、审批通过后自动创建采购订单或发药。"
        )
    if pending_workflow_id:
        updates["pending_workflow_id"] = pending_workflow_id
    return updates
