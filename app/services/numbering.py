"""业务编号生成：前缀 + 日期 + 序号。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import utcnow


async def next_code(
    db: AsyncSession,
    model: Any,
    field_name: str,
    prefix: str,
    width: int = 4,
) -> str:
    column = getattr(model, field_name)
    today = utcnow().strftime("%Y%m%d")
    head = f"{prefix}{today}"
    total = int(
        (await db.execute(select(func.count()).select_from(model))).scalar() or 0
    )
    for offset in range(1, 1000):
        candidate = f"{head}{(total + offset):0{width}d}"
        exists = (
            await db.execute(select(model.id).where(column == candidate).limit(1))
        ).first()
        if exists is None:
            return candidate
    raise RuntimeError("编号生成失败，请重试")
