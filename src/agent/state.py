"""LangGraph 全局状态池：多 Agent 共享上下文（用户指令 / 任务计划 / 执行结果 / 审批状态）。

状态互通是多智能体协作的基础：查询结果、审批流程ID等在此沉淀，
避免子 Agent 间信息割裂与重复工具调用（README 5.2 状态共享机制）。
"""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """多智能体协作全局状态。"""

    messages: list[dict[str, str]]          # 对话消息（{"role","content"}）
    user_id: str                            # 发起用户ID
    user_role: str | None                   # 用户角色（P2：服务端角色权限强制依据）
    user_instruction: str                   # 用户原始指令
    trace_id: str                           # 任务链路ID（审计串联）
    client_ip: str                          # 调用来源IP（审计溯源）

    plan: list[str]                         # 待执行子任务队列（节点名，按序弹出）
    current_agent: str                      # 当前执行节点名
    results: list[dict[str, Any]]           # 各子Agent执行结果（含错误）
    pending_workflow_id: str | None         # 发起的审批流程ID（操作Agent执行凭证）

    final_answer: str                       # 最终答复（无业务任务时直接生成）
    error: str | None                       # 全局异常信息
