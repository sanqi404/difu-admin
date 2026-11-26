"""移动端 H5 · 设备绑定：绑定 / 解绑 / 我的设备列表。

一台设备（device_id）只允许绑定一个账号：重复绑定同一账号为幂等更新推送令牌，
已被他人绑定时则抢占式改绑到当前登录鬼差，避免换号登录后推送错乱。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, client_ip, client_ua, get_current_user
from app.core.response import NotFoundError, resp_ok
from app.core.utils import model_to_dict
from app.database import get_db, utcnow
from app.models import MobileDevice
from app.schemas import MobileDeviceBindIn
from app.services.audit import write_audit

router = APIRouter(prefix="/mobile/devices", tags=["移动端-设备"])


@router.get("", summary="我的已绑定设备")
async def list_devices(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = (
        await db.execute(
            select(MobileDevice)
            .where(MobileDevice.user_id == user.officer.id)
            .order_by(MobileDevice.last_active_at.desc(), MobileDevice.id.desc())
        )
    ).scalars().all()
    return resp_ok([model_to_dict(i) for i in items], msg="我的设备")


@router.post("/bind", summary="绑定设备与推送令牌")
async def bind_device(
    payload: MobileDeviceBindIn,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    device = (
        await db.execute(select(MobileDevice).where(MobileDevice.device_id == payload.device_id))
    ).scalar_one_or_none()
    now = utcnow()
    if device is None:
        device = MobileDevice(
            user_id=user.officer.id,
            device_id=payload.device_id,
            push_token=payload.push_token,
            platform=payload.platform,
            last_active_at=now,
        )
        db.add(device)
        action = "bind"
    else:
        device.user_id = user.officer.id
        device.push_token = payload.push_token
        device.platform = payload.platform
        device.last_active_at = now
        action = "rebind"

    await db.flush()
    await write_audit(
        db,
        action=f"mobile_device_{action}",
        module="移动端设备",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="mobile_device",
        resource_id=device.id or 0,
        detail=f"绑定设备 {payload.device_id}（{payload.platform}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    await db.refresh(device)
    return resp_ok(model_to_dict(device), msg="设备绑定成功")


@router.delete("/{device_id}", summary="解绑设备")
async def unbind_device(
    device_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    device = (
        await db.execute(select(MobileDevice).where(MobileDevice.device_id == device_id))
    ).scalar_one_or_none()
    if device is None or device.user_id != user.officer.id:
        raise NotFoundError("未找到该设备绑定记录")
    record_id = device.id
    await db.delete(device)
    await write_audit(
        db,
        action="mobile_device_unbind",
        module="移动端设备",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="mobile_device",
        resource_id=record_id,
        detail=f"解绑设备 {device_id}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"device_id": device_id}, msg="设备已解绑")
