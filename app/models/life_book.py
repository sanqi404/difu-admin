"""生死簿：阳寿登记流水（录入 / 修改 / 复核 / 驳回 / 注销），含留痕快照。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LifeBook(Base, TimestampMixin):
    __tablename__ = "life_book"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="流水号")
    soul_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("soul.id"), nullable=True, index=True, comment="关联亡魂"
    )
    soul_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="亡魂姓名")
    action: Mapped[str] = mapped_column(String(32), nullable=False, comment="操作类型：录入/修改/复核/驳回/注销")
    lifespan_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="核定阳寿（年）")
    before_content: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="变更前内容")
    after_content: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="变更后内容")
    diff_desc: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="变更摘要")
    review_status: Mapped[str] = mapped_column(
        String(32), default="待复核", nullable=False, index=True, comment="待复核/已复核/已驳回"
    )
    operator_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, comment="录入人"
    )
    operator_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="录入人姓名")
    reviewer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, comment="复核人"
    )
    reviewer_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="复核人姓名")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="复核时间(UTC)")
    review_comment: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="复核意见")
    is_tampered: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="疑似篡改标记")
