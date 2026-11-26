"""拘魂工单：勾魂任务派发与执行台账。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SummonOrder(Base, TimestampMixin):
    __tablename__ = "summon_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="工单号")
    soul_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("soul.id"), nullable=True, index=True, comment="目标亡魂"
    )
    soul_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="亡魂姓名")
    region: Mapped[str] = mapped_column(String(32), default="中央", nullable=False, index=True, comment="鬼域")
    city_god_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("city_god.id"), nullable=True, comment="归属城隍网点"
    )
    assignee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, index=True, comment="执行鬼差"
    )
    assignee_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="执行鬼差姓名")
    priority: Mapped[str] = mapped_column(String(32), default="普通", nullable=False, comment="普通/加急/特急")
    status: Mapped[str] = mapped_column(
        String(32), default="待派发", nullable=False, index=True, comment="待派发/执行中/已完成/已超时/异常"
    )
    death_type: Mapped[str] = mapped_column(String(32), default="寿终正寝", nullable=False, comment="死因")
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="拘魂地点")
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="限办期限(UTC)")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始执行(UTC)")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间(UTC)")
    result: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="执行结果")
    abnormal_reason: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="异常说明")
