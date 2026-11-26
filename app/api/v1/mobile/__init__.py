"""移动端 H5 专属接口包。

子模块各自声明完整路径前缀（/mobile/approvals、/mobile/messages、/mobile/devices），
此处仅做聚合，由 app.api.v1.router 统一挂到 /api/v1 下。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.mobile import approvals, devices, messages

router = APIRouter()
router.include_router(approvals.router)
router.include_router(messages.router)
router.include_router(devices.router)

__all__ = ["router", "approvals", "messages", "devices"]
