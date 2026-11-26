"""RBAC 管理：角色、权限点、菜单。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, client_ip, client_ua, require_permission
from app.core.response import ConflictError, NotFoundError, resp_ok
from app.core.utils import model_to_dict, models_to_list
from app.database import get_db
from app.models import Menu, Permission, Role, RolePermission
from app.schemas import AssignPermissionIn, MenuCreateIn, MenuUpdateIn, RoleCreateIn, RoleUpdateIn
from app.services.audit import write_audit

roles_router = APIRouter(prefix="/roles", tags=["角色管理"])
perms_router = APIRouter(prefix="/permissions", tags=["权限点"])
menus_router = APIRouter(prefix="/menus", tags=["菜单管理"])


def _build_menu_tree(rows: list[Menu]) -> list[dict]:
    nodes = {row.id: {**model_to_dict(row), "children": []} for row in rows}
    tree: list[dict] = []
    for row in rows:
        node = nodes[row.id]
        parent = nodes.get(row.parent_id) if row.parent_id else None
        if parent is not None:
            parent["children"].append(node)
        else:
            tree.append(node)

    def _sort(items: list[dict]) -> None:
        items.sort(key=lambda x: (x.get("sort") or 0, x.get("id") or 0))
        for item in items:
            _sort(item["children"])

    _sort(tree)
    return tree


# ---------------------------- 角色 ----------------------------
@roles_router.get("", summary="角色列表")
async def list_roles(
    user: CurrentUser = Depends(require_permission("role:view")),
    db: AsyncSession = Depends(get_db),
):
    roles = (await db.execute(select(Role).order_by(Role.sort.asc(), Role.id.asc()))).scalars().all()
    links = (await db.execute(select(RolePermission))).scalars().all()
    perms = {p.id: p.code for p in (await db.execute(select(Permission))).scalars().all()}
    grouped: dict[int, list[str]] = {}
    for link in links:
        code = perms.get(link.permission_id)
        if code:
            grouped.setdefault(link.role_id, []).append(code)
    data = []
    for role in roles:
        row = model_to_dict(role)
        row["permissions"] = sorted(grouped.get(role.id, []))
        row["permission_count"] = len(row["permissions"])
        data.append(row)
    return resp_ok(data)


@roles_router.get("/{role_id}", summary="角色详情")
async def get_role(
    role_id: int,
    user: CurrentUser = Depends(require_permission("role:view")),
    db: AsyncSession = Depends(get_db),
):
    role = await db.get(Role, role_id)
    if role is None:
        raise NotFoundError("角色不存在")
    codes = (
        await db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
    ).scalars().all()
    data = model_to_dict(role)
    data["permissions"] = sorted(codes)
    return resp_ok(data)


@roles_router.post("", summary="新增角色")
async def create_role(
    payload: RoleCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("role:create")),
    db: AsyncSession = Depends(get_db),
):
    exists = (await db.execute(select(Role).where(Role.code == payload.code))).scalar_one_or_none()
    if exists is not None:
        raise ConflictError(f"角色编码「{payload.code}」已存在")
    role = Role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        data_scope=payload.data_scope,
        is_builtin=False,
        sort=payload.sort,
        status="在职",
    )
    db.add(role)
    await db.flush()
    await write_audit(
        db,
        action="create",
        module="角色管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="role",
        resource_id=role.id,
        detail=f"新增角色 {role.code}（{role.name}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(role), msg="角色已创建")


@roles_router.put("/{role_id}", summary="编辑角色")
async def update_role(
    role_id: int,
    payload: RoleUpdateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("role:update")),
    db: AsyncSession = Depends(get_db),
):
    role = await db.get(Role, role_id)
    if role is None:
        raise NotFoundError("角色不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    await write_audit(
        db,
        action="update",
        module="角色管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="role",
        resource_id=role.id,
        detail=f"编辑角色 {role.code}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(role), msg="已保存")


@roles_router.post("/{role_id}/permissions", summary="角色授权（覆盖式）")
async def assign_permissions(
    role_id: int,
    payload: AssignPermissionIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("role:assign")),
    db: AsyncSession = Depends(get_db),
):
    role = await db.get(Role, role_id)
    if role is None:
        raise NotFoundError("角色不存在")
    if role.code == "SUPER_ADMIN":
        raise ConflictError("酆都大帝角色拥有全部权限，不可编辑授权")

    valid_ids = set()
    if payload.permission_ids:
        valid_ids = set(
            (await db.execute(select(Permission.id).where(Permission.id.in_(payload.permission_ids)))).scalars().all()
        )
        if len(valid_ids) != len(set(payload.permission_ids)):
            raise ConflictError("存在非法的权限点 ID")

    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for pid in valid_ids:
        db.add(RolePermission(role_id=role_id, permission_id=pid))

    await write_audit(
        db,
        action="assign",
        module="角色管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="role",
        resource_id=role.id,
        detail=f"角色 {role.code} 授权 {len(valid_ids)} 个权限点",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"role_id": role_id, "permission_count": len(valid_ids)}, msg="授权已更新")


# ---------------------------- 权限点 ----------------------------
@perms_router.get("", summary="权限点列表（按模块分组）")
async def list_permissions(
    module: str = Query(""),
    type: str = Query(""),
    user: CurrentUser = Depends(require_permission("permission:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Permission).order_by(Permission.id.asc())
    if module:
        stmt = stmt.where(Permission.module == module)
    if type:
        stmt = stmt.where(Permission.type == type)
    rows = (await db.execute(stmt)).scalars().all()
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row.module, []).append(model_to_dict(row))
    return resp_ok(
        {
            "total": len(rows),
            "modules": [{"module": k, "items": v} for k, v in groups.items()],
            "flat": models_to_list(rows),
        }
    )


# ---------------------------- 菜单 ----------------------------
@menus_router.get("", summary="菜单树（全量，管理端）")
async def list_menus(
    user: CurrentUser = Depends(require_permission("menu:view")),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Menu))).scalars().all()
    return resp_ok(_build_menu_tree(list(rows)))


@menus_router.post("", summary="新增菜单")
async def create_menu(
    payload: MenuCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("menu:create")),
    db: AsyncSession = Depends(get_db),
):
    exists = (await db.execute(select(Menu).where(Menu.code == payload.code))).scalar_one_or_none()
    if exists is not None:
        raise ConflictError(f"菜单编码「{payload.code}」已存在")
    if payload.parent_id and await db.get(Menu, payload.parent_id) is None:
        raise NotFoundError("父级菜单不存在")
    menu = Menu(**payload.model_dump())
    db.add(menu)
    await db.flush()
    await write_audit(
        db,
        action="create",
        module="菜单管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="menu",
        resource_id=menu.id,
        detail=f"新增菜单 {menu.code}（{menu.name}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(menu), msg="菜单已创建")


@menus_router.put("/{menu_id}", summary="编辑菜单")
async def update_menu(
    menu_id: int,
    payload: MenuUpdateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("menu:update")),
    db: AsyncSession = Depends(get_db),
):
    menu = await db.get(Menu, menu_id)
    if menu is None:
        raise NotFoundError("菜单不存在")
    data = payload.model_dump(exclude_unset=True)
    if data.get("parent_id") == menu_id:
        raise ConflictError("父级菜单不可为自身")
    for field, value in data.items():
        setattr(menu, field, value)
    await write_audit(
        db,
        action="update",
        module="菜单管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="menu",
        resource_id=menu.id,
        detail=f"编辑菜单 {menu.code}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(menu), msg="已保存")
