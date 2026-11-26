"""Redis 缓存实现（ENV_MODE=prod，固定 db3）。"""

from __future__ import annotations

from loguru import logger
from redis.asyncio import Redis

from app.cache.base import CacheBackend


class RedisCache(CacheBackend):
    name = "redis"

    def __init__(self, url: str, key_prefix: str = "") -> None:
        self._client: Redis = Redis.from_url(url, encoding="utf-8", decode_responses=True)
        self._prefix = f"{key_prefix}:" if key_prefix else ""

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> str | None:
        return await self._client.get(self._k(key))

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        if ttl is not None and ttl > 0:
            return bool(await self._client.set(self._k(key), str(value), ex=ttl))
        return bool(await self._client.set(self._k(key), str(value)))

    async def delete(self, key: str) -> bool:
        return bool(await self._client.delete(self._k(key)))

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(self._k(key)))

    async def incr(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        k = self._k(key)
        value = await self._client.incrby(k, amount)
        if ttl is not None and ttl > 0 and value == amount:
            await self._client.expire(k, ttl)
        return int(value)

    async def ttl(self, key: str) -> int:
        return int(await self._client.ttl(self._k(key)))

    async def clear_prefix(self, prefix: str = "") -> int:
        pattern = f"{self._prefix}{prefix}*"
        count = 0
        async for key in self._client.scan_iter(match=pattern, count=500):
            await self._client.delete(key)
            count += 1
        return count

    async def close(self) -> None:
        try:
            await self._client.aclose()
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Redis 连接关闭异常: {exc}")
