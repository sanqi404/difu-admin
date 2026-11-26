"""JWT 签发/校验与密码散列。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.response import UnauthorizedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(raw: str) -> str:
    # bcrypt 仅取前 72 字节，超长密码先截断避免底层报错
    return pwd_context.hash(raw[:72])


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(raw[:72], hashed)
    except (ValueError, TypeError):
        return False


def _create_token(payload: dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
        "type": token_type,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(officer_id: int, username: str, role_code: str) -> str:
    return _create_token(
        {"sub": str(officer_id), "username": username, "role": role_code},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        TOKEN_TYPE_ACCESS,
    )


def create_refresh_token(officer_id: int, username: str, role_code: str) -> str:
    return _create_token(
        {"sub": str(officer_id), "username": username, "role": role_code},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        TOKEN_TYPE_REFRESH,
    )


def decode_token(token: str, expect_type: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise UnauthorizedError(f"令牌无效或已过期：{exc}") from exc
    if expect_type and payload.get("type") != expect_type:
        raise UnauthorizedError("令牌类型不匹配")
    if not payload.get("sub"):
        raise UnauthorizedError("令牌载荷缺失")
    return payload


def bearer_jti(token: str) -> str:
    """从令牌中取出 jti，用于登出黑名单。"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        return payload.get("jti", "")
    except JWTError:
        return ""


def token_remaining_seconds(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        exp = int(payload.get("exp", 0))
        return max(0, exp - int(datetime.now(timezone.utc).timestamp()))
    except (JWTError, TypeError, ValueError):
        return 0
