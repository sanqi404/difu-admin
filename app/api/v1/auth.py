"""认证：图形验证码、登录、刷新、登出、当前用户信息与动态菜单。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_cache
from app.cache.base import CacheBackend
from app.config import settings
from app.core.captcha import create_captcha, verify_captcha
from app.core.constants import ROLE_DEFS
from app.core.deps import (
    TOKEN_BLACKLIST_PREFIX,
    CurrentUser,
    client_ip,
    client_ua,
    get_current_user,
)
from app.core.response import AppError, UnauthorizedError, resp_ok
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    bearer_jti,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_remaining_seconds,
    verify_password,
)
from app.core.utils import model_to_dict
from app.database import get_db, utcnow
from app.models import Menu, Officer, Role
from app.schemas import ChangePasswordIn, LoginIn, RefreshIn
from app.services.audit import safe_write_audit, write_audit

router = APIRouter(prefix="/auth", tags=["认证"])

LOGIN_FAIL_PREFIX = "login:fail:"
LOGIN_MAX_FAIL = 5
LOGIN_LOCK_SECONDS = 300


@router.get("/captcha", summary="获取图形验证码")
async def get_captcha(cache: CacheBackend = Depends(get_cache)):
    data = await create_captcha(cache)
    return resp_ok(data, msg="验证码已生成")


def _profile(user: CurrentUser) -> dict:
    officer = user.officer
    role = user.role
    return {
        "id": officer.id,
        "username": officer.username,
        "real_name": officer.real_name,
        "title": officer.title,
        "role_id": role.id,
        "role_code": role.code,
        "role_name": role.name,
        "region": officer.region,
        "city_god_id": officer.city_god_id,
        "data_scope": user.data_scope,
        "avatar": next((rd.name for rd in ROLE_DEFS if rd.code == role.code), role.name),
        "status": officer.status,
        "permissions": sorted(user.permissions) if not user.is_super else ["*"],
        "is_super": user.is_super,
        "last_login_at": officer.last_login_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if officer.last_login_at
        else None,
    }


@router.post("/login", summary="账号密码 + 图形验证码登录")
async def login(
    payload: LoginIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: CacheBackend = Depends(get_cache),
):
    fail_key = f"{LOGIN_FAIL_PREFIX}{payload.username}"
    fail_count = int(await cache.get(fail_key) or 0)
    if fail_count >= LOGIN_MAX_FAIL:
        raise AppError(
            f"连续 {LOGIN_MAX_FAIL} 次密码错误，账号已临时锁定，请 {LOGIN_LOCK_SECONDS // 60} 分钟后再试",
            code=429,
            http_status=429,
        )

    captcha_ok = await verify_captcha(cache, payload.captcha_id, payload.captcha_code)
    if not captcha_ok and settings.is_dev and settings.CAPTCHA_DEV_CODE and payload.captcha_code == settings.CAPTCHA_DEV_CODE:
        captcha_ok = True
        logger.warning(f"dev 模式验证码旁路通过：username={payload.username}")
    if not captcha_ok:
        raise AppError("验证码错误或已过期，请刷新后重试", code=400, http_status=400)

    officer = (
        await db.execute(select(Officer).where(Officer.username == payload.username))
    ).scalar_one_or_none()

    ip = client_ip(request)
    if officer is None or not verify_password(payload.password, officer.password_hash):
        await cache.set(fail_key, str(fail_count + 1), ttl=LOGIN_LOCK_SECONDS)
        await write_audit(
            db,
            action="login_fail",
            module="认证",
            officer_name=payload.username,
            detail=f"登录失败：账号或密码错误（第 {fail_count + 1} 次）",
            level="告警",
            ip=ip,
            user_agent=client_ua(request),
        )
        await db.commit()
        raise UnauthorizedError("账号或密码错误")

    if officer.status != "在职":
        await write_audit(
            db,
            action="login_reject",
            module="认证",
            officer_id=officer.id,
            officer_name=officer.real_name,
            detail=f"账号状态为「{officer.status}」，拒绝登录",
            level="告警",
            ip=ip,
            user_agent=client_ua(request),
        )
        await db.commit()
        raise AppError(f"账号状态为「{officer.status}」，请联系崔判官处理", code=403, http_status=403)

    role = await db.get(Role, officer.role_id)
    if role is None:
        raise AppError("账号未绑定角色，禁止登录", code=403, http_status=403)

    await cache.delete(fail_key)
    officer.last_login_at = utcnow()
    officer.last_login_ip = ip

    await write_audit(
        db,
        action="login",
        module="认证",
        officer_id=officer.id,
        officer_name=officer.real_name,
        role_name=role.name,
        resource="officer",
        resource_id=officer.id,
        detail=f"{officer.real_name}（{role.name}）登录幽冥后台",
        ip=ip,
        user_agent=client_ua(request),
    )
    await db.commit()

    access_token = create_access_token(officer.id, officer.username, role.code)
    refresh_token = create_refresh_token(officer.id, officer.username, role.code)

    return resp_ok(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "profile": {
                "id": officer.id,
                "username": officer.username,
                "real_name": officer.real_name,
                "title": officer.title,
                "role_code": role.code,
                "role_name": role.name,
                "region": officer.region,
                "data_scope": officer.data_scope or role.data_scope,
                "is_super": role.code == "SUPER_ADMIN",
            },
        },
        msg="登录成功，阴阳通行",
    )


@router.post("/refresh", summary="刷新访问令牌")
async def refresh(
    payload: RefreshIn,
    db: AsyncSession = Depends(get_db),
):
    token_payload = decode_token(payload.refresh_token, expect_type=TOKEN_TYPE_REFRESH)
    officer = await db.get(Officer, int(token_payload["sub"]))
    if officer is None or officer.status != "在职":
        raise UnauthorizedError("账号不可用，请重新登录")
    role = await db.get(Role, officer.role_id)
    if role is None:
        raise UnauthorizedError("角色不存在")
    return resp_ok(
        {
            "access_token": create_access_token(officer.id, officer.username, role.code),
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
        msg="令牌已续期",
    )


@router.post("/logout", summary="登出（令牌加入黑名单）")
async def logout(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheBackend = Depends(get_cache),
):
    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:] if auth_header.lower().startswith("bearer ") else ""
    jti = bearer_jti(token)
    if jti:
        ttl = max(60, token_remaining_seconds(token))
        await cache.set(f"{TOKEN_BLACKLIST_PREFIX}{jti}", "1", ttl=ttl)

    await write_audit(
        db,
        action="logout",
        module="认证",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        detail="登出幽冥后台",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(None, msg="已登出")


@router.get("/profile", summary="当前登录鬼差信息")
async def profile(user: CurrentUser = Depends(get_current_user)):
    return resp_ok(_profile(user))


@router.get("/permissions", summary="当前角色权限点（按钮级 v-if 依据）")
async def my_permissions(user: CurrentUser = Depends(get_current_user)):
    return resp_ok(
        {
            "is_super": user.is_super,
            "data_scope": user.data_scope,
            "codes": ["*"] if user.is_super else sorted(user.permissions),
        }
    )


@router.get("/menus", summary="当前角色可见菜单树")
async def my_menus(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = list(
        (
            await db.execute(
                select(Menu).where(Menu.status == "启用").order_by(Menu.sort, Menu.id)
            )
        )
        .scalars()
        .all()
    )
    visible = [
        m
        for m in rows
        if m.type != "按钮"
        and (not m.permission_code or user.is_super or m.permission_code in user.permissions)
    ]
    node_map = {m.id: {**model_to_dict(m), "children": []} for m in visible}
    tree: list[dict] = []
    for m in visible:
        node = node_map[m.id]
        if m.parent_id and m.parent_id in node_map:
            node_map[m.parent_id]["children"].append(node)
        else:
            tree.append(node)

    def _prune(nodes: list[dict]) -> list[dict]:
        """无可见子项的目录一律剪掉，避免前端出现空壳菜单。"""
        kept: list[dict] = []
        for n in nodes:
            n["children"] = _prune(n["children"])
            if n["type"] == "目录" and not n["children"]:
                continue
            kept.append(n)
        return kept

    tree = _prune(tree)
    return resp_ok({"items": tree, "total": len(tree)})


@router.post("/password", summary="修改本账号密码")
async def change_password(
    payload: ChangePasswordIn,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheBackend = Depends(get_cache),
):
    officer = user.officer
    if not verify_password(payload.old_password, officer.password_hash):
        raise AppError("原密码不正确", code=400, http_status=400)
    officer.password_hash = hash_password(payload.new_password)
    await write_audit(
        db,
        action="change_password",
        module="认证",
        officer_id=officer.id,
        officer_name=officer.real_name,
        role_name=user.role.name,
        detail="修改本账号登录密码",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(None, msg="密码已更新，请重新登录")
