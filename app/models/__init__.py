"""ORM 汇总导出：Alembic autogenerate 与 create_all 均依赖此处导入全部模型。"""

from __future__ import annotations

from app.models.audit_log import AuditLog
from app.models.base import Base, TimestampMixin
from app.models.city_god import CityGod
from app.models.document import Document
from app.models.karma import KarmaRecord
from app.models.life_book import LifeBook
from app.models.mobile import ApprovalRequest, ApprovalStep, MobileDevice, MobileMessage
from app.models.officer import Officer
from app.models.punishment import Punishment
from app.models.reincarnation import Reincarnation
from app.models.soul import Soul
from app.models.summon_order import SummonOrder
from app.models.system import Menu, Permission, Role, RolePermission
from app.models.trial import TrialRecord

__all__ = [
    "Base",
    "TimestampMixin",
    "Soul",
    "LifeBook",
    "SummonOrder",
    "TrialRecord",
    "Punishment",
    "Reincarnation",
    "KarmaRecord",
    "Officer",
    "Role",
    "Menu",
    "Permission",
    "RolePermission",
    "CityGod",
    "Document",
    "AuditLog",
    "ApprovalRequest",
    "ApprovalStep",
    "MobileMessage",
    "MobileDevice",
]
