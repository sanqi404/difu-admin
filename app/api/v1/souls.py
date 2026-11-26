"""亡魂主档：查询、建档、编辑、状态机流转、时间轴。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    SOUL_ACTIONS,
    SOUL_FINAL_STATUS,
    SOUL_STATUS_LIST,
    SoulStatus,
    allowed_next_status,
)
from app.core.deps import (
    CurrentUser,
    client_ip,
    client_ua,
    ensure_data_scope,
    get_current_user,
    require_permission,
    scope_conditions,
)
from app.core.response import AppError, ConflictError, NotFoundError, page_resp, resp_ok
from app.core.utils import like_filter, model_to_dict, models_to_list, paginate
from app.database import get_db, utcnow
from app.models import KarmaRecord, LifeBook, Reincarnation, Soul, SummonOrder, TrialRecord
from app.models.punishment import Punishment
from app.schemas import SoulCreateIn, SoulTransitionIn, SoulUpdateIn
from app.services.audit import write_audit
from app.services.numbering import next_code
from app.services.state_machine import change_soul_status

router = APIRouter(prefix="/souls", tags=["亡魂主档"])


def _base_stmt(user: CurrentUser):
    stmt = select(Soul).where(Soul.is_deleted.is_(False))
    for cond in scope_conditions(user, Soul):
        stmt = stmt.where(cond)
    return stmt


@router.get("", summary="亡魂列表（分页 + 多条件）")
async def list_souls(
    keyword: str = Query("", description="姓名 / 编号 / 籍贯模糊搜索"),
    status: str = Query("", description="状态精确过滤"),
    region: str = Query("", description="鬼域"),
    city_god_id: int | None = Query(None),
    gender: str = Query(""),
    sin_level: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("soul:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = _base_stmt(user)
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(Soul.name, keyword),
                like_filter(Soul.soul_no, keyword),
                like_filter(Soul.native_place, keyword),
            )
        )
    if status:
        stmt = stmt.where(Soul.status == status)
    if region:
        stmt = stmt.where(Soul.region == region)
    if city_god_id:
        stmt = stmt.where(Soul.city_god_id == city_god_id)
    if gender:
        stmt = stmt.where(Soul.gender == gender)
    if sin_level:
        stmt = stmt.where(Soul.sin_level == sin_level)

    stmt = stmt.order_by(Soul.updated_at.desc(), Soul.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/status-options", summary="亡魂状态集与可用动作字典")
async def status_options():
    actions = [
        {"name": a.action_name, "code": a.action, "from": a.src, "to": a.dst}
        for a in SOUL_ACTIONS.values()
    ]
    return resp_ok({"statuses": SOUL_STATUS_LIST, "final_status": sorted(SOUL_FINAL_STATUS), "actions": actions})


@router.get("/summary", summary="亡魂状态分布统计")
async def soul_summary(
    user: CurrentUser = Depends(require_permission("soul:view")),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(_base_stmt(user))).scalars().all()
    counter: dict[str, int] = {s: 0 for s in SOUL_STATUS_LIST}
    for soul in rows:
        counter[soul.status] = counter.get(soul.status, 0) + 1
    return resp_ok(
        {
            "total": len(rows),
            "by_status": [{"status": k, "count": v} for k, v in counter.items()],
            "in_prison": counter.get(SoulStatus.SERVING.value, 0),
            "wait_trial": counter.get(SoulStatus.PENDING_TRIAL.value, 0),
        }
    )


@router.get("/{soul_id}", summary="亡魂详情")
async def get_soul(
    soul_id: int,
    user: CurrentUser = Depends(require_permission("soul:view")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    ensure_data_scope(user, soul, "亡魂档案")
    data = model_to_dict(soul)
    data["allowed_actions"] = [
        {
            "action": t["action"],
            "name": t["action_name"],
            "to": soul.prev_status if t["action"] == "unfreeze" else t["status"],
        }
        for t in allowed_next_status(soul.status)
    ]
    return resp_ok(data)


@router.post("", summary="亡魂建档")
async def create_soul(
    payload: SoulCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("soul:create")),
    db: AsyncSession = Depends(get_db),
):
    soul_no = await next_code(db, Soul, "soul_no", "HD", 4)
    soul = Soul(
        soul_no=soul_no,
        name=payload.name,
        gender=payload.gender,
        age=payload.age,
        birth_date=payload.birth_date,
        death_date=payload.death_date,
        native_place=payload.native_place,
        region=payload.region or user.officer.region,
        death_type=payload.death_type,
        city_god_id=payload.city_god_id or user.officer.city_god_id,
        karma_score=payload.karma_score,
        sin_level=payload.sin_level,
        life_book_no=payload.life_book_no,
        current_location=payload.current_location,
        remark=payload.remark,
        status=SoulStatus.REGISTERED.value,
        prev_status="",
    )
    db.add(soul)
    await db.flush()
    await write_audit(
        db,
        action="create",
        module="亡魂主档",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="soul",
        resource_id=soul.id,
        detail=f"为 {soul.name}（{soul.soul_no}）建档",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(soul), msg="建档成功")


@router.put("/{soul_id}", summary="亡魂信息编辑")
async def update_soul(
    soul_id: int,
    payload: SoulUpdateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("soul:update")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    ensure_data_scope(user, soul, "亡魂档案")

    changed: list[str] = []
    for field, value in payload.model_dump(exclude_unset=True).items():
        if getattr(soul, field) != value:
            setattr(soul, field, value)
            changed.append(field)
    if not changed:
        return resp_ok(model_to_dict(soul), msg="无变更")

    await write_audit(
        db,
        action="update",
        module="亡魂主档",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="soul",
        resource_id=soul.id,
        detail=f"修改字段：{', '.join(changed)}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(soul), msg="已保存")


@router.delete("/{soul_id}", summary="亡魂逻辑删除（记篡改级告警）")
async def delete_soul(
    soul_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("soul:delete")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    ensure_data_scope(user, soul, "亡魂档案")
    soul.is_deleted = True
    soul.status = SoulStatus.CANCELLED.value
    soul.current_location = "归档阁"
    await write_audit(
        db,
        action="delete",
        module="亡魂主档",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="soul",
        resource_id=soul.id,
        detail=f"逻辑删除亡魂 {soul.name}（{soul.soul_no}）",
        level="篡改告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"id": soul_id}, msg="已删除（逻辑归档）")


@router.post("/{soul_id}/transition", summary="亡魂状态流转（禁止跳步）")
async def transition_soul(
    soul_id: int,
    payload: SoulTransitionIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("soul:transfer")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    ensure_data_scope(user, soul, "亡魂档案")

    result = await change_soul_status(db, soul, payload.action, reason=payload.reason)
    await write_audit(
        db,
        action=f"transition:{payload.action}",
        module="亡魂主档",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="soul",
        resource_id=soul.id,
        detail=(
            f"{soul.name} 状态 {result['from_status']} → {result['to_status']}"
            f"（{result['action_name']}）{('；说明：' + payload.reason) if payload.reason else ''}"
        ),
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({**result, "soul": model_to_dict(soul)}, msg=f"已流转至「{result['to_status']}」")


@router.get("/{soul_id}/timeline", summary="亡魂全生命周期时间轴")
async def soul_timeline(
    soul_id: int,
    user: CurrentUser = Depends(require_permission("soul:view")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    ensure_data_scope(user, soul, "亡魂档案")

    life_books = (
        await db.execute(
            select(LifeBook).where(LifeBook.soul_id == soul_id).order_by(LifeBook.id)
        )
    ).scalars().all()
    orders = (
        await db.execute(
            select(SummonOrder).where(SummonOrder.soul_id == soul_id).order_by(SummonOrder.id)
        )
    ).scalars().all()
    trials = (
        await db.execute(
            select(TrialRecord)
            .where(TrialRecord.soul_id == soul_id)
            .order_by(TrialRecord.court_level)
        )
    ).scalars().all()
    punishments = (
        await db.execute(
            select(Punishment).where(Punishment.soul_id == soul_id).order_by(Punishment.id)
        )
    ).scalars().all()
    karmas = (
        await db.execute(
            select(KarmaRecord).where(KarmaRecord.soul_id == soul_id).order_by(KarmaRecord.id)
        )
    ).scalars().all()
    reincarnations = (
        await db.execute(
            select(Reincarnation)
            .where(Reincarnation.soul_id == soul_id)
            .order_by(Reincarnation.id)
        )
    ).scalars().all()

    return resp_ok(
        {
            "soul": model_to_dict(soul),
            "life_books": models_to_list(life_books),
            "summon_orders": models_to_list(orders),
            "trials": models_to_list(trials),
            "punishments": models_to_list(punishments),
            "karmas": models_to_list(karmas),
            "reincarnations": models_to_list(reincarnations),
        }
    )


@router.post("/{soul_id}/restore", summary="从逻辑删除恢复")
async def restore_soul(
    soul_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("soul:update")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, soul_id)
    if soul is None:
        raise NotFoundError("亡魂不存在")
    if not soul.is_deleted:
        raise ConflictError("该亡魂未被删除")
    soul.is_deleted = False
    soul.status = SoulStatus.REGISTERED.value
    soul.current_location = "阴司在册"
    await write_audit(
        db,
        action="restore",
        module="亡魂主档",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="soul",
        resource_id=soul.id,
        detail=f"恢复亡魂 {soul.name}（{soul.soul_no}）至「在册」",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(soul), msg="已恢复")
