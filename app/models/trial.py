"""审判记录：十殿阎罗 1~10 殿多级审批链路。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TrialRecord(Base, TimestampMixin):
    __tablename__ = "trial_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trial_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="审判编号")
    soul_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("soul.id"), nullable=True, index=True, comment="受审亡魂"
    )
    soul_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="亡魂姓名")
    court_level: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True, comment="殿级 1~10"
    )
    region: Mapped[str] = mapped_column(String(32), default="中央", nullable=False, index=True, comment="鬼域")
    judge_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, comment="主审阎罗"
    )
    judge_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="主审阎罗姓名")
    karma_snapshot: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="孽镜台评分快照")
    guilt_desc: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="罪状详述")
    status: Mapped[str] = mapped_column(
        String(32), default="待审", nullable=False, index=True, comment="待审/审理中/已结案/打回重审"
    )
    verdict: Mapped[str] = mapped_column(String(32), default="", nullable=False, comment="判决")
    verdict_detail: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="判决详情")
    sentence_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="判处刑期（年）")
    hell_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="发配地狱层级 1~18")
    next_court_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="移送下一殿")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开庭时间(UTC)")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结案时间(UTC)")
