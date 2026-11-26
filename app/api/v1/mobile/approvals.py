"""移动端 H5 · 审批中心：待办 / 我发起 / 已办、详情、同意 / 驳回 / 转交。

审批链规则统一由 app.core.constants.resolve_approval_chain 解析，
数据域隔离：仅申请人本人、审批链上的审批人、超级管理员可查看审批单。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    APPROVAL_ACTION_LABELS,
    APPROVAL_BIZ_PERMISSION,
    APPROVAL_CHAIN_RULES,
    APPROVAL_STATUS_AGREED,
    APPROVAL_STATUS_FINAL,
    APPROVAL_STATUS_REJECTED,
    APPROVAL_STEP_AGREE,
    APPROVAL_STEP_LOCKED,
    APPROVAL_STEP_REJECT,
    APPROVAL_STEP_TRANSFER,
    APPROVAL_STEP_WAIT,
    BIZ_TYPE_LIST,
    approval_status_label,
    resolve_approval_chain,
)
from app.core.deps import CurrentUser, client_ip, client_ua, get_current_user
from app.core.response import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    page_resp,
    resp_ok,
)
from app.core.utils import model_to_dict, paginate
from app.database import get_db, utcnow
from app.models import ApprovalRequest, ApprovalStep, MobileMessage, Officer
from app.schemas import ApprovalActionIn
from app.services.audit import write_audit

router = APIRouter(prefix="/mobile/approvals", tags=["移动端-审批中心"])

SCOPE_TODO = "todo"
SCOPE_MINE = "mine"
SCOPE_DONE = "done"
SCOPES = (SCOPE_TODO, SCOPE_MINE, SCOPE_DONE)


# ----------------------------------------------------------------------------
# 内部工具
# ----------------------------------------------------------------------------
def _load_payload(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {"value": data}


def _chain_of(req: ApprovalRequest):
    """按审批单载荷中的 years 复算审批链，用于推进后回写环节标签。"""
    payload = _load_payload(req.payload_json)
    years = payload.get("years")
    if isinstance(years, bool) or years is None:
        years = None
    elif isinstance(years, int):
        pass
    elif isinstance(years, float):
        years = int(years)
    elif isinstance(years, str) and years.strip().isdigit():
        years = int(years.strip())
    else:
        years = None
    try:
        return resolve_approval_chain(req.biz_type, years=years)
    except ValueError:
        return []


async def _steps_of(db: AsyncSession, request_ids: list[int]) -> dict[int, list[ApprovalStep]]:
    if not request_ids:
        return {}
    rows = (
        await db.execute(
            select(ApprovalStep)
            .where(ApprovalStep.request_id.in_(request_ids))
            .order_by(ApprovalStep.step_no, ApprovalStep.id)
        )
    ).scalars().all()
    grouped: dict[int, list[ApprovalStep]] = {}
    for row in rows:
        grouped.setdefault(row.request_id, []).append(row)
    return grouped


async def _officer_names(db: AsyncSession, officer_ids: set[int | None]) -> dict[int, str]:
    ids = {i for i in officer_ids if i}
    if not ids:
        return {}
    rows = (await db.execute(select(Officer.id, Officer.real_name).where(Officer.id.in_(ids)))).all()
    return {row[0]: row[1] for row in rows}


def _serialize_step(step: ApprovalStep, names: dict[int, str]) -> dict[str, Any]:
    data = model_to_dict(step)
    data["approver_name"] = names.get(step.approver_id or 0, "")
    data["action_label"] = APPROVAL_ACTION_LABELS.get(step.action, step.action)
    return data


def _serialize_request(
    req: ApprovalRequest,
    steps: list[ApprovalStep],
    names: dict[int, str],
    me_id: int,
) -> dict[str, Any]:
    data = model_to_dict(req)
    data["payload"] = _load_payload(req.payload_json)
    waiting = [s for s in steps if s.action == APPROVAL_STEP_WAIT]
    if waiting:
        current_step = min(s.step_no for s in waiting)
    else:
        current_step = max((s.step_no for s in steps), default=1)
    data["current_step"] = current_step
    data["is_final"] = req.status in APPROVAL_STATUS_FINAL
    data["can_action"] = any(s.action == APPROVAL_STEP_WAIT and s.approver_id == me_id for s in steps)
    data["applicant_name"] = names.get(req.applicant_id or 0, "")
    data["biz_permission"] = APPROVAL_BIZ_PERMISSION.get(req.biz_type, "")
    data["steps"] = [_serialize_step(s, names) for s in steps]
    return data


async def _push_message(
    db: AsyncSession,
    *,
    receiver_id: int | None,
    msg_type: str,
    title: str,
    content: str,
    biz_ref: str,
    priority: str = "普通",
) -> None:
    """审批流转时同步投递移动端消息（不单独提交事务）。"""
    if not receiver_id:
        return
    db.add(
        MobileMessage(
            receiver_id=receiver_id,
            type=msg_type,
            title=title,
            content=content,
            biz_ref=biz_ref,
            is_read=False,
            priority=priority,
        )
    )


# ----------------------------------------------------------------------------
# 接口
# ----------------------------------------------------------------------------
@router.get("/rules", summary="审批链规则说明")
async def approval_rules(user: CurrentUser = Depends(get_current_user)) -> Any:
    return resp_ok(
        {
            "biz_types": BIZ_TYPE_LIST,
            "rules": APPROVAL_CHAIN_RULES,
            "actions": APPROVAL_ACTION_LABELS,
            "status_final": APPROVAL_STATUS_FINAL,
        },
        msg="审批链规则",
    )


@router.get("", summary="审批单列表")
async def list_approvals(
    scope: str = Query(SCOPE_TODO, description="todo 待我审批 / mine 我发起 / done 我审批过"),
    biz_type: str = Query("", description="按业务类型过滤"),
    keyword: str = Query("", description="标题/摘要关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if scope not in SCOPES:
        raise AppError("scope 仅支持 todo / mine / done")
    if biz_type and biz_type not in BIZ_TYPE_LIST:
        raise AppError(f"未知的业务类型：{biz_type}")

    stmt = select(ApprovalRequest)
    if biz_type:
        stmt = stmt.where(ApprovalRequest.biz_type == biz_type)
    if keyword:
        stmt = stmt.where(
            or_(
                ApprovalRequest.title.like(f"%{keyword}%"),
                ApprovalRequest.summary.like(f"%{keyword}%"),
            )
        )

    me = user.officer.id
    if scope == SCOPE_TODO:
        todo_ids = select(ApprovalStep.request_id).where(
            ApprovalStep.approver_id == me,
            ApprovalStep.action == APPROVAL_STEP_WAIT,
        )
        stmt = stmt.where(
            ApprovalRequest.id.in_(todo_ids),
            ApprovalRequest.status.notin_(APPROVAL_STATUS_FINAL),
        ).order_by(
            ApprovalRequest.deadline_at.is_(None),
            ApprovalRequest.deadline_at.asc(),
            ApprovalRequest.id.desc(),
        )
    elif scope == SCOPE_MINE:
        stmt = stmt.where(ApprovalRequest.applicant_id == me).order_by(ApprovalRequest.id.desc())
    else:
        done_ids = select(ApprovalStep.request_id).where(
            ApprovalStep.approver_id == me,
            ApprovalStep.action.in_([APPROVAL_STEP_AGREE, APPROVAL_STEP_REJECT, APPROVAL_STEP_TRANSFER]),
        )
        stmt = stmt.where(ApprovalRequest.id.in_(done_ids)).order_by(ApprovalRequest.id.desc())

    items, total = await paginate(db, stmt, page, page_size)
    steps_map = await _steps_of(db, [i.id for i in items])
    names = await _officer_names(
        db,
        {i.applicant_id for i in items}
        | {s.approver_id for group in steps_map.values() for s in group},
    )
    data = [_serialize_request(i, steps_map.get(i.id, []), names, me) for i in items]
    return page_resp(data, total, page, page_size)


@router.get("/{request_id}", summary="审批单详情")
async def get_approval(
    request_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    req = await db.get(ApprovalRequest, request_id)
    if req is None:
        raise NotFoundError("审批单不存在")
    steps = (await _steps_of(db, [req.id])).get(req.id, [])
    involved = req.applicant_id == user.officer.id or any(s.approver_id == user.officer.id for s in steps)
    if not (involved or user.is_super):
        raise ForbiddenError("无权查看该审批单")
    names = await _officer_names(
        db, {req.applicant_id} | {s.approver_id for s in steps}
    )
    return resp_ok(_serialize_request(req, steps, names, user.officer.id), msg="审批单详情")


@router.post("/{request_id}/action", summary="审批动作：同意 / 驳回 / 转交")
async def do_approval_action(
    request_id: int,
    payload: ApprovalActionIn,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    req = await db.get(ApprovalRequest, request_id)
    if req is None:
        raise NotFoundError("审批单不存在")
    if req.status in APPROVAL_STATUS_FINAL:
        raise ConflictError(f"该审批单已「{req.status}」，无法再操作")

    steps = (await _steps_of(db, [req.id])).get(req.id, [])
    mine = [s for s in steps if s.approver_id == user.officer.id and s.action == APPROVAL_STEP_WAIT]
    if not mine:
        raise ForbiddenError("当前环节的审批人不是你，无权处理该审批单")

    action = payload.action
    comment = payload.comment.strip()
    if action == APPROVAL_STEP_REJECT and not comment:
        raise AppError("驳回必须填写审批意见")
    target: Officer | None = None
    if action == APPROVAL_STEP_TRANSFER:
        if not payload.transfer_to:
            raise AppError("转交必须指定目标审批人")
        target = await db.get(Officer, payload.transfer_to)
        if target is None:
            raise AppError("转交目标审批人不存在")
        if target.id == user.officer.id:
            raise AppError("不能转交给自己")
        if any(s.approver_id == target.id and s.action == APPROVAL_STEP_WAIT for s in steps):
            raise ConflictError("目标审批人已在当前环节的待办中")

    step_no = mine[0].step_no
    now = utcnow()
    for step in mine:
        step.action = action
        step.comment = comment or APPROVAL_ACTION_LABELS.get(action, action)
        step.acted_at = now

    next_label = ""
    if action == APPROVAL_STEP_TRANSFER:
        db.add(
            ApprovalStep(
                request_id=req.id,
                step_no=step_no,
                approver_id=target.id if target else None,
                action=APPROVAL_STEP_WAIT,
                comment=f"{user.officer.real_name} 转交",
            )
        )
        next_label = req.status
        await _push_message(
            db,
            receiver_id=target.id if target else None,
            msg_type="审批待办",
            title=f"转交审批：{req.title}",
            content=f"{user.officer.real_name} 将「{req.title}」转交给你审批。{comment}",
            biz_ref=f"approval:{req.id}",
            priority="重要",
        )
    elif action == APPROVAL_STEP_REJECT:
        next_label = APPROVAL_STATUS_REJECTED
        req.status = APPROVAL_STATUS_REJECTED
        await _push_message(
            db,
            receiver_id=req.applicant_id,
            msg_type="审批结果",
            title=f"审批驳回：{req.title}",
            content=f"{user.officer.real_name} 驳回「{req.title}」。意见：{comment}",
            biz_ref=f"approval:{req.id}",
            priority="重要",
        )
    else:
        await db.flush()
        remain = (
            await db.execute(
                select(func.count())
                .select_from(ApprovalStep)
                .where(
                    ApprovalStep.request_id == req.id,
                    ApprovalStep.step_no == step_no,
                    ApprovalStep.action == APPROVAL_STEP_WAIT,
                )
            )
        ).scalar_one()
        if remain == 0:
            locked = (
                await db.execute(
                    select(ApprovalStep)
                    .where(
                        ApprovalStep.request_id == req.id,
                        ApprovalStep.step_no > step_no,
                        ApprovalStep.action == APPROVAL_STEP_LOCKED,
                    )
                    .order_by(ApprovalStep.step_no, ApprovalStep.id)
                )
            ).scalars().all()
            if locked:
                for step in locked:
                    step.action = APPROVAL_STEP_WAIT
                chain = _chain_of(req)
                label = approval_status_label(chain[step_no]) if step_no < len(chain) else ""
                next_label = label or f"L{locked[0].step_no}-待审批"
                req.status = next_label
                for step in locked:
                    await _push_message(
                        db,
                        receiver_id=step.approver_id,
                        msg_type="审批待办",
                        title=f"待你审批：{req.title}",
                        content=f"{req.biz_type}「{req.title}」已进入 {next_label} 环节。",
                        biz_ref=f"approval:{req.id}",
                        priority="重要",
                    )
            else:
                next_label = APPROVAL_STATUS_AGREED
                req.status = APPROVAL_STATUS_AGREED
                await _push_message(
                    db,
                    receiver_id=req.applicant_id,
                    msg_type="审批结果",
                    title=f"审批通过：{req.title}",
                    content=f"你发起的「{req.title}」已审批通过。",
                    biz_ref=f"approval:{req.id}",
                )
        else:
            next_label = req.status

    await write_audit(
        db,
        action=f"approval_{action}",
        module="移动审批",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="approval_request",
        resource_id=req.id,
        detail=f"{req.biz_type}｜{req.title}｜{APPROVAL_ACTION_LABELS.get(action, action)}，环节 {step_no} → {next_label}"
        + (f"；意见：{comment}" if comment else ""),
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    await db.refresh(req)
    latest = (await _steps_of(db, [req.id])).get(req.id, [])
    names = await _officer_names(db, {req.applicant_id} | {s.approver_id for s in latest})
    detail = _serialize_request(req, latest, names, user.officer.id)
    detail["action"] = action
    detail["action_label"] = APPROVAL_ACTION_LABELS.get(action, action)
    detail["next_step_label"] = next_label
    return resp_ok(detail, msg=f"审批已{APPROVAL_ACTION_LABELS.get(action, action)}")
