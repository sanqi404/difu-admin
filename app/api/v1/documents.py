"""文书管理：路引、拘票、判决书、轮回文书、还阳令的签发与核验。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DOC_STATUS, DOC_TYPES
from app.core.deps import CurrentUser, client_ip, client_ua, require_permission
from app.core.response import AppError, ConflictError, NotFoundError, page_resp, resp_ok
from app.core.utils import like_filter, model_to_dict, models_to_list, paginate
from app.database import get_db, utcnow
from app.models import CityGod, Document, Soul, SummonOrder
from app.schemas import DocumentCreateIn
from app.services.audit import write_audit
from app.services.numbering import next_code

router = APIRouter(prefix="/documents", tags=["文书管理"])


@router.get("", summary="文书列表")
async def list_documents(
    keyword: str = Query(""),
    doc_type: str = Query(""),
    status: str = Query(""),
    soul_id: int | None = Query(None),
    city_god_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: CurrentUser = Depends(require_permission("doc:view")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document)
    if keyword:
        stmt = stmt.where(
            or_(like_filter(Document.doc_no, keyword), like_filter(Document.soul_name, keyword), like_filter(Document.title, keyword))
        )
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    if status:
        stmt = stmt.where(Document.status == status)
    if soul_id:
        stmt = stmt.where(Document.soul_id == soul_id)
    if city_god_id:
        stmt = stmt.where(Document.city_god_id == city_god_id)

    stmt = stmt.order_by(Document.id.desc())
    items, total = await paginate(db, stmt, page, page_size)
    return page_resp(models_to_list(items), total, page, page_size)


@router.get("/{doc_id}", summary="文书详情")
async def get_document(
    doc_id: int,
    user: CurrentUser = Depends(require_permission("doc:view")),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise NotFoundError("文书不存在")
    return resp_ok(model_to_dict(doc))


@router.post("", summary="起草文书")
async def create_document(
    payload: DocumentCreateIn,
    request: Request,
    user: CurrentUser = Depends(require_permission("doc:issue")),
    db: AsyncSession = Depends(get_db),
):
    if payload.doc_type not in DOC_TYPES:
        raise AppError(f"非法文书类型，可选：{'、'.join(DOC_TYPES)}")

    soul = await db.get(Soul, payload.soul_id) if payload.soul_id else None
    if payload.soul_id and soul is None:
        raise NotFoundError("关联亡魂不存在")
    if payload.summon_order_id and await db.get(SummonOrder, payload.summon_order_id) is None:
        raise NotFoundError("关联工单不存在")
    if payload.city_god_id and await db.get(CityGod, payload.city_god_id) is None:
        raise NotFoundError("关联城隍网点不存在")

    prefix = {"路引": "LY", "拘票": "JP", "判决书": "PJ", "轮回文书": "LH", "还阳令": "HY", "冻结令": "DJ"}.get(payload.doc_type, "WS")
    doc_no = await next_code(db, Document, "doc_no", prefix, 5)
    doc = Document(
        doc_no=doc_no,
        doc_type=payload.doc_type,
        title=payload.title or f"{payload.doc_type}-{soul.name if soul else '无名'}",
        soul_id=payload.soul_id,
        soul_name=soul.name if soul else "",
        summon_order_id=payload.summon_order_id,
        city_god_id=payload.city_god_id or (soul.city_god_id if soul else None),
        content=payload.content,
        status="草稿",
    )
    db.add(doc)
    await db.flush()
    await write_audit(
        db,
        action="create",
        module="文书管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="document",
        resource_id=doc.id,
        detail=f"起草{doc.doc_type} {doc_no}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(doc), msg="文书已起草")


@router.post("/{doc_id}/issue", summary="签发文书")
async def issue_document(
    doc_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("doc:issue")),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise NotFoundError("文书不存在")
    if doc.status != "草稿":
        raise ConflictError(f"当前状态为「{doc.status}」，仅草稿可签发")
    doc.status = "已签发"
    doc.issued_by = user.officer.real_name
    doc.issued_at = utcnow()
    await write_audit(
        db,
        action="issue",
        module="文书管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="document",
        resource_id=doc.id,
        detail=f"签发{doc.doc_type} {doc.doc_no}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(doc), msg="文书已签发")


@router.post("/{doc_id}/verify", summary="核验文书（鬼门关验引）")
async def verify_document(
    doc_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("doc:verify")),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise NotFoundError("文书不存在")
    if doc.status == "已作废":
        raise ConflictError("文书已作废，不可核验")
    if doc.status == "草稿":
        raise ConflictError("文书尚未签发，不可核验")
    if doc.status == "已核验":
        raise ConflictError("文书已核验，请勿重复操作")
    doc.status = "已核验"
    doc.verified_by = user.officer.real_name
    doc.verified_at = utcnow()
    await write_audit(
        db,
        action="verify",
        module="文书管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="document",
        resource_id=doc.id,
        detail=f"核验{doc.doc_type} {doc.doc_no}",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(doc), msg="文书已核验")


@router.post("/{doc_id}/void", summary="作废文书")
async def void_document(
    doc_id: int,
    request: Request,
    user: CurrentUser = Depends(require_permission("doc:void")),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise NotFoundError("文书不存在")
    if doc.status == "已作废":
        raise ConflictError("文书已作废")
    doc.status = "已作废"
    await write_audit(
        db,
        action="void",
        module="文书管理",
        officer_id=user.officer.id,
        officer_name=user.officer.real_name,
        role_name=user.role.name,
        resource="document",
        resource_id=doc.id,
        detail=f"作废{doc.doc_type} {doc.doc_no}",
        level="告警",
        ip=client_ip(request),
        user_agent=client_ua(request),
    )
    await db.commit()
    return resp_ok(model_to_dict(doc), msg="文书已作废")
