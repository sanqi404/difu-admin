"""生死簿：流水查询、改命录入、复核/驳回。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    CurrentUser,
    client_ip,
    client_ua,
    ensure_data_scope,
    require_permission,
    scope_conditions,
)
from app.core.response import ConflictError, NotFoundError, resp_ok, page_resp
from app.core.utils import like_filter, model_to_dict, models_to_list, paginate
from app.database import get_db, utcnow
from app.models import LifeBook, Soul
from app.schemas import LifeBookCreateIn, LifeBookUpdateIn, ReviewIn
from app.services.audit import write_audit
from app.services.numbering import next_code

router = APIRouter(prefix="/life-books", tags=["生死簿"])


@router.get("", summary="生死簿流水列表")
async def list_life_books(
    keyword: str = Query("", description="亡魂姓名 / 流水号"),
    review_status: str = Query(""),
    action: str = Query(""),
    region: str = Query(""),
    is_tampered: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("lifebook:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(LifeBook)
    if keyword:
        stmt = stmt.where(
            or_(like_filter(LifeBook.soul_name, keyword), like_filter(LifeBook.book_no, keyword))
        )
    if review_status:
        stmt = stmt.where(LifeBook.review_status == review_status)
    if action:
        stmt = stmt.where(LifeBook.action == action)
    if is_tampered is not None:
        stmt = stmt.where(LifeBook.is_tampered.is_(is_tampered))
    # 生死簿按亡魂所在鬼域做数据域隔离
    if not user.is_super and user.data_scope != "ALL":
        soul_ids = select(Soul.id).where(Soul.region == user.officer.region)
        stmt = stmt.where(or_(LifeBook.soul_id.in_(soul_ids), LifeBook.soul_id.is_(None)))
    if region:
        stmt = stmt.where(LifeBook.soul_name.in_(select(Soul.name).where(Soul.region == region)))

    stmt = stmt.order_by(LifeBook.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/summary", summary="生死簿复核状态统计")
async def life_book_summary(
    user: CurrentUser = Depends(require_permission("lifebook:view")),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(LifeBook))).scalars().all()
    counter: dict[str, int] = {}
    for row in rows:
        counter[row.review_status] = counter.get(row.review_status, 0) + 1
    tampered = sum(1 for r in rows if r.is_tampered)
    return resp_ok(
        {
            "total": len(rows),
            "by_review_status": [{"status": k, "count": v} for k, v in counter.items()],
            "pending": counter.get("待复核", 0),
            "tampered": tampered,
        }
    )


@router.get("/{book_id}", summary="生死簿流水详情")
async def get_life_book(
    book_id: int,
    user: CurrentUser = Depends(require_permission("lifebook:view")),
    db: AsyncSession = Depends(get_db),
):
    book = await db.get(LifeBook, book_id)
    if book is None:
        raise NotFoundError("生死簿流水不存在")
    return resp_ok(model_to_dict(book))


@router.post("", summary="生死簿改命录入（默认待复核）")
async def create_life_book(
    payload: LifeBookCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("lifebook:create")),
    db: AsyncSession = Depends(get_db),
):
    book_no = await next_code(db, LifeBook, "book_no", "SSB", 5)
    soul = await db.get(Soul, payload.soul_id) if payload.soul_id else None
    if payload.soul_id and soul is None:
        raise NotFoundError("关联亡魂不存在")

    book = LifeBook(
        book_no=book_no,
        soul_id=payload.soul_id,
        soul_name=payload.soul_name or (soul.name if soul else ""),
        action=payload.action,
        lifespan_years=payload.lifespan_years,
        before_content=payload.before_content,
        after_content=payload.after_content,
        diff_desc=payload.diff_desc,
        review_status="待复核",
        operator_id=user.officer.id,
    )
    db.add(book)
    await db.flush()
    if soul is not None:
        soul.life_book_no = book_no

    await write_audit(
        db,
        action="create",
        module="生死簿",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="life_book",
        resource_id=book.id,
        detail=f"{payload.action} {book.soul_name} 阳寿 {payload.lifespan_years} 年，待复核",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(book), msg="已录入，等待复核")


@router.put("/{book_id}", summary="修改待复核流水")
async def update_life_book(
    book_id: int,
    payload: LifeBookUpdateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("lifebook:update")),
    db: AsyncSession = Depends(get_db),
):
    book = await db.get(LifeBook, book_id)
    if book is None:
        raise NotFoundError("生死簿流水不存在")
    if book.review_status != "待复核":
        raise ConflictError(f"当前状态为「{book.review_status}」，不可修改")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    await write_audit(
        db,
        action="update",
        module="生死簿",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="life_book",
        resource_id=book.id,
        detail=f"修改 {book.book_no} 待复核内容",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(book), msg="已保存")


@router.post("/{book_id}/review", summary="复核通过")
async def approve_life_book(
    book_id: int,
    payload: ReviewIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("lifebook:review")),
    db: AsyncSession = Depends(get_db),
):
    book = await db.get(LifeBook, book_id)
    if book is None:
        raise NotFoundError("生死簿流水不存在")
    if book.review_status != "待复核":
        raise ConflictError(f"当前状态为「{book.review_status}」，无需复核")

    book.review_status = "已复核"
    book.reviewer_id = user.officer.id
    book.reviewer_name = user.officer.real_name
    book.reviewed_at = utcnow()
    book.review_comment = payload.comment

    await write_audit(
        db,
        action="review_pass",
        module="生死簿",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="life_book",
        resource_id=book.id,
        detail=f"复核通过 {book.book_no}（{book.soul_name}）{('；意见：' + payload.comment) if payload.comment else ''}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(book), msg="复核通过")


@router.post("/{book_id}/reject", summary="复核驳回")
async def reject_life_book(
    book_id: int,
    payload: ReviewIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("lifebook:review")),
    db: AsyncSession = Depends(get_db),
):
    book = await db.get(LifeBook, book_id)
    if book is None:
        raise NotFoundError("生死簿流水不存在")
    if book.review_status != "待复核":
        raise ConflictError(f"当前状态为「{book.review_status}」，无需复核")
    if not payload.comment.strip():
        raise ConflictError("驳回必须填写意见")

    book.review_status = "已驳回"
    book.reviewer_id = user.officer.id
    book.reviewer_name = user.officer.real_name
    book.reviewed_at = utcnow()
    book.review_comment = payload.comment

    await write_audit(
        db,
        action="review_reject",
        module="生死簿",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="life_book",
        resource_id=book.id,
        detail=f"驳回 {book.book_no}（{book.soul_name}）；意见：{payload.comment}",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(book), msg="已驳回")
