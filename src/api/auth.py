"""认证路由：登录签发 JWT / 当前用户信息（P2 认证落地）。"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.common.constants import USER_ROLE_ALLOWED_AGENTS
from src.common.logging import get_logger
from src.common.security import create_token, decode_token, verify_password
from src.config.settings import get_settings
from src.db.engine import get_session_factory
from src.db.models import AuthUser

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(min_length=1, max_length=64, description="用户名")
    password: str = Field(min_length=1, max_length=128, description="口令")


class LoginResponse(BaseModel):
    """登录响应。"""

    token: str = Field(description="JWT 访问令牌（Authorization: Bearer <token>）")
    username: str = Field(description="用户名")
    role: str = Field(description="用户角色")
    allowed_agents: list[str] = Field(description="该角色允许的 Agent 角色（服务端强制）")


async def seed_users_if_empty() -> None:
    """首次启动播种初始账号（表空时；生产环境登录后必须立即改密）。"""
    from src.common.constants import SEED_USERS
    from src.common.security import hash_password

    async with get_session_factory()() as session:
        count = len((await session.execute(select(AuthUser.id))).all())
        if count > 0:
            return
        for username, password, role in SEED_USERS:
            session.add(AuthUser(username=username, password_hash=hash_password(password), role=role))
        await session.commit()
        logger.info("初始账号已播种: %s", [u for u, _, _ in SEED_USERS])


def _require_user(request: Request) -> dict:
    """从请求解析当前登录用户（Bearer JWT -> {username, role}）。

    Raises:
        HTTPException 401: 未携带令牌 / 令牌无效或过期。
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = decode_token(auth.removeprefix("Bearer ").strip(),
                               get_settings().auth_jwt_secret)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=f"令牌无效: {exc}") from exc
    return {"username": payload["sub"], "role": payload["role"]}


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    """用户名口令登录：校验 PBKDF2 散列，签发 12 小时 JWT。"""
    async with get_session_factory()() as session:
        user = (await session.execute(
            select(AuthUser).where(AuthUser.username == req.username)
        )).scalar_one_or_none()

    if user is None or not verify_password(req.password, user.password_hash):
        logger.warning("登录失败: username=%s", req.username)
        raise HTTPException(status_code=401, detail="用户名或口令错误")

    settings = get_settings()
    token = create_token(user.username, user.role, settings.auth_jwt_secret)
    logger.info("登录成功: username=%s role=%s", user.username, user.role)
    return LoginResponse(
        token=token,
        username=user.username,
        role=user.role,
        allowed_agents=sorted(USER_ROLE_ALLOWED_AGENTS.get(user.role, frozenset())),
    )


@router.get("/me")
async def me(request: Request) -> dict:
    """当前登录用户信息（前端启动时校验本地令牌有效性）。"""
    user = _require_user(request)
    return {
        "username": user["username"],
        "role": user["role"],
        "allowed_agents": sorted(USER_ROLE_ALLOWED_AGENTS.get(user["role"], frozenset())),
    }
