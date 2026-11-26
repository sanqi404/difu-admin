"""缓存抽象接口：业务代码只依赖 CacheBackend，不感知 Redis / 内存实现差异。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheBackend(ABC):
    """统一缓存接口（字符串语义，值统一按 str 存取）。"""

    name: str = "base"

    @abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int | None = None) -> bool: ...

    @abstractmethod
    async def delete(self, key: str) -> bool: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def incr(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        """原子自增，用于接口限流 / 登录失败计数。"""

    @abstractmethod
    async def ttl(self, key: str) -> int:
        """剩余存活秒数；-1 永久，-2 不存在。"""

    @abstractmethod
    async def clear_prefix(self, prefix: str = "") -> int:
        """按前缀清理（用于强制下线等场景），返回清理条数。"""

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> bool:
        import json  # noqa: PLC0415

        return await self.set(key, json.dumps(value, ensure_ascii=False, default=str), ttl)

    async def get_json(self, key: str) -> Any:
        import json  # noqa: PLC0415

        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    async def close(self) -> None:
        """释放连接，内存实现无需处理。"""
        return None
