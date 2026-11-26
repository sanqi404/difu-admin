"""Pydantic 请求/响应模型（按业务域分组）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ============================================================
# 认证
# ============================================================
class LoginIn(StrictModel):
    username: str = Field(min_length=2, max_length=64, description="登录账号")
    password: str = Field(min_length=4, max_length=64, description="登录密码")
    captcha_id: str = Field(min_length=8, max_length=64, description="验证码ID")
    captcha_code: str = Field(min_length=2, max_length=8, description="验证码")


class RefreshIn(StrictModel):
    refresh_token: str = Field(min_length=10)


class ChangePasswordIn(StrictModel):
    old_password: str = Field(min_length=4, max_length=64)
    new_password: str = Field(min_length=6, max_length=64)


# ============================================================
# 亡魂
# ============================================================
class SoulCreateIn(StrictModel):
    name: str = Field(min_length=1, max_length=64)
    gender: str = "男"
    age: int = Field(default=0, ge=0, le=999)
    birth_date: datetime | None = None
    death_date: datetime | None = None
    native_place: str = ""
    region: str = "中央"
    death_type: str = "寿终正寝"
    city_god_id: int | None = None
    karma_score: int = 0
    sin_level: str = "无"
    life_book_no: str = ""
    current_location: str = "阴司在册"
    remark: str = ""


class SoulUpdateIn(StrictModel):
    name: str | None = None
    gender: str | None = None
    age: int | None = Field(default=None, ge=0, le=999)
    birth_date: datetime | None = None
    death_date: datetime | None = None
    native_place: str | None = None
    region: str | None = None
    death_type: str | None = None
    city_god_id: int | None = None
    karma_score: int | None = None
    sin_level: str | None = None
    remark: str | None = None


class SoulTransitionIn(StrictModel):
    action: str = Field(min_length=2, max_length=32, description="流转动作，如 summon / file / convict")
    reason: str = Field(default="", max_length=500, description="流转说明")


# ============================================================
# 生死簿
# ============================================================
class LifeBookCreateIn(StrictModel):
    soul_id: int | None = None
    soul_name: str = Field(min_length=1, max_length=64)
    action: str = "录入"
    lifespan_years: int = Field(default=60, ge=0, le=999)
    before_content: str = ""
    after_content: str = ""
    diff_desc: str = ""


class LifeBookUpdateIn(StrictModel):
    lifespan_years: int | None = Field(default=None, ge=0, le=999)
    after_content: str | None = None
    diff_desc: str | None = None


class ReviewIn(StrictModel):
    comment: str = Field(default="", max_length=500)


# ============================================================
# 拘魂工单
# ============================================================
class SummonCreateIn(StrictModel):
    soul_id: int
    priority: str = "普通"
    deadline_at: datetime | None = None
    location: str = ""
    death_type: str = "寿终正寝"
    city_god_id: int | None = None


class DispatchIn(StrictModel):
    assignee_id: int


class SummonFinishIn(StrictModel):
    result: str = Field(default="勾魂完成", max_length=500)


class SummonExceptionIn(StrictModel):
    reason: str = Field(min_length=1, max_length=500)


# ============================================================
# 审判
# ============================================================
class TrialCreateIn(StrictModel):
    soul_id: int
    court_level: int = Field(default=1, ge=1, le=10)
    guilt_desc: str = ""


class VerdictIn(StrictModel):
    verdict: str = Field(min_length=2, max_length=32, description="有罪/无罪/打回重审/还阳/发配枉死城")
    verdict_detail: str = ""
    sentence_years: int = Field(default=0, ge=0, le=9999)
    hell_level: int = Field(default=0, ge=0, le=18)
    next_court_level: int = Field(default=0, ge=0, le=10)


# ============================================================
# 刑期
# ============================================================
class PunishmentAdjustIn(StrictModel):
    reduced_years: int = Field(default=1, ge=1, le=999)
    reason: str = ""


# ============================================================
# 轮回
# ============================================================
class ReincarnationCreateIn(StrictModel):
    soul_id: int
    path: str = "人道"
    target_world: str = ""
    scheduled_at: datetime | None = None
    remark: str = ""


# ============================================================
# 业力
# ============================================================
class KarmaCreateIn(StrictModel):
    soul_id: int
    karma_type: str = "恶"
    category: str = ""
    score: int = Field(default=0, ge=-1000, le=1000)
    source: str = "孽镜台"
    description: str = ""
    occurred_at: datetime | None = None


class KarmaScoreIn(StrictModel):
    soul_id: int


# ============================================================
# 鬼差 / 角色 / 菜单
# ============================================================
class OfficerCreateIn(StrictModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=64)
    real_name: str = Field(min_length=1, max_length=64)
    title: str = ""
    role_id: int
    region: str = "中央"
    city_god_id: int | None = None
    data_scope: str = "REGION"
    phone: str = ""
    email: str = ""
    status: str = "在职"
    remark: str = ""


class OfficerUpdateIn(StrictModel):
    real_name: str | None = None
    title: str | None = None
    role_id: int | None = None
    region: str | None = None
    city_god_id: int | None = None
    data_scope: str | None = None
    phone: str | None = None
    email: str | None = None
    remark: str | None = None


class ResetPasswordIn(StrictModel):
    new_password: str = Field(min_length=6, max_length=64)


class StatusIn(StrictModel):
    status: str = Field(min_length=2, max_length=32)


class RoleCreateIn(StrictModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    data_scope: str = "REGION"
    sort: int = 0


class RoleUpdateIn(StrictModel):
    name: str | None = None
    description: str | None = None
    data_scope: str | None = None
    sort: int | None = None
    status: str | None = None


class AssignPermissionIn(StrictModel):
    permission_ids: list[int] = Field(default_factory=list)


class MenuCreateIn(StrictModel):
    parent_id: int | None = None
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    path: str = ""
    component: str = ""
    icon: str = ""
    type: str = "菜单"
    permission_code: str = ""
    sort: int = 0
    visible: bool = True


class MenuUpdateIn(StrictModel):
    parent_id: int | None = None
    name: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    type: str | None = None
    permission_code: str | None = None
    sort: int | None = None
    visible: bool | None = None


# ============================================================
# 城隍网点 / 文书
# ============================================================
class CityGodCreateIn(StrictModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    region: str = "中央"
    level: str = "县城隍"
    parent_id: int | None = None
    city_god_name: str = Field(min_length=1, max_length=64)
    address: str = ""
    contact: str = ""
    soul_capacity: int = Field(default=1000, ge=1)
    status: str = "在职"
    remark: str = ""


class CityGodUpdateIn(StrictModel):
    name: str | None = None
    region: str | None = None
    level: str | None = None
    city_god_name: str | None = None
    address: str | None = None
    contact: str | None = None
    soul_capacity: int | None = None
    status: str | None = None
    remark: str | None = None


class DocumentCreateIn(StrictModel):
    doc_type: str = "路引"
    title: str = ""
    soul_id: int | None = None
    summon_order_id: int | None = None
    city_god_id: int | None = None
    content: str = ""


# ============================================================
# 移动端 H5（审批 / 设备）
# ============================================================
class ApprovalActionIn(StrictModel):
    action: str = Field(
        pattern="^(agree|reject|transfer)$",
        description="审批动作：agree 同意 / reject 驳回 / transfer 转交",
    )
    comment: str = Field(default="", max_length=500, description="审批批注")
    transfer_to: int | None = Field(default=None, description="转交目标审批人（鬼差 ID）")


class MobileDeviceBindIn(StrictModel):
    device_id: str = Field(min_length=4, max_length=128, description="设备唯一标识")
    push_token: str = Field(default="", max_length=255, description="推送令牌")
    platform: str = Field(default="h5", pattern="^(ios|android|h5)$", description="平台")


# ============================================================
# 通用
# ============================================================
class DetailQuery(StrictModel):
    id: int


def dump(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(exclude_unset=True)
    return data
