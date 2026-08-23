"""对话接口出入参模型。"""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求。"""

    user_id: str = Field(default="u-dev", min_length=1, description="发起用户ID")
    message: str = Field(min_length=1, max_length=2000, description="用户指令")


class ChatResponse(BaseModel):
    """对话响应。"""

    answer: str = Field(description="面向用户的自然语言汇总")
    trace_id: str = Field(description="任务链路ID（审计检索凭证）")
    results: list[dict[str, Any]] = Field(default_factory=list, description="各子Agent执行明细")
    status: str = Field(description="OK / PARTIAL")
