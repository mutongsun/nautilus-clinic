"""异步数据库引擎与会话工厂（审计日志持久化用，PostgreSQL + asyncpg）。"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import get_settings
from src.db.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """获取全局异步引擎（懒加载单例）。"""
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db() -> None:
    """初始化表结构（骨架阶段 create_all；生产演进为 alembic 迁移）。

    使用一次性独立引擎并在完成后 dispose——禁止触碰全局懒加载引擎：
    启动预热（asyncio.run）与正式服务（uvicorn）运行在不同 event loop，
    asyncpg 连接绑定创建时的 loop，跨 loop 复用会抛
    "Future attached to a different loop" 导致审计/幂等查询持续降级。
    """
    from src.config.settings import get_settings

    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()
