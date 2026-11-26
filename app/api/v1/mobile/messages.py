"""移动端 H5 · 消息中心：列表、未读数、单条已读、全部已读。

数据域隔离：所有查询与写操作都限定在 receiver_id == 当前登录鬼差。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import APPROVAL_BIZ_PERMISSION  # noqa: F401  保持与审批模块常量同源
from app.core.deps import CurrentUser, get_current_user
from app.core.response import AppError, NotFoundError, page_resp, resp_ok
from app.core.utils import model_to_dict, paginate
from app.database import get_db, utcnow
from app.models import MobileMessage

router = APIRouter(prefix="/mobile/messages", tags=["移动端-消息中心"])

MESSAGE_TYPES = ("审批待办", "审批结果", "工单派发", "系统通知", "紧急通告")
MESSAGE_PRIORITIES = ("普通", "重要", "紧急")


@router.get("", summary="消息列表")
async def list_messages(
    is_read: bool | None = Query(None, description="是否已读，留空返回全部"),
    type: str = Query("", description="消息类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if type and type not in MESSAGE_TYPES:
        raise AppError(f"未知的消息类型：{type}")
    stmt = select(MobileMessage).where(MobileMessage.receiver_id == user.officer.id)
    if is_read is not None:
        stmt = stmt.where(MobileMessage.is_read.is_(is_read))
    if type:
        stmt = stmt.where(MobileMessage.type == type)
    stmt = stmt.order_by(MobileMessage.created_at.desc(), MobileMessage.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp([model_to_dict(i) for i in items], total, page, page_size)


@router.get("/unread-count", summary="未读消息数")
async def unread_count(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    total = (
        await db.execute(
            select(func.count())
            .select_from(MobileMessage)
            .where(MobileMessage.receiver_id == user.officer.id, MobileMessage.is_read.is_(False))
        )
    ).scalar_one()
    by_type_rows = (
        await db.execute(
            select(MobileMessage.type, func.count())
            .where(MobileMessage.receiver_id == user.officer.id, MobileMessage.is_read.is_(False))
            .group_by(MobileMessage.type)
        )
    ).all()
    by_priority_rows = (
        await db.execute(
            select(MobileMessage.priority, func.count())
            .where(MobileMessage.receiver_id == user.officer.id, MobileMessage.is_read.is_(False))
            .group_by(MobileMessage.priority)
        )
    ).all()
    return resp_ok(
        {
            "unread": total,
            "by_type": {row[0]: row[1] for row in by_type_rows},
            "by_priority": {row[0]: row[1] for row in by_priority_rows},
        },
        msg="未读消息统计",
    )


@router.post("/{message_id}/read", summary="标记单条已读")
async def read_message(
    message_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    message = await db.get(MobileMessage, message_id)
    if message is None:
        raise NotFoundError("消息不存在")
    if message.receiver_id != user.officer.id:
        raise NotFoundError("消息不存在")
    if not message.is_read:
        message.is_read = True
        await db.commit()
        await db.refresh(message)
    return resp_ok(model_to_dict(message), msg="已标记为已读")


@router.post("/read-all", summary="全部标记已读")
async def read_all_messages(
    type: str = Query("", description="可按消息类型批量已读，留空为全部"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if type and type not in MESSAGE_TYPES:
        raise AppError(f"未知的消息类型：{type}")
    conditions = [MobileMessage.receiver_id == user.officer.id, MobileMessage.is_read.is_(False)]
    if type:
        conditions.append(MobileMessage.type == type)
    result = await db.execute(
        update(MobileMessage)
        .where(*conditions)
        .values(is_read=True)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return resp_ok(
        {"updated": result.rowcount or 0, "type": type or "全部", "at": utcnow().isoformat()},
        msg="已全部标记为已读",
    )
