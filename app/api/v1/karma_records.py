"""业力记录：孽镜台评分、善恶流水。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import KARMA_CATEGORIES, KARMA_SOURCES, KARMA_TYPES
from app.core.deps import (
    CurrentUser,
    client_ip,
    client_ua,
    require_permission,
    scope_conditions,
)
from app.core.response import AppError, NotFoundError, page_resp, resp_ok
from app.core.utils import like_filter, model_to_dict, models_to_list, paginate
from app.database import get_db, utcnow
from app.models import KarmaRecord, Soul
from app.schemas import KarmaCreateIn, KarmaScoreIn
from app.services.audit import write_audit
from app.services.numbering import next_code

router = APIRouter(prefix="/karma-records", tags=["业力记录"])


def _norm_score(karma_type: str, score: int) -> int:
    """把善恶统一成带符号的分值：善为正、恶为负、中性保持。"""
    if karma_type == "善":
        return abs(score)
    if karma_type == "恶":
        return -abs(score)
    return score


def _sin_level(total: int) -> str:
    if total <= -80:
        return "极重"
    if total <= -50:
        return "重"
    if total <= -20:
        return "中"
    if total < 0:
        return "轻"
    return "无"


@router.get("", summary="业力记录列表")
async def list_karma(
    keyword: str = Query(""),
    soul_id: int | None = Query(None),
    karma_type: str = Query(""),
    category: str = Query(""),
    source: str = Query(""),
    region: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("karma:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KarmaRecord)
    for cond in scope_conditions(user, KarmaRecord):
        stmt = stmt.where(cond)
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(KarmaRecord.karma_no, keyword),
                like_filter(KarmaRecord.soul_name, keyword),
            )
        )
    if soul_id:
        stmt = stmt.where(KarmaRecord.soul_id == soul_id)
    if karma_type:
        stmt = stmt.where(KarmaRecord.karma_type == karma_type)
    if category:
        stmt = stmt.where(KarmaRecord.category == category)
    if source:
        stmt = stmt.where(KarmaRecord.source == source)
    if region:
        stmt = stmt.where(KarmaRecord.region == region)

    stmt = stmt.order_by(KarmaRecord.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/summary", summary="业力分布统计")
async def karma_summary(
    user: CurrentUser = Depends(require_permission("karma:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KarmaRecord)
    for cond in scope_conditions(user, KarmaRecord):
        stmt = stmt.where(cond)
    rows = (await db.execute(stmt)).scalars().all()
    by_type: dict[str, int] = {t: 0 for t in KARMA_TYPES}
    by_category: dict[str, int] = {}
    for row in rows:
        by_type[row.karma_type] = by_type.get(row.karma_type, 0) + 1
        by_category[row.category] = by_category.get(row.category, 0) + 1
    return resp_ok(
        {
            "total": len(rows),
            "by_type": [{"type": k, "count": v} for k, v in by_type.items()],
            "by_category": sorted(
                [{"category": k, "count": v} for k, v in by_category.items()],
                key=lambda x: -x["count"],
            ),
        }
    )


@router.get("/soul/{soul_id}", summary="某亡魂的业力明细与合计")
async def soul_karma(
    soul_id: int,
    user: CurrentUser = Depends(require_permission("karma:view")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, soul_id)
    if soul is None:
        raise NotFoundError("亡魂不存在")
    rows = (
        (await db.execute(select(KarmaRecord).where(KarmaRecord.soul_id == soul_id).order_by(KarmaRecord.id.desc())))
        .scalars()
        .all()
    )
    total = sum(_norm_score(r.karma_type, r.score) for r in rows)
    return resp_ok(
        {
            "soul_id": soul.id,
            "soul_name": soul.name,
            "current_score": soul.karma_score,
            "sin_level": soul.sin_level,
            "computed_score": total,
            "items": models_to_list(rows),
        }
    )


@router.get("/{karma_id}", summary="业力记录详情")
async def get_karma(
    karma_id: int,
    user: CurrentUser = Depends(require_permission("karma:view")),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(KarmaRecord, karma_id)
    if record is None:
        raise NotFoundError("业力记录不存在")
    return resp_ok(model_to_dict(record))


@router.post("", summary="业力录入")
async def create_karma(
    payload: KarmaCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("karma:create")),
    db: AsyncSession = Depends(get_db),
):
    if payload.karma_type not in KARMA_TYPES:
        raise AppError(f"非法业力类型，可选：{'、'.join(KARMA_TYPES)}")
    if payload.category and payload.category not in KARMA_CATEGORIES:
        raise AppError(f"非法业力类别，可选：{'、'.join(KARMA_CATEGORIES)}")
    if payload.source and payload.source not in KARMA_SOURCES:
        raise AppError(f"非法业力来源，可选：{'、'.join(KARMA_SOURCES)}")

    soul = await db.get(Soul, payload.soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")

    karma_no = await next_code(db, KarmaRecord, "karma_no", "YL", 6)
    record = KarmaRecord(
        karma_no=karma_no,
        soul_id=soul.id,
        soul_name=soul.name,
        region=soul.region or "中央",
        karma_type=payload.karma_type,
        category=payload.category,
        score=abs(payload.score),
        source=payload.source,
        occurred_at=payload.occurred_at or utcnow(),
        recorder_id=user.officer.id,
        recorder_name=user.officer.real_name,
        description=payload.description,
    )
    db.add(record)
    await db.flush()

    await write_audit(
        db,
        action="create",
        module="业力记录",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="karma_record",
        resource_id=record.id,
        detail=f"{karma_no}：{soul.name} {payload.karma_type}·{payload.category} {payload.score} 分",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(record), msg="业力已记录")


@router.post("/score", summary="孽镜台评分（重算亡魂业力与罪孽等级）")
async def score_karma(
    payload: KarmaScoreIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("karma:score")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, payload.soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")

    rows = (
        (await db.execute(select(KarmaRecord).where(KarmaRecord.soul_id == soul.id))).scalars().all()
    )
    if not rows:
        raise AppError("该亡魂尚无业力记录，孽镜台无法成像")

    total = sum(_norm_score(r.karma_type, r.score) for r in rows)
    old_score, old_level = soul.karma_score, soul.sin_level
    soul.karma_score = total
    soul.sin_level = _sin_level(total)

    # 孽镜台评分流水本身也留痕
    karma_no = await next_code(db, KarmaRecord, "karma_no", "YL", 6)
    db.add(
        KarmaRecord(
            karma_no=karma_no,
            soul_id=soul.id,
            soul_name=soul.name,
            region=soul.region or "中央",
            karma_type="中性",
            category="",
            score=abs(total) if total else 0,
            source="孽镜台",
            occurred_at=utcnow(),
            recorder_id=user.officer.id,
            recorder_name=user.officer.real_name,
            description=f"孽镜台评分：{old_score} → {total}（{old_level} → {soul.sin_level}），孽镜照前尘",
        )
    )

    await write_audit(
        db,
        action="score",
        module="业力记录",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="soul",
        resource_id=soul.id,
        detail=f"孽镜台评分 {soul.name}：{old_score} → {total}，罪孽等级 {old_level} → {soul.sin_level}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(
        {
            "soul_id": soul.id,
            "soul_name": soul.name,
            "before": {"score": old_score, "sin_level": old_level},
            "after": {"score": soul.karma_score, "sin_level": soul.sin_level},
            "record_count": len(rows),
        },
        msg="孽镜台评分完成",
    )
