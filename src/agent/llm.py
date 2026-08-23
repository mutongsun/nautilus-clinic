"""LLM 访问助手：调度 Agent 意图精化的可选增强（未配置 Key 时自动降级为纯规则）。"""

import json
from typing import Any

from src.common.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)

_CANDIDATE_AGENTS = ["query_agent", "approval_agent", "operator_agent"]

_PROMPT = (
    "你是企业智能体的任务规划器。根据用户指令，从下列候选子任务中选择需要执行的部分并给出执行顺序，"
    f"以JSON数组返回（可为空数组）：{json.dumps(_CANDIDATE_AGENTS, ensure_ascii=False)}\n"
    "规则：涉及查询库存/患者等只读信息选 query_agent；"
    "涉及申请/审批/采购流程选 approval_agent；"
    "涉及下单/发药等实际写入，必须保证 approval_agent 已在 operator_agent 之前。\n"
    "用户指令：{instruction}\n"
    "规则引擎初步结果（供参考，可修正）：{base_plan}\n"
    "只输出JSON数组，不要任何解释。"
)


def get_chat_model() -> Any | None:
    """获取 ChatOpenAI 实例；未配置 API Key 返回 None（调用方降级）。"""
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout=10,
        )
    except Exception:  # noqa: BLE001 —— LLM 不可用必须降级而非阻断
        logger.exception("LLM 初始化失败，将降级为纯规则分发")
        return None


async def refine_plan_with_llm(instruction: str, base_plan: list[str]) -> list[str]:
    """用 LLM 精化任务计划；任何失败均回退规则结果（双驱动分发之模型侧）。"""
    model = get_chat_model()
    if model is None:
        return base_plan
    try:
        resp = await model.ainvoke(_PROMPT.format(instruction=instruction, base_plan=base_plan))
        plan = json.loads(resp.content)
        refined = [p for p in plan if p in _CANDIDATE_AGENTS]
        # 保底：LLM 漏掉规则发现的任务时，以规则结果补齐（模型只做精化，不做否决）
        for p in base_plan:
            if p not in refined:
                refined.append(p)
        return refined
    except Exception:  # noqa: BLE001
        logger.warning("LLM 意图精化失败，回退规则分发", extra={"instruction": instruction[:100]})
        return base_plan
