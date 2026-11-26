"""通用序列化与分页工具。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sa_inspect


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        # 统一输出带 Z 的 UTC ISO 串，前端按本地时区展示
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def model_to_dict(obj: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    result: dict[str, Any] = {}
    for attr in sa_inspect(obj).mapper.column_attrs:
        key = attr.key
        if key in exclude:
            continue
        result[key] = _jsonable(getattr(obj, key))
    return result


def models_to_list(objs: list[Any], exclude: set[str] | None = None) -> list[dict[str, Any]]:
    return [model_to_dict(o, exclude) for o in objs]


async def paginate(
    db: AsyncSession, stmt: Select, page: int = 1, page_size: int = 20
) -> tuple[list[Any], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int((await db.execute(count_stmt)).scalar() or 0)
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return list(result.scalars().all()), total


def like_filter(column: Any, keyword: str) -> Any:
    return column.like(f"%{keyword}%")
