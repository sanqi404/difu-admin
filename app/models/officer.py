"""鬼差账号（地府在编人员）：登录凭据 + 角色 + 数据域 + 所属网点。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Officer(Base, TimestampMixin):
    __tablename__ = "officer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="登录账号")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码散列")
    real_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    title: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="仙职/岗位")
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id"), nullable=False, index=True, comment="所属角色"
    )
    region: Mapped[str] = mapped_column(String(32), default="中央", nullable=False, index=True, comment="所属鬼域")
    city_god_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("city_god.id"), nullable=True, comment="所属城隍网点"
    )
    data_scope: Mapped[str] = mapped_column(
        String(32), default="REGION", nullable=False, comment="数据域：ALL/REGION/SELF"
    )
    phone: Mapped[str] = mapped_column(String(32), default="", nullable=False, comment="联络方式")
    email: Mapped[str] = mapped_column(String(128), default="", nullable=False, comment="阴司信邮")
    status: Mapped[str] = mapped_column(String(32), default="在职", nullable=False, comment="在职/停用/冻结")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后登录(UTC)")
    last_login_ip: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="最后登录IP")
    remark: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="备注")
