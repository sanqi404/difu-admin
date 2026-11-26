"""十殿审判：立案送审、开堂、1~10 殿多级审判、判决与打回重审。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import HELL_NAMES, VERDICTS, SoulStatus
from app.core.deps import (
    CurrentUser,
    client_ip,
    client_ua,
    ensure_data_scope,
    require_permission,
    scope_conditions,
)
from app.core.response import AppError, ConflictError, NotFoundError, page_resp, resp_ok
from app.core.utils import like_filter, model_to_dict, models_to_list, paginate
from app.database import get_db, utcnow
from app.models import Soul, TrialRecord
from app.models.punishment import Punishment
from app.schemas import TrialCreateIn, VerdictIn
from app.services.audit import write_audit
from app.services.numbering import next_code
from app.services.state_machine import change_soul_status

router = APIRouter(prefix="/trials", tags=["十殿审判"])

COURT_NAMES = [
    "一殿秦广王", "二殿楚江王", "三殿宋帝王", "四殿仵官王", "五殿阎罗王",
    "六殿卞城王", "七殿泰山王", "八殿都市王", "九殿平等王", "十殿转轮王",
]


@router.get("", summary="审判记录列表")
async def list_trials(
    keyword: str = Query(""),
    court_level: int | None = Query(None, ge=1, le=10),
    status: str = Query(""),
    verdict: str = Query(""),
    region: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("trial:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TrialRecord)
    for cond in scope_conditions(user, TrialRecord):
        stmt = stmt.where(cond)
    if keyword:
        stmt = stmt.where(
            or_(
                like_filter(TrialRecord.trial_no, keyword),
                like_filter(TrialRecord.soul_name, keyword),
            )
        )
    if court_level:
        stmt = stmt.where(TrialRecord.court_level == court_level)
    if status:
        stmt = stmt.where(TrialRecord.status == status)
    if verdict:
        stmt = stmt.where(TrialRecord.verdict == verdict)
    if region:
        stmt = stmt.where(TrialRecord.region == region)

    stmt = stmt.order_by(TrialRecord.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/summary", summary="十殿审判分布统计")
async def trial_summary(
    user: CurrentUser = Depends(require_permission("trial:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TrialRecord)
    for cond in scope_conditions(user, TrialRecord):
        stmt = stmt.where(cond)
    rows = (await db.execute(stmt)).scalars().all()
    by_court = {level: 0 for level in range(1, 11)}
    by_status: dict[str, int] = {}
    for row in rows:
        by_court[row.court_level] = by_court.get(row.court_level, 0) + 1
        by_status[row.status] = by_status.get(row.status, 0) + 1
    return resp_ok(
        {
            "total": len(rows),
            "by_court": [
                {"level": lv, "court": COURT_NAMES[lv - 1], "count": cnt}
                for lv, cnt in sorted(by_court.items())
            ],
            "by_status": [{"status": k, "count": v} for k, v in by_status.items()],
            "reopened": by_status.get("打回重审", 0),
        }
    )


@router.get("/{trial_id}", summary="审判记录详情")
async def get_trial(
    trial_id: int,
    user: CurrentUser = Depends(require_permission("trial:view")),
    db: AsyncSession = Depends(get_db),
):
    trial = await db.get(TrialRecord, trial_id)
    if trial is None:
        raise NotFoundError("审判记录不存在")
    ensure_data_scope(user, trial, "审判记录")
    data = model_to_dict(trial)
    data["court_name"] = COURT_NAMES[trial.court_level - 1]
    return resp_ok(data)


@router.post("", summary="立案送审（提审开堂）")
async def create_trial(
    payload: TrialCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("trial:create")),
    db: AsyncSession = Depends(get_db),
):
    soul = await db.get(Soul, payload.soul_id)
    if soul is None or soul.is_deleted:
        raise NotFoundError("亡魂不存在")
    if soul.status != SoulStatus.PENDING_TRIAL.value:
        raise ConflictError(f"亡魂当前状态为「{soul.status}」，仅「待审」可立案送审")

    pending = (
        await db.execute(
            select(TrialRecord).where(
                TrialRecord.soul_id == soul.id,
                TrialRecord.status.in_(["待审", "审理中"]),
            )
        )
    ).scalar_one_or_none()
    if pending is not None:
        raise ConflictError(f"该亡魂已有在审记录 {pending.trial_no}")

    transition = await change_soul_status(db, soul, "start_trial", reason=f"提审至{COURT_NAMES[payload.court_level - 1]}")

    trial_no = await next_code(db, TrialRecord, "trial_no", "SP", 5)
    trial = TrialRecord(
        trial_no=trial_no,
        soul_id=soul.id,
        soul_name=soul.name,
        court_level=payload.court_level,
        region=soul.region,
        judge_id=user.officer.id,
        judge_name=user.officer.real_name,
        karma_snapshot=soul.karma_score,
        guilt_desc=payload.guilt_desc,
        status="待审",
    )
    db.add(trial)
    await db.flush()

    await write_audit(
        db,
        action="create",
        module="十殿审判",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="trial",
        resource_id=trial.id,
        detail=f"立案 {trial_no}：{soul.name} 送 {COURT_NAMES[payload.court_level - 1]}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok({"trial": model_to_dict(trial), "transition": transition}, msg="已立案送审")


@router.post("/{trial_id}/handle", summary="开堂审理")
async def handle_trial(
    trial_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("trial:handle")),
    db: AsyncSession = Depends(get_db),
):
    trial = await db.get(TrialRecord, trial_id)
    if trial is None:
        raise NotFoundError("审判记录不存在")
    ensure_data_scope(user, trial, "审判记录")
    if trial.status != "待审":
        raise ConflictError(f"当前状态为「{trial.status}」，不可开庭")

    trial.status = "审理中"
    trial.started_at = utcnow()
    trial.judge_id = user.officer.id
    trial.judge_name = user.officer.real_name

    await write_audit(
        db,
        action="handle",
        module="十殿审判",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="trial",
        resource_id=trial.id,
        detail=f"{trial.trial_no} 开堂审理（{COURT_NAMES[trial.court_level - 1]}）",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(trial), msg="已开庭")


@router.post("/{trial_id}/verdict", summary="宣读判决（支持升级/打回/还阳/发配枉死城）")
async def verdict_trial(
    trial_id: int,
    payload: VerdictIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("trial:verdict")),
    db: AsyncSession = Depends(get_db),
):
    trial = await db.get(TrialRecord, trial_id)
    if trial is None:
        raise NotFoundError("审判记录不存在")
    ensure_data_scope(user, trial, "审判记录")
    if trial.status not in ("待审", "审理中"):
        raise ConflictError(f"当前状态为「{trial.status}」，不可判决")
    if payload.verdict not in VERDICTS:
        raise AppError(f"非法判决类型，可选：{'、'.join(VERDICTS)}")

    soul = await db.get(Soul, trial.soul_id) if trial.soul_id else None
    if soul is None:
        raise NotFoundError("审判关联亡魂不存在")

    now = utcnow()
    events: list[dict] = []
    next_trial: TrialRecord | None = None

    # 1) 升殿审理：结本殿并转下一殿
    if payload.verdict == "有罪" and payload.next_court_level > trial.court_level:
        trial.status = "已结案"
        trial.verdict = "移交上级殿"
        trial.verdict_detail = payload.verdict_detail or f"案情重大，移交{COURT_NAMES[payload.next_court_level - 1]}复核"
        trial.closed_at = now
        trial.next_court_level = payload.next_court_level

        next_no = await next_code(db, TrialRecord, "trial_no", "SP", 5)
        next_trial = TrialRecord(
            trial_no=next_no,
            soul_id=soul.id,
            soul_name=soul.name,
            court_level=payload.next_court_level,
            region=soul.region,
            judge_id=user.officer.id,
            judge_name=user.officer.real_name,
            karma_snapshot=soul.karma_score,
            guilt_desc=trial.guilt_desc,
            status="待审",
        )
        db.add(next_trial)

    # 2) 打回重审：回退到下一级殿重新审理，亡魂停留在审判中
    elif payload.verdict == "打回重审":
        trial.status = "打回重审"
        trial.verdict = "打回重审"
        trial.verdict_detail = payload.verdict_detail or "证据不足，打回重审"
        trial.closed_at = now
        lower_level = max(1, trial.court_level - 1)
        trial.next_court_level = lower_level

        next_no = await next_code(db, TrialRecord, "trial_no", "SP", 5)
        next_trial = TrialRecord(
            trial_no=next_no,
            soul_id=soul.id,
            soul_name=soul.name,
            court_level=lower_level,
            region=soul.region,
            judge_id=user.officer.id,
            judge_name=user.officer.real_name,
            karma_snapshot=soul.karma_score,
            guilt_desc=trial.guilt_desc,
            status="待审",
        )
        db.add(next_trial)

    # 3) 其余判决
    else:
        trial.status = "已结案"
        trial.verdict = payload.verdict
        trial.verdict_detail = payload.verdict_detail
        trial.sentence_years = payload.sentence_years
        trial.hell_level = payload.hell_level
        trial.closed_at = now

        if payload.verdict == "有罪":
            if payload.sentence_years > 0 and payload.hell_level > 0:
                punish_no = await next_code(db, Punishment, "punish_no", "XQ", 5)
                db.add(
                    Punishment(
                        punish_no=punish_no,
                        soul_id=soul.id,
                        soul_name=soul.name,
                        trial_record_id=trial.id,
                        region=soul.region,
                        hell_level=payload.hell_level,
                        hell_name=HELL_NAMES[payload.hell_level - 1],
                        sentence_years=payload.sentence_years,
                        start_at=now,
                        end_at=now + timedelta(days=365 * payload.sentence_years),
                        status="待执行",
                        progress=0,
                    )
                )
                await db.flush()
            events.append(await change_soul_status(db, soul, "convict", reason="十殿定罪"))
            if payload.sentence_years > 0 and payload.hell_level > 0:
                events.append(await change_soul_status(db, soul, "sentence", reason="交付刑期执行"))

        elif payload.verdict == "无罪":
            events.append(await change_soul_status(db, soul, "acquit_rebirth", reason="无罪释放，转轮回"))

        elif payload.verdict == "还阳":
            events.append(await change_soul_status(db, soul, "grant_return", reason="判令还阳"))

        elif payload.verdict == "发配枉死城":
            punish_no = await next_code(db, Punishment, "punish_no", "XQ", 5)
            db.add(
                Punishment(
                    punish_no=punish_no,
                    soul_id=soul.id,
                    soul_name=soul.name,
                    trial_record_id=trial.id,
                    region=soul.region,
                    hell_level=payload.hell_level or 18,
                    hell_name=HELL_NAMES[(payload.hell_level or 18) - 1],
                    sentence_years=max(1, payload.sentence_years),
                    start_at=now,
                    end_at=now + timedelta(days=365 * max(1, payload.sentence_years)),
                    status="待执行",
                    progress=0,
                )
            )
            await db.flush()
            events.append(await change_soul_status(db, soul, "convict", reason="发配枉死城"))
            events.append(await change_soul_status(db, soul, "sentence", reason="交付刑期执行"))
            events.append(await change_soul_status(db, soul, "to_wrongful", reason="押入枉死城"))

    await write_audit(
        db,
        action="verdict",
        module="十殿审判",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="trial",
        resource_id=trial.id,
        detail=(
            f"{trial.trial_no}（{COURT_NAMES[trial.court_level - 1]}）判决：{payload.verdict}"
            f"{'；' + payload.verdict_detail if payload.verdict_detail else ''}"
            f"；亡魂最终状态：{soul.status}"
        ),
        level="正常" if payload.verdict not in ("打回重审", "还阳") else "告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()

    return resp_ok(
        {
            "trial": model_to_dict(trial),
            "next_trial": model_to_dict(next_trial) if next_trial else None,
            "soul_status": soul.status,
            "transitions": events,
        },
        msg=f"判决已宣读：{payload.verdict}",
    )
