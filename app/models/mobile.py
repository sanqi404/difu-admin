"""移动端 H5 专属模型：审批中心 / 消息中心 / 设备绑定。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import utcnow
from app.models.base import Base, TimestampMixin


class ApprovalRequest(Base, TimestampMixin):
    """移动审批单主表：status 承担 current_step 语义，记录当前所处审批环节。"""

    __tablename__ = "approval_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    biz_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="业务类型：生死簿添寿/判令还阳/减刑赦免/异常上报/工单撤销",
    )
    biz_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True, comment="关联业务主键")
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="审批标题")
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="审批摘要")
    payload_json: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="业务载荷(JSON 字符串)")
    applicant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, index=True, comment="申请人鬼差"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="审批中",
        nullable=False,
        index=True,
        comment="当前环节，如 L1-城隍 / L2-酆都大帝；终态 已通过/已驳回/已撤销",
    )
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审批截止时间(UTC)")


class ApprovalStep(Base):
    """审批环节明细：同一 step_no 出现多条即为双人会签。"""

    __tablename__ = "approval_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_request.id"), nullable=False, index=True, comment="审批单"
    )
    step_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True, comment="环节序号")
    approver_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, index=True, comment="审批人"
    )
    action: Mapped[str] = mapped_column(
        String(16),
        default="pending",
        nullable=False,
        index=True,
        comment="pending 未激活 / wait 待审批 / agree / reject / transfer",
    )
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="批注")
    acted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="处理时间(UTC)")


class MobileMessage(Base):
    """移动端消息中心。"""

    __tablename__ = "mobile_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receiver_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, index=True, comment="接收鬼差"
    )
    type: Mapped[str] = mapped_column(
        String(32), default="系统通知", nullable=False, index=True, comment="消息类型：审批待办/审批结果/工单派发/系统通知"
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="消息标题")
    content: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="消息正文")
    biz_ref: Mapped[str] = mapped_column(
        String(64), default="", nullable=False, index=True, comment="业务引用，如 approval:12 / summon:3"
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否已读")
    priority: Mapped[str] = mapped_column(
        String(16), default="普通", nullable=False, comment="优先级：普通/重要/紧急"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, comment="创建时间(UTC)"
    )


class MobileDevice(Base):
    """移动端设备与推送令牌绑定。"""

    __tablename__ = "mobile_device"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("officer.id"), nullable=True, index=True, comment="绑定鬼差"
    )
    device_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True, comment="设备唯一标识"
    )
    push_token: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="推送令牌")
    platform: Mapped[str] = mapped_column(
        String(16), default="h5", nullable=False, comment="平台：ios/android/h5"
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, comment="最近活跃时间(UTC)"
    )


__all__ = ["ApprovalRequest", "ApprovalStep", "MobileMessage", "MobileDevice"]
