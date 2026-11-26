"""阴律日志：全量操作留痕，含篡改告警级别。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.database import utcnow


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    officer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, index=True, comment="操作鬼差"
    )
    officer_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="操作鬼差姓名")
    role_name: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="操作角色")
    action: Mapped[str] = mapped_column(String(64), nullable=False, comment="动作：login/create/update/delete/transition...")
    module: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True, comment="业务模块")
    resource: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="资源类型")
    resource_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="资源ID")
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="操作详情")
    level: Mapped[str] = mapped_column(
        String(32), default="正常", nullable=False, index=True, comment="正常/告警/篡改告警"
    )
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="来源IP")
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="客户端标识")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True, comment="操作时间(UTC)"
    )
