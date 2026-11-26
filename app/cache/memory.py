"""进程内内存缓存实现（ENV_MODE=dev 使用）。"""

from __future__ import annotations

import asyncio
import time

from app.cache.base import CacheBackend


class MemoryCache(CacheBackend):
    name = "memory"

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}
        self._lock = asyncio.Lock()

    def _expired(self, expire_at: float | None) -> bool:
        return expire_at is not None and expire_at <= time.monotonic()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expire_at = item
            if self._expired(expire_at):
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        async with self._lock:
            expire_at = None if ttl is None or ttl <= 0 else time.monotonic() + ttl
            self._store[key] = (str(value), expire_at)
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    async def incr(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        async with self._lock:
            item = self._store.get(key)
            current = 0
            expire_at: float | None = None
            if item is not None and not self._expired(item[1]):
                current = int(item[0])
                expire_at = item[1]
            current += amount
            if expire_at is None and ttl is not None and ttl > 0:
                expire_at = time.monotonic() + ttl
            self._store[key] = (str(current), expire_at)
            return current

    async def ttl(self, key: str) -> int:
        async with self._lock:
            item = self._store.get(key)
            if item is None:
                return -2
            value, expire_at = item
            if self._expired(expire_at):
                self._store.pop(key, None)
                return -2
            if expire_at is None:
                return -1
            return max(0, int(expire_at - time.monotonic()))

    async def clear_prefix(self, prefix: str = "") -> int:
        async with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                self._store.pop(k, None)
            return len(keys)

    async def close(self) -> None:
        self._store.clear()
