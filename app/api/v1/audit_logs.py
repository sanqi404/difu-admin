"""阴律日志：审计查询、告警筛选与导出。"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, client_ip, client_ua, require_permission
from app.core.response import page_resp, resp_ok
from app.core.utils import like_filter, models_to_list, paginate
from app.database import get_db
from app.models import AuditLog
from app.services.audit import write_audit

router = APIRouter(prefix="/audit-logs", tags=["阴律日志"])


def _apply_filters(stmt, keyword: str, module: str, level: str, action: str, officer_id: int | None,
                   start: str, end: str):
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(AuditLog.detail, keyword),
                like_filter(AuditLog.officer_name, keyword),
                like_filter(AuditLog.resource, keyword),
            )
        )
    if module:
        stmt = stmt.where(AuditLog.module == module)
    if level:
        stmt = stmt.where(AuditLog.level == level)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if officer_id:
        stmt = stmt.where(AuditLog.officer_id == officer_id)
    if start:
        stmt = stmt.where(AuditLog.created_at >= datetime.fromisoformat(start).replace(tzinfo=None))
    if end:
        stmt = stmt.where(AuditLog.created_at <= datetime.fromisoformat(end).replace(tzinfo=None))
    return stmt


@router.get("", summary="审计日志列表")
async def list_audit_logs(
    keyword: str = Query(""),
    module: str = Query(""),
    level: str = Query(""),
    action: str = Query(""),
    officer_id: int | None = Query(None),
    start: str = Query("", description="开始时间，ISO 格式，如 2026-11-01T00:00:00"),
    end: str = Query("", description="结束时间，ISO 格式"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("audit:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = _apply_filters(select(AuditLog), keyword, module, level, action, officer_id, start, end)
    stmt = stmt.order_by(AuditLog.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/statistics", summary="审计统计（模块/等级分布）")
async def audit_statistics(
    start: str = Query(""),
    end: str = Query(""),
    user: CurrentUser = Depends(require_permission("audit:view")),
    db: AsyncSession = Depends(get_db),
):
    base = _apply_filters(select(AuditLog), "", "", "", "", None, start, end).subquery()
    by_module = (
        await db.execute(select(base.c.module, func.count()).group_by(base.c.module).order_by(func.count().desc()))
    ).all()
    by_level = (await db.execute(select(base.c.level, func.count()).group_by(base.c.level))).all()
    by_action = (
        await db.execute(select(base.c.action, func.count()).group_by(base.c.action).order_by(func.count().desc()).limit(10))
    ).all()
    tampered = (await db.execute(select(func.count()).select_from(base).where(base.c.level == "篡改告警"))).scalar_one()
    return resp_ok(
        {
            "by_module": [{"module": m or "未知", "count": c} for m, c in by_module],
            "by_level": [{"level": lv or "正常", "count": c} for lv, c in by_level],
            "top_actions": [{"action": a, "count": c} for a, c in by_action],
            "tamper_count": tampered,
        }
    )


@router.get("/export", summary="导出审计日志（xlsx）")
async def export_audit_logs(
    request: Request,
    module: str = Query(""),
    level: str = Query(""),
    action: str = Query(""),
    start: str = Query(""),
    end: str = Query(""),
    user: CurrentUser = Depends(require_permission("audit:export")),
    db: AsyncSession = Depends(get_db),
):
    from openpyxl import Workbook

    stmt = _apply_filters(select(AuditLog), "", module, level, action, None, start, end)
    rows = (await db.execute(stmt.order_by(AuditLog.id.desc()).limit(5000))).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "阴律日志"
    ws.append(["ID", "时间", "鬼差", "角色", "动作", "模块", "资源", "资源ID", "详情", "等级", "IP"])
    for row in rows:
        ws.append(
            [
                row.id,
                row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
                row.officer_name or "",
                row.role_name or "",
                row.action or "",
                row.module or "",
                row.resource or "",
                row.resource_id or "",
                row.detail or "",
                row.level or "",
                row.ip or "",
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    await write_audit(
        db,
        action="export",
        module="阴律日志",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="audit_log",
        detail=f"导出审计日志 {len(rows)} 条",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()

    filename = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
