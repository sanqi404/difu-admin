"""刑期台账：十八层地狱服刑记录。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Punishment(Base, TimestampMixin):
    __tablename__ = "punishment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    punish_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="刑期编号")
    soul_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("soul.id"), nullable=True, index=True, comment="服刑亡魂"
    )
    soul_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="亡魂姓名")
    trial_record_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("trial_record.id"), nullable=True, comment="来源判决"
    )
    region: Mapped[str] = mapped_column(String(32), default="中央", nullable=False, index=True, comment="鬼域")
    hell_level: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True, comment="地狱层级 1~18"
    )
    hell_name: Mapped[str] = mapped_column(String(32), default="", nullable=False, comment="地狱名称")
    sentence_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="刑期（年）")
    reduced_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="已减免（年）")
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="起刑时间(UTC)")
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="刑满时间(UTC)")
    status: Mapped[str] = mapped_column(
        String(32), default="待执行", nullable=False, index=True, comment="待执行/服刑中/已刑满/已转出/已减免"
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="服刑进度 0~100")
    executor_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="执刑鬼差")
    remark: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="备注")
