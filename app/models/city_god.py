"""城隍网点：地府在阳间的分支机构（府 / 州 / 县三级，按鬼域归属）。"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CityGod(Base, TimestampMixin):
    __tablename__ = "city_god"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="网点编码")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="网点名称")
    region: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="所属鬼域")
    level: Mapped[str] = mapped_column(String(32), default="县城隍", nullable=False, comment="网点级别")
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="上级网点ID")
    city_god_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="城隍神姓名")
    address: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="辖境地址")
    contact: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="联络方式")
    soul_capacity: Mapped[int] = mapped_column(Integer, default=1000, nullable=False, comment="亡魂容量")
    soul_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="在册亡魂数")
    status: Mapped[str] = mapped_column(String(32), default="在职", nullable=False, comment="网点状态")
    remark: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="备注")
