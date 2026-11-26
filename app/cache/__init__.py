"""缓存工厂：按 CACHE_BACKEND（默认由 ENV_MODE 推导）单例提供 CacheBackend。"""

from __future__ import annotations

from loguru import logger

from app.cache.base import CacheBackend
from app.cache.memory import MemoryCache
from app.cache.redis_cache import RedisCache
from app.config import settings

_cache: CacheBackend | None = None


def build_cache() -> CacheBackend:
    backend = settings.CACHE_BACKEND.lower()
    if backend == "redis":
        logger.info(f"缓存通道: Redis -> {settings.REDIS_URL}")
        return RedisCache(settings.REDIS_URL, settings.CACHE_PREFIX)
    if backend == "memory":
        logger.info("缓存通道: 进程内 Memory")
        return MemoryCache()
    raise ValueError(f"未知缓存类型 CACHE_BACKEND={settings.CACHE_BACKEND}")


def get_cache() -> CacheBackend:
    global _cache
    if _cache is None:
        _cache = build_cache()
    return _cache


async def shutdown_cache() -> None:
    global _cache
    if _cache is not None:
        await _cache.close()
        _cache = None


__all__ = ["CacheBackend", "MemoryCache", "RedisCache", "get_cache", "shutdown_cache"]
