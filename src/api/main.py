"""Agent 服务 FastAPI 入口（容器内端口 8100）。

职责边界（开发规范 1.1）：仅做参数声明、鉴权入口与响应组装，不含业务逻辑。

P2 企业级强化：
  - 用户认证：/chat* 需 Bearer JWT（AUTH_ENABLED=true 时），用户身份来自令牌而非请求体；
  - 角色权限：用户角色 -> 允许的 Agent 角色（USER_ROLE_ALLOWED_AGENTS），服务端强制；
  - 异步任务：POST /chat/async 立即返回 task_id，Redis 存状态，GET /chat/tasks/{id} 轮询；
  - 会话外置：对话历史写 Redis（进程重启不丢，多实例演进基础）。
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from src.agent.graph import build_graph, compose_answer
from src.api.auth import _require_user, router as auth_router, seed_users_if_empty
from src.api.schemas.chat import ChatRequest, ChatResponse
from src.common.exceptions import BaseAppError
from src.common.logging import get_logger, setup_logging
from src.config.settings import get_settings
from src.services import session_store

# 对话控制台前端（单文件静态页，随镜像发布）
_INDEX_HTML = Path(__file__).resolve().parent.parent / "static" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务生命周期：初始化表结构、播种账号、编译协作图。"""
    settings = get_settings()
    setup_logging(settings.log_level)
    try:
        from src.db.engine import init_db

        await init_db()
        await seed_users_if_empty()
    except Exception:  # noqa: BLE001 —— DB 未就绪不阻断服务（登录时自然报错）
        get_logger(__name__).exception("数据库初始化失败（认证功能不可用，服务仍启动）")
    app.state.graph = build_graph()
    yield


app = FastAPI(title="Nautilus Agent Platform", version="0.2.0", lifespan=lifespan)
app.include_router(auth_router)


@app.exception_handler(BaseAppError)
async def app_error_handler(_req: Request, exc: BaseAppError) -> JSONResponse:
    """已知业务异常：返回错误码+可读信息（不含堆栈，不暴露内部细节）。"""
    return JSONResponse(status_code=400, content={"code": exc.code, "message": exc.message})


@app.exception_handler(Exception)
async def unexpected_error_handler(req: Request, exc: Exception) -> JSONResponse:
    """未预期异常：统一友好提示；堆栈只进日志（含 trace 上下文），不回传前端。"""
    logger = get_logger(__name__)
    logger.exception(
        "未预期异常: path=%s client=%s", req.url.path, req.client.host if req.client else "?"
    )
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "系统繁忙，请稍后重试或联系管理员"},
    )


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    """API Key 校验中间件（服务间调用场景；用户认证由各端点 _require_user 负责）。"""
    settings = get_settings()
    if (
        settings.api_auth_enabled
        and request.url.path.startswith("/chat")
        and not request.url.path.startswith("/chat/tasks")
        and request.headers.get("X-API-Key") != settings.api_auth_key
        and not request.headers.get("Authorization", "").startswith("Bearer ")
    ):
        return JSONResponse(
            status_code=401, content={"code": "UNAUTHORIZED", "message": "无效的 API Key"}
        )
    return await call_next(request)


def _current_user(request: Request, req: ChatRequest) -> dict:
    """解析对话发起者：认证开启取令牌用户（不可伪造），关闭时回退请求体（开发模式）。"""
    if get_settings().auth_enabled:
        user = _require_user(request)
        return {"user_id": user["username"], "user_role": user["role"]}
    return {"user_id": req.user_id or "u-dev", "user_role": None}


@app.get("/health")
async def health() -> dict[str, str]:
    """健康检查端点（docker-compose healthcheck 探测目标）。"""
    return {"status": "ok", "service": "agent"}


@app.get("/", include_in_schema=False)
async def console() -> FileResponse:
    """对话控制台前端页面。"""
    return FileResponse(_INDEX_HTML, media_type="text/html")


def _client_ip(request: Request) -> str:
    """提取客户端真实IP（优先反向代理头，兼容 Nginx/网关部署）。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _run_chat(app: FastAPI, user: dict, message: str, request: Request) -> dict:
    """执行一次完整多智能体协作（同步/异步端点共用）。"""
    logger = get_logger(__name__)
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    state = {
        "messages": [{"role": "user", "content": message}],
        "user_id": user["user_id"],
        "user_role": user.get("user_role"),
        "user_instruction": message,
        "trace_id": trace_id,
        "client_ip": _client_ip(request),
        "results": [],
    }
    final_state = await app.state.graph.ainvoke(state)

    answer = compose_answer(final_state)
    results = final_state.get("results", [])
    status = "OK" if all(r.get("ok") for r in results) else "PARTIAL"
    # 会话历史外置 Redis（旧->新：用户消息 + 助手答复）
    await session_store.append_session(user["user_id"], "user", message)
    await session_store.append_session(user["user_id"], "assistant", answer)
    logger.info("对话处理完成", extra={"trace_id": trace_id, "status": status, "steps": len(results)})
    return {"answer": answer, "trace_id": trace_id, "results": results, "status": status}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """同步对话入口：阻塞执行完整协作后一次性返回。"""
    user = _current_user(request, req)
    data = await _run_chat(app, user, req.message, request)
    return ChatResponse(**data)


# ==================== P2 异步任务端点 ====================

@app.post("/chat/async")
async def chat_async(req: ChatRequest, request: Request) -> dict:
    """异步对话入口：立即返回 task_id，前端轮询 /chat/tasks/{task_id} 获取结果。

    适用长链路任务（多Agent协作 + 等待外部系统），避免 HTTP 长阻塞超时。
    """
    user = _current_user(request, req)
    task_id = uuid.uuid4().hex[:16]
    await session_store.create_task(task_id)

    async def _runner() -> None:
        """后台执行协作并回写任务终态（异常兜底为 FAILED，不让任务悬空）。"""
        try:
            await session_store.set_task(task_id, {"status": "RUNNING"})
            data = await _run_chat(app, user, req.message, request)
            await session_store.set_task(task_id, {"status": data["status"], **data})
        except Exception as exc:  # noqa: BLE001
            get_logger(__name__).exception("异步任务失败: task=%s", task_id)
            await session_store.set_task(
                task_id, {"status": "FAILED", "answer": f"任务执行失败: {exc}", "results": []}
            )

    asyncio.create_task(_runner())
    return {"task_id": task_id, "status": "PENDING"}


@app.get("/chat/tasks/{task_id}")
async def chat_task(task_id: str) -> dict:
    """查询异步任务状态：PENDING / RUNNING / OK / PARTIAL / FAILED。"""
    task = await session_store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return task


@app.get("/chat/sessions/me")
async def my_session(request: Request) -> dict:
    """当前用户最近会话历史（Redis 外置，跨请求/跨重启保留）。"""
    user = _require_user(request) if get_settings().auth_enabled else {"username": "u-dev"}
    return {"username": user["username"], "messages": await session_store.get_session(user["username"])}
