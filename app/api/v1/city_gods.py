"""城隍网点：网点点位、容量与所辖亡魂统计。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, client_ip, client_ua, require_permission, scope_conditions
from app.core.response import ConflictError, NotFoundError, resp_ok
from app.core.utils import like_filter, model_to_dict, models_to_list
from app.database import get_db
from app.models import CityGod, Soul
from app.schemas import CityGodCreateIn, CityGodUpdateIn
from app.services.audit import write_audit

router = APIRouter(prefix="/city-gods", tags=["城隍网点"])


@router.get("", summary="城隍网点列表（含在册亡魂数）")
async def list_city_gods(
    keyword: str = Query(""),
    region: str = Query(""),
    level: str = Query(""),
    status: str = Query(""),
    user: CurrentUser = Depends(require_permission("citygod:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CityGod)
    if keyword:
        stmt = stmt.where(
            or_(like_filter(CityGod.code, keyword), like_filter(CityGod.name, keyword))
        )
    if region:
        stmt = stmt.where(CityGod.region == region)
    if level:
        stmt = stmt.where(CityGod.level == level)
    if status:
        stmt = stmt.where(CityGod.status == status)
    rows = (await db.execute(stmt.order_by(CityGod.id.asc()))).scalars().all()

    counts = dict(
        (
            await db.execute(
                select(Soul.city_god_id, func.count(Soul.id))
                .where(Soul.is_deleted.is_(False), Soul.city_god_id.is_not(None))
                .group_by(Soul.city_god_id)
            )
        ).all()
    )
    data = []
    for row in rows:
        item = model_to_dict(row)
        item["soul_count"] = counts.get(row.id, 0)
        data.append(item)
    return resp_ok(data)


@router.get("/{city_god_id}", summary="网点详情")
async def get_city_god(
    city_god_id: int,
    user: CurrentUser = Depends(require_permission("citygod:view")),
    db: AsyncSession = Depends(get_db),
):
    node = await db.get(CityGod, city_god_id)
    if node is None:
        raise NotFoundError("城隍网点不存在")
    item = model_to_dict(node)
    item["soul_count"] = (
        await db.execute(
            select(func.count(Soul.id)).where(Soul.city_god_id == city_god_id, Soul.is_deleted.is_(False))
        )
    ).scalar_one()
    return resp_ok(item)


@router.post("", summary="新增网点")
async def create_city_god(
    payload: CityGodCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("citygod:create")),
    db: AsyncSession = Depends(get_db),
):
    exists = (await db.execute(select(CityGod).where(CityGod.code == payload.code))).scalar_one_or_none()
    if exists is not None:
        raise ConflictError(f"网点编码「{payload.code}」已存在")
    if payload.parent_id and await db.get(CityGod, payload.parent_id) is None:
        raise NotFoundError("上级网点不存在")
    node = CityGod(**payload.model_dump(), soul_count=0)
    db.add(node)
    await db.flush()
    await write_audit(
        db,
        action="create",
        module="城隍网点",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="city_god",
        resource_id=node.id,
        detail=f"新增网点 {node.code}（{node.name}·{node.level}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(node), msg="网点已设立")


@router.put("/{city_god_id}", summary="编辑网点")
async def update_city_god(
    city_god_id: int,
    payload: CityGodUpdateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("citygod:update")),
    db: AsyncSession = Depends(get_db),
):
    node = await db.get(CityGod, city_god_id)
    if node is None:
        raise NotFoundError("城隍网点不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    await write_audit(
        db,
        action="update",
        module="城隍网点",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="city_god",
        resource_id=node.id,
        detail=f"编辑网点 {node.code}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(node), msg="已保存")
