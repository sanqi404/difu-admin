"""数据库会话管理。业务代码只依赖 DATABASE_URL：dev=SQLite / prod=MySQL。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# ---------- 引擎 ----------
_engine_kwargs: dict = {"echo": settings.DB_ECHO, "future": True, "pool_pre_ping": True}
if settings.is_sqlite:
    # SQLite 单文件场景不需要连接池上限，允许跨线程回滚点
    _engine_kwargs["connect_args"] = {"timeout": 15}
else:
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 1800})

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

if settings.is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):  # noqa: ANN001
        """SQLite 必须显式开启外键约束，否则 FK 形同虚设。"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：一次请求一个会话，异常回滚。"""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """建表（dev 便捷启动用；生产请走 alembic upgrade head）。"""
    from app.models import Base  # noqa: PLC0415  延迟导入避免循环

    if settings.sqlite_file is not None:
        settings.sqlite_file.parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.is_sqlite:
            # 复检一次，确保当前连接外键可用
            result = await conn.execute(text("PRAGMA foreign_keys"))
            if not result.scalar():
                logger.warning("SQLite 外键约束未开启，请检查 PRAGMA 设置")


async def ping_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # pragma: no cover
        logger.error(f"数据库连通性检查失败: {exc}")
        return False


async def close_db() -> None:
    await engine.dispose()


def utcnow() -> datetime:
    """统一由应用层写入 UTC 时间（入库为 naive UTC，避免跨库时区差异）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
