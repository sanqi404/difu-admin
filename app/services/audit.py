"""阴律日志服务：所有写操作留痕。"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    module: str,
    officer_id: int | None = None,
    officer_name: str = "",
    role_name: str = "",
    resource: str = "",
    resource_id: str | int = "",
    detail: str = "",
    level: str = "正常",
    ip: str = "",
    user_agent: str = "",
) -> AuditLog:
    """仅 add 不 commit，随业务事务一并提交，保证日志与业务同生共死。"""
    log = AuditLog(
        officer_id=officer_id,
        officer_name=officer_name,
        role_name=role_name,
        action=action,
        module=module,
        resource=resource,
        resource_id=str(resource_id),
        detail=detail[:2000],
        level=level,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(log)
    await db.flush()
    return log


def audit_from_user(user: Any, **kwargs: Any) -> dict[str, Any]:
    """从 CurrentUser 提取审计公共字段。"""
    base = {
        "officer_id": getattr(getattr(user, "officer", None), "id", None),
        "officer_name": getattr(getattr(user, "officer", None), "real_name", ""),
        "role_name": getattr(getattr(user, "role", None), "name", ""),
    }
    base.update(kwargs)
    return base


async def safe_write_audit(db: AsyncSession, **kwargs: Any) -> None:
    """审计失败不影响主流程（仅告警日志）。"""
    try:
        await write_audit(db, **kwargs)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"写阴律日志失败: {exc}")
