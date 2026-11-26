"""统计看板：总览、状态分布、30 天趋势。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import REGIONS, SoulStatus
from app.core.deps import CurrentUser, require_permission, scope_conditions
from app.core.response import resp_ok
from app.database import get_db, utcnow
from app.models import (
    AuditLog,
    CityGod,
    Document,
    KarmaRecord,
    LifeBook,
    Officer,
    Punishment,
    Reincarnation,
    Soul,
    SummonOrder,
    TrialRecord,
)

router = APIRouter(prefix="/stats", tags=["统计看板"])

ALL_STATUS = [
    SoulStatus.REGISTERED,
    SoulStatus.SUMMONED,
    SoulStatus.FILED,
    SoulStatus.CROSSED,
    SoulStatus.PENDING_TRIAL,
    SoulStatus.IN_TRIAL,
    SoulStatus.CONVICTED,
    SoulStatus.SERVING,
    SoulStatus.SERVED,
    SoulStatus.WAIT_REBIRTH,
    SoulStatus.REBIRTHED,
    SoulStatus.WRONGFUL_CITY,
    SoulStatus.RETURNED_LIFE,
    SoulStatus.FROZEN,
    SoulStatus.CANCELLED,
]


@router.get("/overview", summary="总览指标")
async def overview(
    user: CurrentUser = Depends(require_permission("stats:view")),
    db: AsyncSession = Depends(get_db),
):
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    soul_base = select(Soul).where(Soul.is_deleted.is_(False))
    for cond in scope_conditions(user, Soul):
        soul_base = soul_base.where(cond)
    soul_rows = (await db.execute(soul_base)).scalars().all()

    status_counts: dict[str, int] = {s: 0 for s in ALL_STATUS}
    region_counts: dict[str, int] = {r: 0 for r in REGIONS}
    for soul in soul_rows:
        status_counts[soul.status] = status_counts.get(soul.status, 0) + 1
        region_counts[soul.region] = region_counts.get(soul.region, 0) + 1

    async def _count(model, *wheres) -> int:
        stmt = select(func.count(model.id))
        for w in wheres:
            stmt = stmt.where(w)
        return (await db.execute(stmt)).scalar_one()

    summon_by_status = dict(
        (await db.execute(select(SummonOrder.status, func.count(SummonOrder.id)).group_by(SummonOrder.status))).all()
    )
    punish_by_status = dict(
        (await db.execute(select(Punishment.status, func.count(Punishment.id)).group_by(Punishment.status))).all()
    )
    reinc_by_status = dict(
        (await db.execute(select(Reincarnation.status, func.count(Reincarnation.id)).group_by(Reincarnation.status))).all()
    )

    return resp_ok(
        {
            "soul": {
                "total": len(soul_rows),
                "today_new": sum(1 for s in soul_rows if s.created_at and s.created_at >= today_start),
                "frozen": status_counts.get(SoulStatus.FROZEN, 0),
                "by_status": [{"status": k, "count": v} for k, v in status_counts.items()],
                "by_region": [{"region": k, "count": v} for k, v in region_counts.items()],
            },
            "summon": {
                "total": sum(summon_by_status.values()),
                "by_status": [{"status": k, "count": v} for k, v in summon_by_status.items()],
            },
            "trial": {
                "total": await _count(TrialRecord),
                "pending": await _count(TrialRecord, TrialRecord.status == "待审"),
                "in_progress": await _count(TrialRecord, TrialRecord.status == "审理中"),
                "closed": await _count(TrialRecord, TrialRecord.status == "已结案"),
            },
            "punishment": {
                "total": sum(punish_by_status.values()),
                "by_status": [{"status": k, "count": v} for k, v in punish_by_status.items()],
            },
            "reincarnation": {
                "total": sum(reinc_by_status.values()),
                "by_status": [{"status": k, "count": v} for k, v in reinc_by_status.items()],
            },
            "life_book": {
                "total": await _count(LifeBook),
                "pending_review": await _count(LifeBook, LifeBook.review_status == "待复核"),
                "rejected": await _count(LifeBook, LifeBook.review_status == "已驳回"),
                "tampered": await _count(LifeBook, LifeBook.is_tampered.is_(True)),
            },
            "karma": {
                "total": await _count(KarmaRecord),
                "good": await _count(KarmaRecord, KarmaRecord.karma_type == "善"),
                "evil": await _count(KarmaRecord, KarmaRecord.karma_type == "恶"),
            },
            "base": {
                "officer": await _count(Officer),
                "online_officer": await _count(Officer, Officer.status == "在职"),
                "city_god": await _count(CityGod),
                "document": await _count(Document),
                "audit": await _count(AuditLog),
                "tamper_audit": await _count(AuditLog, AuditLog.level == "篡改告警"),
            },
        }
    )


@router.get("/trend", summary="近 N 天业务趋势")
async def trend(
    days: int = Query(30, ge=1, le=90),
    user: CurrentUser = Depends(require_permission("stats:view")),
    db: AsyncSession = Depends(get_db),
):
    now = utcnow()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    async def _daily(model) -> dict[str, int]:
        rows = (
            await db.execute(
                select(func.date(model.created_at), func.count(model.id))
                .where(model.created_at >= start)
                .group_by(func.date(model.created_at))
            )
        ).all()
        result: dict[str, int] = {}
        for day, count in rows:
            key = day.strftime("%Y-%m-%d") if hasattr(day, "strftime") else str(day)[:10]
            result[key] = count
        return result

    soul_map = await _daily(Soul)
    summon_map = await _daily(SummonOrder)
    trial_map = await _daily(TrialRecord)
    reinc_map = await _daily(Reincarnation)
    audit_map = await _daily(AuditLog)

    series = []
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        series.append(
            {
                "date": day,
                "new_soul": soul_map.get(day, 0),
                "summon_order": summon_map.get(day, 0),
                "trial": trial_map.get(day, 0),
                "reincarnation": reinc_map.get(day, 0),
                "audit": audit_map.get(day, 0),
            }
        )

    return resp_ok(
        {
            "days": days,
            "series": series,
            "total": {
                "new_soul": sum(v for v in soul_map.values()),
                "summon_order": sum(v for v in summon_map.values()),
                "trial": sum(v for v in trial_map.values()),
                "reincarnation": sum(v for v in reinc_map.values()),
                "audit": sum(v for v in audit_map.values()),
            },
        }
    )
