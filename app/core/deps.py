"""依赖注入：当前登录鬼差 + 四级 RBAC（菜单 / 按钮 / 接口 / 数据域）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_cache
from app.cache.base import CacheBackend
from app.core.constants import DataScope, SUPER_ADMIN_ROLE
from app.core.response import ForbiddenError, UnauthorizedError
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.database import get_db
from app.models import Officer, Permission, Role, RolePermission

bearer_scheme = HTTPBearer(auto_error=False)

TOKEN_BLACKLIST_PREFIX = "auth:blacklist:"
PERM_CACHE_PREFIX = "rbac:perms:"


@dataclass
class CurrentUser:
    officer: Officer
    role: Role
    permissions: set[str] = field(default_factory=set)

    @property
    def is_super(self) -> bool:
        return self.role.code == SUPER_ADMIN_ROLE

    @property
    def data_scope(self) -> str:
        return self.officer.data_scope or self.role.data_scope or DataScope.REGION.value

    def has(self, code: str) -> bool:
        return self.is_super or code in self.permissions

    def has_any(self, codes: list[str]) -> bool:
        return self.is_super or any(c in self.permissions for c in codes)


async def _load_permission_codes(
    db: AsyncSession, cache: CacheBackend, role_id: int
) -> set[str]:
    cache_key = f"{PERM_CACHE_PREFIX}{role_id}"
    cached = await cache.get_json(cache_key)
    if isinstance(cached, list):
        return set(cached)

    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    codes = list((await db.execute(stmt)).scalars().all())
    await cache.set_json(cache_key, codes, ttl=300)
    return set(codes)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    cache: CacheBackend = Depends(get_cache),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("缺少认证令牌，请先登录")

    token = credentials.credentials
    payload = decode_token(token, expect_type=TOKEN_TYPE_ACCESS)

    jti = payload.get("jti", "")
    if jti and await cache.exists(f"{TOKEN_BLACKLIST_PREFIX}{jti}"):
        raise UnauthorizedError("该令牌已登出，请重新登录")

    try:
        officer_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("令牌载荷异常") from exc

    officer = await db.get(Officer, officer_id)
    if officer is None:
        raise UnauthorizedError("鬼差账号不存在")
    if officer.status != "在职":
        raise ForbiddenError(f"账号状态为「{officer.status}」，禁止登录使用")

    role = await db.get(Role, officer.role_id)
    if role is None:
        raise ForbiddenError("账号未关联有效角色")

    permissions = await _load_permission_codes(db, cache, role.id)
    request.state.officer_id = officer.id
    request.state.officer_name = officer.real_name
    return CurrentUser(officer=officer, role=role, permissions=permissions)


def require_permission(*codes: str, mode: str = "all"):
    """接口级鉴权依赖工厂。mode=all 需全部满足，any 满足其一即可。"""

    async def _checker(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.is_super:
            return current
        if mode == "any":
            if not current.has_any(list(codes)):
                raise ForbiddenError(f"缺少权限：{' / '.join(codes)}")
        else:
            missing = [c for c in codes if c not in current.permissions]
            if missing:
                raise ForbiddenError(f"缺少权限：{' / '.join(missing)}")
        return current

    return _checker


def scope_conditions(
    user: CurrentUser,
    model: Any,
    region_attr: str = "region",
    city_attr: str | None = "city_god_id",
) -> list[Any]:
    """数据域过滤：ALL 不限制；REGION 按鬼域；SELF 按所属城隍网点。"""
    scope = user.data_scope
    if user.is_super or scope == DataScope.ALL.value:
        return []

    region_col = getattr(model, region_attr, None)
    if scope == DataScope.REGION.value:
        return [region_col == user.officer.region] if region_col is not None else []

    # SELF：本网点数据；未绑定网点时退化为本鬼域
    conds: list[Any] = []
    city_col = getattr(model, city_attr, None) if city_attr else None
    if city_col is not None and user.officer.city_god_id:
        conds.append(city_col == user.officer.city_god_id)
    if region_col is not None:
        conds.append(region_col == user.officer.region)
    return [or_(*conds)] if conds else []


def ensure_data_scope(user: CurrentUser, obj: Any, what: str = "资源") -> None:
    """单条数据越权校验：不在本人数据域内直接 403。"""
    scope = user.data_scope
    if user.is_super or scope == DataScope.ALL.value:
        return
    if scope == DataScope.REGION.value:
        if getattr(obj, "region", user.officer.region) != user.officer.region:
            raise ForbiddenError(f"无权访问其他鬼域的{what}")
        return
    city_id = getattr(obj, "city_god_id", None)
    if city_id is not None and user.officer.city_god_id:
        if city_id != user.officer.city_god_id:
            raise ForbiddenError(f"无权访问其他网点的{what}")
        return
    if getattr(obj, "region", user.officer.region) != user.officer.region:
        raise ForbiddenError(f"无权访问其他鬼域的{what}")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def client_ua(request: Request) -> str:
    return request.headers.get("user-agent", "")[:255]
