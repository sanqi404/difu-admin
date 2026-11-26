"""亡魂状态机：强校验、禁止跳步、旁路状态受控。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    SOUL_ACTIONS,
    SOUL_FINAL_STATUS,
    SoulStatus,
    resolve_transition,
)
from app.core.response import AppError, ConflictError
from app.database import utcnow
from app.models import Reincarnation, Soul, TrialRecord
from app.models.punishment import Punishment

LOCATION_BY_STATUS: dict[str, str] = {
    SoulStatus.REGISTERED.value: "阴司在册",
    SoulStatus.SUMMONED.value: "拘魂途中",
    SoulStatus.FILED.value: "城隍备案司",
    SoulStatus.CROSSED.value: "鬼门关",
    SoulStatus.PENDING_TRIAL.value: "迷魂殿",
    SoulStatus.IN_TRIAL.value: "十殿法庭",
    SoulStatus.CONVICTED.value: "待刑司",
    SoulStatus.SERVING.value: "地狱刑狱",
    SoulStatus.SERVED.value: "刑满释放司",
    SoulStatus.WAIT_REBIRTH.value: "轮回台",
    SoulStatus.REBIRTHED.value: "六道轮回",
    SoulStatus.WRONGFUL_CITY.value: "枉死城",
    SoulStatus.RETURNED_LIFE.value: "还阳道",
    SoulStatus.FROZEN.value: "冻结牢",
    SoulStatus.CANCELLED.value: "归档阁",
}


async def _check_preconditions(
    db: AsyncSession, soul: Soul, action: str
) -> None:
    if action == "convict":
        stmt = (
            select(TrialRecord)
            .where(TrialRecord.soul_id == soul.id, TrialRecord.status == "已结案")
            .order_by(TrialRecord.id.desc())
            .limit(1)
        )
        trial = (await db.execute(stmt)).scalar_one_or_none()
        if trial is None:
            raise AppError("尚未产生已结案的审判记录，不得进入「已定罪」")
        if trial.verdict not in ("有罪",):
            raise AppError(f"最近一次判决为「{trial.verdict or '未定'}」，无法定罪")

    if action == "sentence":
        stmt = select(Punishment).where(
            Punishment.soul_id == soul.id, Punishment.status.in_(["待执行", "服刑中"])
        )
        if (await db.execute(stmt)).scalar_one_or_none() is None:
            raise AppError("未登记刑期台账，无法交付执行")

    if action == "reincarnate":
        stmt = select(Reincarnation).where(
            Reincarnation.soul_id == soul.id, Reincarnation.status.in_(["待办理", "待投胎"])
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        if record is None:
            raise AppError("未建立轮回档案，无法办理投胎")
        if not record.soup_confirmed:
            raise AppError("孟婆汤尚未确认饮用，禁止投胎")


async def _apply_side_effects(
    db: AsyncSession, soul: Soul, action: str, to_status: str
) -> None:
    now = utcnow()
    if action in ("sentence", "serve_out"):
        stmt = (
            select(Punishment)
            .where(Punishment.soul_id == soul.id)
            .order_by(Punishment.id.desc())
            .limit(1)
        )
        punish = (await db.execute(stmt)).scalar_one_or_none()
        if punish is not None:
            if action == "sentence":
                punish.status = "服刑中"
                punish.start_at = punish.start_at or now
                if punish.progress <= 0:
                    punish.progress = 5
            else:
                punish.status = "已刑满"
                punish.progress = 100
                punish.end_at = now

    if action == "reincarnate":
        stmt = (
            select(Reincarnation)
            .where(Reincarnation.soul_id == soul.id)
            .order_by(Reincarnation.id.desc())
            .limit(1)
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        if record is not None:
            record.status = "已投胎"
            record.reincarnated_at = now


async def change_soul_status(
    db: AsyncSession,
    soul: Soul,
    action: str,
    *,
    reason: str = "",
    strict: bool = True,
    now: Any = None,
) -> dict[str, Any]:
    """执行一次状态流转；非法流转抛 409，业务前置不满足抛 400。"""
    now = now or utcnow()
    current = soul.status

    if current in SOUL_FINAL_STATUS:
        raise ConflictError(f"亡魂已处于终态「{current}」，不可再流转")

    transition = resolve_transition(current, action)
    if transition is None:
        allowed = list(SOUL_ACTIONS.values())
        allowed_names = "、".join(sorted({a.action_name for a in allowed}))
        raise ConflictError(
            f"当前状态「{current}」不允许执行动作「{action}」（可用动作：{allowed_names}）"
        )

    # 异常解冻：只能回到冻结前的状态
    if action == "unfreeze":
        target = soul.prev_status
        if not target:
            raise AppError("缺少冻结前状态，无法解冻")
        to_status = target
    elif action == "freeze":
        to_status = SoulStatus.FROZEN.value
    else:
        to_status = transition.dst

    if to_status == current:
        raise ConflictError(f"亡魂已处于「{current}」状态")

    if strict and action not in ("freeze", "unfreeze"):
        await _check_preconditions(db, soul, action)

    prev = current
    if action == "freeze":
        soul.prev_status = current
    elif action == "unfreeze":
        soul.prev_status = ""

    soul.status = to_status
    soul.current_location = LOCATION_BY_STATUS.get(to_status, soul.current_location)

    if strict:
        await _apply_side_effects(db, soul, action, to_status)

    return {
        "soul_id": soul.id,
        "soul_no": soul.soul_no,
        "action": action,
        "action_name": transition.action_name,
        "from_status": prev,
        "to_status": to_status,
        "reason": reason,
    }
