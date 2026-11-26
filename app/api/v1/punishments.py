"""刑期台账：十八层地狱执行、减免、刑满释放。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import HELL_NAMES, SoulStatus
from app.core.deps import (
    CurrentUser,
    client_ip,
    client_ua,
    ensure_data_scope,
    require_permission,
    scope_conditions,
)
from app.core.response import AppError, ConflictError, NotFoundError, page_resp, resp_ok
from app.core.utils import like_filter, model_to_dict, models_to_list, paginate
from app.database import get_db, utcnow
from app.models import Punishment, Soul
from app.schemas import PunishmentAdjustIn
from app.services.audit import write_audit
from app.services.state_machine import change_soul_status

router = APIRouter(prefix="/punishments", tags=["刑期执行"])


@router.get("", summary="刑期台账列表")
async def list_punishments(
    keyword: str = Query(""),
    status: str = Query(""),
    hell_level: int | None = Query(None, ge=1, le=18),
    region: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("punishment:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Punishment)
    for cond in scope_conditions(user, Punishment):
        stmt = stmt.where(cond)
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(Punishment.punish_no, keyword),
                like_filter(Punishment.soul_name, keyword),
            )
        )
    if status:
        stmt = stmt.where(Punishment.status == status)
    if hell_level:
        stmt = stmt.where(Punishment.hell_level == hell_level)
    if region:
        stmt = stmt.where(Punishment.region == region)

    stmt = stmt.order_by(Punishment.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/summary", summary="刑期执行统计（十八层地狱分布）")
async def punishment_summary(
    user: CurrentUser = Depends(require_permission("punishment:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Punishment)
    for cond in scope_conditions(user, Punishment):
        stmt = stmt.where(cond)
    rows = (await db.execute(stmt)).scalars().all()
    by_hell = {i: 0 for i in range(1, 19)}
    by_status: dict[str, int] = {}
    for row in rows:
        by_hell[row.hell_level] = by_hell.get(row.hell_level, 0) + 1
        by_status[row.status] = by_status.get(row.status, 0) + 1
    return resp_ok(
        {
            "total": len(rows),
            "by_hell": [
                {"level": lv, "hell": HELL_NAMES[lv - 1], "count": cnt}
                for lv, cnt in sorted(by_hell.items())
            ],
            "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
            "serving": by_status.get("服刑中", 0),
            "served": by_status.get("已刑满", 0),
        }
    )


@router.get("/{punish_id}", summary="刑期详情")
async def get_punishment(
    punish_id: int,
    user: CurrentUser = Depends(require_permission("punishment:view")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Punishment, punish_id)
    if record is None:
        raise NotFoundError("刑期记录不存在")
    ensure_data_scope(user, record, "刑期台账")
    return resp_ok(model_to_dict(record))


@router.post("/{punish_id}/execute", summary="开始服刑")
async def execute_punishment(
    punish_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("punishment:execute")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Punishment, punish_id)
    if record is None:
        raise NotFoundError("刑期记录不存在")
    ensure_data_scope(user, record, "刑期台账")
    if record.status not in ("待执行", "已减免"):
        raise ConflictError(f"当前状态为「{record.status}」，不可开始服刑")

    soul = await db.get(Soul, record.soul_id) if record.soul_id else None
    if soul is None:
        raise NotFoundError("刑期关联亡魂不存在")

    now = utcnow()
    record.status = "服刑中"
    record.start_at = record.start_at or now
    record.end_at = record.end_at or now + timedelta(days=365 * max(1, record.sentence_years))
    record.executor_name = user.officer.real_name

    transition = None
    if soul.status == SoulStatus.CONVICTED.value:
        transition = await change_soul_status(db, soul, "sentence", reason=f"交付{record.hell_name}")
    elif soul.status != SoulStatus.SERVING.value:
        raise ConflictError(f"亡魂当前状态为「{soul.status}」，不可开始服刑")

    await write_audit(
        db,
        action="execute",
        module="刑期执行",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="punishment",
        resource_id=record.id,
        detail=f"{record.punish_no}：{record.soul_name} 押入{record.hell_name}，刑期 {record.sentence_years} 年",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"punishment": model_to_dict(record), "transition": transition}, msg="已开始服刑")


@router.post("/{punish_id}/adjust", summary="刑期减免 / 延期")
async def adjust_punishment(
    punish_id: int,
    payload: PunishmentAdjustIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("punishment:adjust")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Punishment, punish_id)
    if record is None:
        raise NotFoundError("刑期记录不存在")
    ensure_data_scope(user, record, "刑期台账")
    if record.status in ("已刑满", "已转出"):
        raise ConflictError(f"当前状态为「{record.status}」，不可调整")

    delta = payload.reduced_years
    new_reduced = (record.reduced_years or 0) + delta
    if new_reduced > record.sentence_years:
        raise AppError("累计减免年限不可超过原判刑期")

    record.reduced_years = new_reduced
    base = record.start_at or utcnow()
    record.end_at = base + timedelta(days=365 * (record.sentence_years - new_reduced))
    record.status = "已减免" if new_reduced > 0 and record.status == "待执行" else record.status
    if record.status == "服刑中" and record.end_at <= utcnow():
        record.status = "已刑满"
    record.remark = payload.reason or record.remark

    await write_audit(
        db,
        action="adjust",
        module="刑期执行",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="punishment",
        resource_id=record.id,
        detail=f"{record.punish_no} 刑期调整 {delta:+d} 年（累计减免 {new_reduced} 年）；{payload.reason or ''}",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(record), msg="刑期已调整")


@router.post("/{punish_id}/finish", summary="刑满释放")
async def finish_punishment(
    punish_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("punishment:execute")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Punishment, punish_id)
    if record is None:
        raise NotFoundError("刑期记录不存在")
    ensure_data_scope(user, record, "刑期台账")
    if record.status != "服刑中":
        raise ConflictError(f"当前状态为「{record.status}」，仅服刑中可刑满释放")

    soul = await db.get(Soul, record.soul_id) if record.soul_id else None
    if soul is None:
        raise NotFoundError("刑期关联亡魂不存在")

    record.status = "已刑满"
    record.end_at = utcnow()
    transition = await change_soul_status(db, soul, "serve_out", reason="刑满释放")

    await write_audit(
        db,
        action="finish",
        module="刑期执行",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="punishment",
        resource_id=record.id,
        detail=f"{record.punish_no}：{record.soul_name} 刑满释放",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"punishment": model_to_dict(record), "transition": transition}, msg="已刑满释放")
