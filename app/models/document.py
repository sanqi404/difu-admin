"""文书：路引 / 拘票 / 判决书 / 轮回文书 / 还阳令 / 冻结令。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="文书编号")
    doc_type: Mapped[str] = mapped_column(
        String(32), default="路引", nullable=False, index=True, comment="路引/拘票/判决书/轮回文书/还阳令/冻结令"
    )
    title: Mapped[str] = mapped_column(String(128), default="", nullable=False, comment="文书标题")
    soul_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("soul.id"), nullable=True, index=True, comment="关联亡魂"
    )
    soul_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="亡魂姓名")
    summon_order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("summon_order.id"), nullable=True, comment="关联拘魂工单"
    )
    city_god_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("city_god.id"), nullable=True, comment="签发网点"
    )
    content: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="文书正文")
    status: Mapped[str] = mapped_column(
        String(32), default="草稿", nullable=False, index=True, comment="草稿/已签发/已核验/已作废"
    )
    issued_by: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="签发人")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="签发时间(UTC)")
    verified_by: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="核验人")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="核验时间(UTC)")
