"""六道轮回：轮回立案、孟婆汤确认、投胎确认、归档。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import REINCARNATION_PATHS, SoulStatus
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
from app.models import Reincarnation, Soul
from app.schemas import ReincarnationCreateIn
from app.services.audit import write_audit
from app.services.numbering import next_code
from app.services.state_machine import change_soul_status

router = APIRouter(prefix="/reincarnations", tags=["六道轮回"])


@router.get("", summary="轮回档案列表")
async def list_reincarnations(
    keyword: str = Query(""),
    status: str = Query(""),
    path: str = Query(""),
    region: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("reincarnation:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Reincarnation)
    for cond in scope_conditions(user, Reincarnation):
        stmt = stmt.where(cond)
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(Reincarnation.reinc_no, keyword),
                like_filter(Reincarnation.soul_name, keyword),
            )
        )
    if status:
        stmt = stmt.where(Reincarnation.status == status)
    if path:
        stmt = stmt.where(Reincarnation.path == path)
    if region:
        stmt = stmt.where(Reincarnation.region == region)

    stmt = stmt.order_by(Reincarnation.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/summary", summary="六道轮回分布统计")
async def reincarnation_summary(
    user: CurrentUser = Depends(require_permission("reincarnation:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Reincarnation)
    for cond in scope_conditions(user, Reincarnation):
        stmt = stmt.where(cond)
    rows = (await db.execute(stmt)).scalars().all()
    by_path = {p: 0 for p in REINCARNATION_PATHS}
    by_status: dict[str, int] = {}
    for row in rows:
        by_path[row.path] = by_path.get(row.path, 0) + 1
        by_status[row.status] = by_status.get(row.status, 0) + 1
    return resp_ok(
        {
            "total": len(rows),
            "by_path": [{"path": k, "count": v} for k, v in by_path.items()],
            "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
            "soup_pending": sum(1 for r in rows if not r.soup_confirmed),
        }
    )


@router.get("/{reinc_id}", summary="轮回档案详情")
async def get_reincarnation(
    reinc_id: int,
    user: CurrentUser = Depends(require_permission("reincarnation:view")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Reincarnation, reinc_id)
    if record is None:
        raise NotFoundError("轮回档案不存在")
    ensure_data_scope(user, record, "轮回档案")
    return resp_ok(model_to_dict(record))


@router.post("", summary="轮回立案")
async def create_reincarnation(
    payload: ReincarnationCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("reincarnation:create")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, payload.soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    if soul.status not in (SoulStatus.SERVED.value, SoulStatus.WAIT_REBIRTH.value, SoulStatus.WRONGFUL_CITY.value):
        raise ConflictError(f"亡魂当前状态为「{soul.status}」，仅「刑满 / 待投胎 / 枉死城」可办理轮回")
    if payload.path not in REINCARNATION_PATHS:
        raise AppError(f"非法六道，可选：{'、'.join(REINCARNATION_PATHS)}")

    existing = (
        await db.execute(
            select(Reincarnation).where(
                Reincarnation.soul_id == soul.id,
                Reincarnation.status.in_(["待办理", "待投胎"]),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"该亡魂已有在办轮回档案 {existing.reinc_no}")

    reinc_no = await next_code(db, Reincarnation, "reinc_no", "LH", 5)
    record = Reincarnation(
        reinc_no=reinc_no,
        soul_id=soul.id,
        soul_name=soul.name,
        region=soul.region or "中央",
        path=payload.path,
        target_world=payload.target_world,
        karma_score=soul.karma_score,
        soup_confirmed=False,
        status="待办理",
        scheduled_at=payload.scheduled_at,
        operator_id=user.officer.id,
        remark=payload.remark,
    )
    db.add(record)
    await db.flush()

    await write_audit(
        db,
        action="create",
        module="六道轮回",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="reincarnation",
        resource_id=record.id,
        detail=f"轮回立案 {reinc_no}：{soul.name} 入{payload.path}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(record), msg="轮回档案已建立")


@router.post("/{reinc_id}/soup", summary="孟婆汤确认")
async def confirm_soup(
    reinc_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("reincarnation:soup")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Reincarnation, reinc_id)
    if record is None:
        raise NotFoundError("轮回档案不存在")
    if record.soup_confirmed:
        raise ConflictError("该亡魂已饮孟婆汤，请勿重复确认")
    if record.status in ("已投胎", "已归档", "已撤销"):
        raise ConflictError(f"当前状态为「{record.status}」，不可办理孟婆汤")

    record.soup_confirmed = True
    record.soup_at = utcnow()
    record.soup_operator = user.officer.real_name
    record.status = "待投胎"

    await write_audit(
        db,
        action="soup",
        module="六道轮回",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="reincarnation",
        resource_id=record.id,
        detail=f"{record.reinc_no}：{record.soul_name} 饮孟婆汤，前尘尽忘",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(record), msg="孟婆汤已确认")


@router.post("/{reinc_id}/reincarnate", summary="投胎确认（需先饮孟婆汤）")
async def confirm_reincarnation(
    reinc_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("reincarnation:confirm")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Reincarnation, reinc_id)
    if record is None:
        raise NotFoundError("轮回档案不存在")
    if record.status == "已投胎":
        raise ConflictError("该档案已完成投胎")
    if not record.soup_confirmed:
        raise ConflictError("未确认孟婆汤，不可投胎（前尘未断）")

    soul = await db.get(Soul, record.soul_id) if record.soul_id else None
    if soul is None:
        raise NotFoundError("轮回关联亡魂不存在")

    transition = None
    if soul.status == SoulStatus.SERVED.value:
        transition = await change_soul_status(db, soul, "to_rebirth", reason="刑满转轮回")
    transition = await change_soul_status(db, soul, "reincarnate", reason=f"投{record.path}")

    record.status = "已投胎"
    record.reincarnated_at = utcnow()

    await write_audit(
        db,
        action="reincarnate",
        module="六道轮回",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="reincarnation",
        resource_id=record.id,
        detail=f"{record.reinc_no}：{record.soul_name} 投{record.path}（{record.target_world or '待定'}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(
        {"reincarnation": model_to_dict(record), "transition": transition},
        msg="投胎已确认",
    )


@router.post("/{reinc_id}/archive", summary="轮回档案归档（亡魂注销）")
async def archive_reincarnation(
    reinc_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("reincarnation:confirm")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Reincarnation, reinc_id)
    if record is None:
        raise NotFoundError("轮回档案不存在")
    if record.status != "已投胎":
        raise ConflictError(f"当前状态为「{record.status}」，仅已投胎可归档")

    soul = await db.get(Soul, record.soul_id) if record.soul_id else None
    if soul is None:
        raise NotFoundError("轮回关联亡魂不存在")

    record.status = "已归档"
    transition = await change_soul_status(db, soul, "archive", reason="投胎归档")

    await write_audit(
        db,
        action="archive",
        module="六道轮回",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="reincarnation",
        resource_id=record.id,
        detail=f"{record.reinc_no}：{record.soul_name} 轮回归档",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"reincarnation": model_to_dict(record), "transition": transition}, msg="已归档")
