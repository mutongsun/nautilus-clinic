"""{{PROJECT_NAME}} — 诊所业务 Agent（医疗行业模板）。

由 nautilus-agent-cli 生成；工程规范遵循 Nautilus Agent Platform 开发规范
（目录结构 / 风险等级标注 / 审计埋点 / Git 分支）。
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="{{PROJECT_NAME}}", version="0.1.0")


class ChatIn(BaseModel):
    """对话请求。"""

    message: str = Field(min_length=1, description="用户指令")


@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatIn) -> dict[str, str]:
    """对话入口（TODO: 接入 MCP 网关与 LangGraph 编排）。"""
    return {"answer": f"已收到指令: {req.message}"}
