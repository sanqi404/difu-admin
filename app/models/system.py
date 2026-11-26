"""RBAC 四要素：角色 / 权限点 / 角色-权限 / 菜单。"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="角色编码")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色名称")
    description: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="角色描述")
    data_scope: Mapped[str] = mapped_column(
        String(32), default="REGION", nullable=False, comment="数据域：ALL/REGION/SELF"
    )
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否内置")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
    status: Mapped[str] = mapped_column(String(32), default="启用", nullable=False, comment="状态")


class Permission(Base, TimestampMixin):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="权限编码")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="权限名称")
    module: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="所属模块")
    type: Mapped[str] = mapped_column(String(32), default="api", nullable=False, comment="类型：api/button")
    method: Mapped[str] = mapped_column(String(16), default="", nullable=False, comment="HTTP 方法")
    path: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="接口路径")
    description: Mapped[str] = mapped_column(Text, default="", nullable=False, comment="说明")


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False, index=True, comment="角色ID"
    )
    permission_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("permission.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="权限ID",
    )


class Menu(Base, TimestampMixin):
    __tablename__ = "menu"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="父菜单ID")
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="菜单编码")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="菜单名称")
    path: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="前端路由")
    component: Mapped[str] = mapped_column(String(255), default="", nullable=False, comment="组件路径")
    icon: Mapped[str] = mapped_column(String(64), default="", nullable=False, comment="图标")
    type: Mapped[str] = mapped_column(String(32), default="菜单", nullable=False, comment="类型：目录/菜单")
    permission_code: Mapped[str] = mapped_column(
        String(64), default="", nullable=False, comment="访问所需权限编码"
    )
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否可见")
    status: Mapped[str] = mapped_column(String(32), default="启用", nullable=False, comment="状态")
