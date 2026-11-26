"""鬼差账号管理。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, client_ip, client_ua, require_permission, scope_conditions
from app.core.response import ConflictError, NotFoundError, page_resp, resp_ok
from app.core.security import hash_password
from app.core.utils import like_filter, model_to_dict, models_to_list, paginate
from app.database import get_db
from app.models import CityGod, Officer, Role
from app.schemas import OfficerCreateIn, OfficerUpdateIn, ResetPasswordIn, StatusIn
from app.services.audit import write_audit

router = APIRouter(prefix="/officers", tags=["鬼差账号"])


async def _resolve_role(db: AsyncSession, role_id: int | None, role_code: str | None) -> Role:
    role = None
    if role_id:
        role = await db.get(Role, role_id)
    elif role_code:
        role = (await db.execute(select(Role).where(Role.code == role_code))).scalar_one_or_none()
    if role is None:
        raise NotFoundError("角色不存在")
    return role


@router.get("", summary="鬼差列表")
async def list_officers(
    keyword: str = Query(""),
    role_id: int | None = Query(None),
    region: str = Query(""),
    city_god_id: int | None = Query(None),
    status: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("officer:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Officer)
    for cond in scope_conditions(user, Officer):
        stmt = stmt.where(cond)
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(Officer.username, keyword),
                like_filter(Officer.real_name, keyword),
                like_filter(Officer.title, keyword),
            )
        )
    if role_id:
        stmt = stmt.where(Officer.role_id == role_id)
    if region:
        stmt = stmt.where(Officer.region == region)
    if city_god_id:
        stmt = stmt.where(Officer.city_god_id == city_god_id)
    if status:
        stmt = stmt.where(Officer.status == status)

    stmt = stmt.order_by(Officer.id.asc())
    items, total = await paginate(db, stmt, page, page_size)
    roles = {r.id: r for r in (await db.execute(select(Role))).scalars().all()}
    data = []
    for officer in items:
        row = model_to_dict(officer, exclude={"password_hash"})
        role = roles.get(officer.role_id)
        row["role_code"] = role.code if role else ""
        row["role_name"] = role.name if role else ""
        data.append(row)
    return page_resp(data, total, page, page_size)


@router.get("/{officer_id}", summary="鬼差详情")
async def get_officer(
    officer_id: int,
    user: CurrentUser = Depends(require_permission("officer:view")),
    db: AsyncSession = Depends(get_db),
):
    officer = await db.get(Officer, officer_id)
    if officer is None:
        raise NotFoundError("鬼差不存在")
    row = model_to_dict(officer, exclude={"password_hash"})
    role = await db.get(Role, officer.role_id) if officer.role_id else None
    row["role_code"] = role.code if role else ""
    row["role_name"] = role.name if role else ""
    return resp_ok(row)


@router.post("", summary="新增鬼差")
async def create_officer(
    payload: OfficerCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("officer:create")),
    db: AsyncSession = Depends(get_db),
):
    exists = (
        await db.execute(select(Officer).where(Officer.username == payload.username))
    ).scalar_one_or_none()
    if exists is not None:
        raise ConflictError(f"账号「{payload.username}」已存在")

    role = await _resolve_role(db, payload.role_id, None)
    if payload.city_god_id and await db.get(CityGod, payload.city_god_id) is None:
        raise NotFoundError("城隍网点不存在")

    officer = Officer(
        username=payload.username,
        password_hash=hash_password(payload.password),
        real_name=payload.real_name,
        title=payload.title,
        role_id=role.id,
        region=payload.region,
        city_god_id=payload.city_god_id,
        data_scope=role.data_scope,
        phone=payload.phone,
        email=payload.email,
        status="在职",
        remark=payload.remark,
    )
    db.add(officer)
    await db.flush()

    await write_audit(
        db,
        action="create",
        module="鬼差账号",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="officer",
        resource_id=officer.id,
        detail=f"新增鬼差 {payload.username}（{payload.real_name}·{role.name}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(officer, exclude={"password_hash"}), msg="鬼差已入职")


@router.put("/{officer_id}", summary="编辑鬼差")
async def update_officer(
    officer_id: int,
    payload: OfficerUpdateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("officer:update")),
    db: AsyncSession = Depends(get_db),
):
    officer = await db.get(Officer, officer_id)
    if officer is None:
        raise NotFoundError("鬼差不存在")

    data = payload.model_dump(exclude_unset=True)
    role_id = data.pop("role_id", None)
    if role_id:
        role = await _resolve_role(db, role_id, None)
        officer.role_id = role.id
        officer.data_scope = role.data_scope
    for field, value in data.items():
        setattr(officer, field, value)

    await write_audit(
        db,
        action="update",
        module="鬼差账号",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="officer",
        resource_id=officer.id,
        detail=f"编辑鬼差 {officer.username}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(officer, exclude={"password_hash"}), msg="已保存")


@router.post("/{officer_id}/reset-password", summary="重置密码")
async def reset_password(
    officer_id: int,
    payload: ResetPasswordIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("officer:reset")),
    db: AsyncSession = Depends(get_db),
):
    officer = await db.get(Officer, officer_id)
    if officer is None:
        raise NotFoundError("鬼差不存在")
    officer.password_hash = hash_password(payload.new_password)
    await write_audit(
        db,
        action="reset_password",
        module="鬼差账号",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="officer",
        resource_id=officer.id,
        detail=f"重置 {officer.username} 密码",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(None, msg="密码已重置")


@router.post("/{officer_id}/status", summary="启用/停用鬼差")
async def set_officer_status(
    officer_id: int,
    payload: StatusIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("officer:status")),
    db: AsyncSession = Depends(get_db),
):
    officer = await db.get(Officer, officer_id)
    if officer is None:
        raise NotFoundError("鬼差不存在")
    if officer.id == user.officer.id and payload.status != "在职":
        raise ConflictError("不可停用当前登录账号")
    officer.status = payload.status
    await write_audit(
        db,
        action="status",
        module="鬼差账号",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="officer",
        resource_id=officer.id,
        detail=f"{officer.username} 状态 → {payload.status}",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(officer, exclude={"password_hash"}), msg="状态已更新")
