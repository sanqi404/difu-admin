"""图形验证码：验证码文本走 CacheBackend 存储，图片以 base64 返回（无静态资源依赖）。"""

from __future__ import annotations

import base64
import io
import random
import uuid

from PIL import Image, ImageDraw, ImageFont

from app.cache.base import CacheBackend
from app.config import settings

# 去掉 0/O/1/I/l 等易混淆字符
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

CAPTCHA_KEY_PREFIX = "captcha:"


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


def _render(code: str) -> str:
    width, height = 128, 44
    img = Image.new("RGB", (width, height), (24, 20, 17))
    draw = ImageDraw.Draw(img)
    font = _load_font(28)

    # 干扰线
    for _ in range(5):
        draw.line(
            [
                (random.randint(0, width), random.randint(0, height)),
                (random.randint(0, width), random.randint(0, height)),
            ],
            fill=(random.randint(60, 120), random.randint(40, 90), random.randint(20, 60)),
            width=1,
        )
    # 噪点
    for _ in range(60):
        draw.point(
            (random.randint(0, width), random.randint(0, height)),
            fill=(random.randint(80, 160), random.randint(60, 120), random.randint(40, 90)),
        )
    # 字符
    step = width // (len(code) + 1)
    for idx, ch in enumerate(code):
        x = step * (idx + 1) - 10 + random.randint(-2, 2)
        y = random.randint(2, 8)
        draw.text((x, y), ch, font=font, fill=(230, 180, 90))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


async def create_captcha(cache: CacheBackend) -> dict[str, object]:
    length = settings.CAPTCHA_LENGTH
    code = "".join(random.choices(_ALPHABET, k=length))
    captcha_id = uuid.uuid4().hex
    await cache.set(
        f"{CAPTCHA_KEY_PREFIX}{captcha_id}", code, ttl=settings.CAPTCHA_EXPIRE_SECONDS
    )
    return {
        "captcha_id": captcha_id,
        "image": _render(code),
        "expires_in": settings.CAPTCHA_EXPIRE_SECONDS,
    }


async def verify_captcha(cache: CacheBackend, captcha_id: str, code: str) -> bool:
    """验证成功后立即删除，保证一次性使用。"""
    if not captcha_id or not code:
        return False
    key = f"{CAPTCHA_KEY_PREFIX}{captcha_id}"
    cached = await cache.get(key)
    if cached is None:
        return False
    await cache.delete(key)
    return cached.strip().upper() == code.strip().upper()
