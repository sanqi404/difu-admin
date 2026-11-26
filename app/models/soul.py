"""亡魂主档：全生命周期核心实体。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import SoulStatus
from app.models.base import Base, TimestampMixin


class Soul(Base, TimestampMixin):
    __tablename__ = "soul"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    soul_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="亡魂编号")
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="姓名")
    gender: Mapped[str] = mapped_column(String(8), default="男", nullable=False, comment="性别")
    age: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="卒年")
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="生辰")
    death_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="死亡时间"
    )
    native_place: Mapped[str] = mapped_column(String(128), default="", nullable=False, comment="籍贯")
    region: Mapped[str] = mapped_column(
        String(32), default="中央", nullable=False, index=True, comment="所属鬼域（数据域隔离依据）"
    )
    status: Mapped[str] = mapped_column(
        String(32), default=SoulStatus.REGISTERED.value, nullable=False, index=True, comment="亡魂状态"
    )
    prev_status: Mapped[str] = mapped_column(
        String(32), default="", nullable=False, comment="冻结前状态（解冻回退用）"
    )
    karma_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="孽镜台业力评分")
    sin_level: Mapped[str] = mapped_column(String(32), default="无", nullable=False, comment="罪业等级")
    death_type: Mapped[str] = mapped_column(String(32), default="寿终正寝", nullable=False, comment="死因类别")
    life_book_no: Mapped[str] = mapped_column(String(32), default="", nullable=False, comment="生死簿编号")
    city_god_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("city_god.id"), nullable=True, index=True, comment="归属城隍网点"
    )
    # 与 summon_order 互为引用，为避免双向外键导致建表排序死锁，此处仅存 ID 不建 FK 约束
    summon_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="当前拘魂工单ID")
    current_location: Mapped[str] = mapped_column(
        String(64), default="阴司在册", nullable=False, comment="当前所在（殿/狱/关）"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="软删除标记"
    )
    remark: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="备注")
