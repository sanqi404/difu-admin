"""ORM 基类与公共时间字段。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.database import utcnow

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """创建/更新时间统一由应用层写入 UTC。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, comment="创建时间(UTC)"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False, comment="更新时间(UTC)"
    )


__all__ = ["Base", "TimestampMixin", "utcnow"]
