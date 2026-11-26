"""拘魂工单：派发、执行、完成、超时、异常。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SoulStatus
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
from app.models import Officer, Soul, SummonOrder
from app.schemas import DispatchIn, SummonCreateIn, SummonExceptionIn, SummonFinishIn
from app.services.audit import write_audit
from app.services.numbering import next_code
from app.services.state_machine import change_soul_status

router = APIRouter(prefix="/summon-orders", tags=["拘魂工单"])


@router.get("", summary="拘魂工单列表")
async def list_orders(
    keyword: str = Query(""),
    status: str = Query(""),
    priority: str = Query(""),
    region: str = Query(""),
    assignee_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("summon:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SummonOrder)
    for cond in scope_conditions(user, SummonOrder):
        stmt = stmt.where(cond)
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(SummonOrder.order_no, keyword),
                like_filter(SummonOrder.soul_name, keyword),
            )
        )
    if status:
        stmt = stmt.where(SummonOrder.status == status)
    if priority:
        stmt = stmt.where(SummonOrder.priority == priority)
    if region:
        stmt = stmt.where(SummonOrder.region == region)
    if assignee_id:
        stmt = stmt.where(SummonOrder.assignee_id == assignee_id)

    stmt = stmt.order_by(SummonOrder.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/summary", summary="拘魂工单状态统计")
async def order_summary(
    user: CurrentUser = Depends(require_permission("summon:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SummonOrder)
    for cond in scope_conditions(user, SummonOrder):
        stmt = stmt.where(cond)
    rows = (await db.execute(stmt)).scalars().all()
    counter: dict[str, int] = {}
    for row in rows:
        counter[row.status] = counter.get(row.status, 0) + 1
    return resp_ok(
        {
            "total": len(rows),
            "by_status": [{"status": k, "count": v} for k, v in counter.items()],
            "finished": counter.get("已完成", 0),
            "running": counter.get("执行中", 0),
            "timeout": counter.get("已超时", 0),
            "abnormal": counter.get("异常", 0),
        }
    )


@router.get("/{order_id}", summary="工单详情")
async def get_order(
    order_id: int,
    user: CurrentUser = Depends(require_permission("summon:view")),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(SummonOrder, order_id)
    if order is None:
        raise NotFoundError("工单不存在")
    ensure_data_scope(user, order, "拘魂工单")
    return resp_ok(model_to_dict(order))


@router.post("", summary="开立拘魂工单")
async def create_order(
    payload: SummonCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("summon:create")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, payload.soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    if soul.status != SoulStatus.REGISTERED.value:
        raise ConflictError(f"亡魂当前状态为「{soul.status}」，仅「在册」可开立拘魂工单")

    existing = (
        await db.execute(
            select(SummonOrder).where(
                SummonOrder.soul_id == soul.id,
                SummonOrder.status.in_(["待派发", "执行中"]),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"该亡魂已有进行中的工单 {existing.order_no}")

    order_no = await next_code(db, SummonOrder, "order_no", "GH", 5)
    order = SummonOrder(
        order_no=order_no,
        soul_id=soul.id,
        soul_name=soul.name,
        region=soul.region,
        city_god_id=payload.city_god_id or soul.city_god_id,
        priority=payload.priority,
        status="待派发",
        death_type=payload.death_type,
        location=payload.location or soul.current_location,
        deadline_at=payload.deadline_at,
    )
    db.add(order)
    await db.flush()
    soul.summon_order_id = order.id

    await write_audit(
        db,
        action="create",
        module="拘魂工单",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="summon_order",
        resource_id=order.id,
        detail=f"开立工单 {order_no}：拘 {soul.name}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(order), msg="工单已开立")


@router.post("/{order_id}/dispatch", summary="派发工单给外勤鬼差")
async def dispatch_order(
    order_id: int,
    payload: DispatchIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("summon:dispatch")),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(SummonOrder, order_id)
    if order is None:
        raise NotFoundError("工单不存在")
    ensure_data_scope(user, order, "拘魂工单")
    if order.status not in ("待派发", "已超时", "异常"):
        raise ConflictError(f"工单状态为「{order.status}」，不可派发")

    assignee = await db.get(Officer, payload.assignee_id)
    if assignee is None:
        raise NotFoundError("鬼差不存在")
    if assignee.status != "在职":
        raise AppError(f"鬼差「{assignee.real_name}」当前状态为「{assignee.status}」，不可派单")

    order.assignee_id = assignee.id
    order.assignee_name = assignee.real_name
    order.status = "执行中"
    order.started_at = utcnow()
    if order.deadline_at is None:
        from datetime import timedelta

        order.deadline_at = utcnow() + timedelta(days=3)

    await write_audit(
        db,
        action="dispatch",
        module="拘魂工单",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="summon_order",
        resource_id=order.id,
        detail=f"派发 {order.order_no} 给 {assignee.real_name}（{assignee.title}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(order), msg="已派发")


@router.post("/{order_id}/finish", summary="完成拘魂并同步亡魂状态")
async def finish_order(
    order_id: int,
    payload: SummonFinishIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("summon:execute")),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(SummonOrder, order_id)
    if order is None:
        raise NotFoundError("工单不存在")
    ensure_data_scope(user, order, "拘魂工单")
    if order.status not in ("执行中", "已超时"):
        raise ConflictError(f"工单状态为「{order.status}」，不可完成")

    soul = await db.get(Soul, order.soul_id) if order.soul_id else None
    if soul is None:
        raise NotFoundError("工单关联亡魂不存在")

    result = await change_soul_status(db, soul, "summon", reason=payload.result)

    order.status = "已完成"
    order.finished_at = utcnow()
    order.result = payload.result

    await write_audit(
        db,
        action="finish",
        module="拘魂工单",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="summon_order",
        resource_id=order.id,
        detail=f"完成 {order.order_no}：{payload.result}；亡魂状态 → {result['to_status']}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"order": model_to_dict(order), "transition": result}, msg="勾魂完成")


@router.post("/{order_id}/exception", summary="登记工单异常")
async def exception_order(
    order_id: int,
    payload: SummonExceptionIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("summon:execute")),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(SummonOrder, order_id)
    if order is None:
        raise NotFoundError("工单不存在")
    if order.status in ("已完成", "已撤销"):
        raise ConflictError(f"工单状态为「{order.status}」，不可登记异常")

    order.status = "异常"
    order.abnormal_reason = payload.reason

    await write_audit(
        db,
        action="exception",
        module="拘魂工单",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="summon_order",
        resource_id=order.id,
        detail=f"工单 {order.order_no} 异常：{payload.reason}",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(order), msg="异常已登记")


@router.post("/{order_id}/cancel", summary="撤销工单")
async def cancel_order(
    order_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("summon:dispatch")),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(SummonOrder, order_id)
    if order is None:
        raise NotFoundError("工单不存在")
    if order.status in ("已完成", "已撤销"):
        raise ConflictError(f"工单状态为「{order.status}」，不可撤销")
    order.status = "已撤销"
    await write_audit(
        db,
        action="cancel",
        module="拘魂工单",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="summon_order",
        resource_id=order.id,
        detail=f"撤销工单 {order.order_no}",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(order), msg="已撤销")
