"""轮回档案：孟婆汤确认 + 六道投胎办理。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Reincarnation(Base, TimestampMixin):
    __tablename__ = "reincarnation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reinc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="轮回编号")
    soul_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("soul.id"), nullable=True, index=True, comment="投胎亡魂"
    )
    soul_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="亡魂姓名")
    region: Mapped[str] = mapped_column(String(32), default="中央", nullable=False, index=True, comment="鬼域")
    path: Mapped[str] = mapped_column(
        String(32), default="人道", nullable=False, index=True, comment="六道：天道/人道/阿修罗道/畜生道/饿鬼道/地狱道"
    )
    target_world: Mapped[str] = mapped_column(String(128), default="", nullable=False, comment="投胎去向")
    karma_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="业力评分快照")
    soup_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="孟婆汤是否已饮（确认）"
    )
    soup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="饮汤时间(UTC)")
    soup_operator: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="孟婆经办人")
    status: Mapped[str] = mapped_column(
        String(32), default="待办理", nullable=False, index=True, comment="待办理/待投胎/已投胎/已归档/已撤销"
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="预约投胎时间(UTC)")
    reincarnated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="实际投胎时间(UTC)")
    operator_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, comment="经办鬼差"
    )
    remark: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="备注")
