"""业力记录：孽镜台映像与善恶业力明细。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KarmaRecord(Base, TimestampMixin):
    __tablename__ = "karma_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    karma_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="业力编号")
    soul_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("soul.id"), nullable=True, index=True, comment="关联亡魂"
    )
    soul_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="亡魂姓名")
    region: Mapped[str] = mapped_column(String(32), default="中央", nullable=False, index=True, comment="鬼域")
    karma_type: Mapped[str] = mapped_column(String(32), default="恶", nullable=False, comment="善/恶/中性")
    category: Mapped[str] = mapped_column(String(32), default="", nullable=False, index=True, comment="业力类别")
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="业力分值（正善负恶）")
    source: Mapped[str] = mapped_column(
        String(32), default="孽镜台", nullable=False, comment="孽镜台/城隍上报/生死簿核定/人工录入"
    )
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="业力发生时间(UTC)")
    recorder_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, comment="记录人"
    )
    recorder_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="记录人姓名")
    description: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="业力描述")
