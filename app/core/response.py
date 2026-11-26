"""统一响应体与业务异常。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

# 业务码约定
CODE_OK = 0
CODE_BAD_REQUEST = 400
CODE_UNAUTHORIZED = 401
CODE_FORBIDDEN = 403
CODE_NOT_FOUND = 404
CODE_CONFLICT = 409
CODE_SERVER_ERROR = 500


class AppError(Exception):
    """业务异常：由全局异常处理器转成统一响应体。"""

    def __init__(
        self,
        msg: str = "操作失败",
        code: int = CODE_BAD_REQUEST,
        http_status: int = 400,
        data: Any = None,
    ) -> None:
        self.msg = msg
        self.code = code
        self.http_status = http_status
        self.data = data
        super().__init__(msg)


class UnauthorizedError(AppError):
    def __init__(self, msg: str = "登录状态已失效，请重新登录") -> None:
        super().__init__(msg=msg, code=CODE_UNAUTHORIZED, http_status=401)


class ForbiddenError(AppError):
    def __init__(self, msg: str = "无权访问该资源") -> None:
        super().__init__(msg=msg, code=CODE_FORBIDDEN, http_status=403)


class NotFoundError(AppError):
    def __init__(self, msg: str = "资源不存在") -> None:
        super().__init__(msg=msg, code=CODE_NOT_FOUND, http_status=404)


class ConflictError(AppError):
    def __init__(self, msg: str = "状态冲突") -> None:
        super().__init__(msg=msg, code=CODE_CONFLICT, http_status=409)


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    pages: int


class PageData(BaseModel):
    items: list[Any]
    meta: PageMeta


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resp_ok(data: Any = None, msg: str = "success") -> dict[str, Any]:
    return {"code": CODE_OK, "msg": msg, "data": data, "timestamp": _now_iso()}


def resp_fail(msg: str = "操作失败", code: int = CODE_BAD_REQUEST, data: Any = None) -> dict[str, Any]:
    return {"code": code, "msg": msg, "data": data, "timestamp": _now_iso()}


def page_resp(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    pages = (total + page_size - 1) // page_size if page_size else 0
    return resp_ok(
        {
            "items": items,
            "meta": {"page": page, "page_size": page_size, "total": total, "pages": pages},
        }
    )
