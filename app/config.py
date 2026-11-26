"""全局配置：双通道（dev / prod）由 ENV_MODE 切换，业务代码只依赖 DATABASE_URL 与 CacheBackend。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

# dev：SQLite（文件落在项目 data/ 目录）
DEV_DATABASE_URL = "sqlite+aiosqlite:///./data/difu_dev.db"
# prod：MySQL（真实连接串请写入 .env 的 PROD_DATABASE_URL，不要提交到版本库）
PROD_DATABASE_URL = os.getenv(
    "PROD_DATABASE_URL",
    "mysql+pymysql://<user>:<password>@<db_host>:3306/difu_admin?charset=utf8mb4",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ---------- 基础 ----------
    ENV_MODE: Literal["dev", "prod"] = "dev"
    APP_NAME: str = "地府生死铺后台管理系统"
    APP_VERSION: str = "1.0.0-p1"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # ---------- 数据库 ----------
    DATABASE_URL: str = ""
    # prod 模式 MySQL 连接串：请写在 .env 中（.env 已被 .gitignore 排除）
    PROD_DATABASE_URL: str = ""
    DB_ECHO: bool = False

    # ---------- 缓存 ----------
    CACHE_BACKEND: str = ""  # 留空按 ENV_MODE 自动选择；可强制 memory / redis
    REDIS_URL: str = "redis://127.0.0.1:6379/3"
    CACHE_PREFIX: str = "difu"
    CACHE_DEFAULT_TTL: int = 300

    # ---------- JWT ----------
    JWT_SECRET: str = "change-me-to-a-random-long-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---------- 图形验证码 ----------
    CAPTCHA_LENGTH: int = 4
    CAPTCHA_EXPIRE_SECONDS: int = 120
    # dev 联调便捷码：仅 ENV_MODE=dev 生效，prod 请置空
    CAPTCHA_DEV_CODE: str = "0000"

    # ---------- CORS ----------
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---------- 种子数据 ----------
    SEED_ADMIN_USERNAME: str = "admin"
    SEED_ADMIN_PASSWORD: str = "123123"

    @model_validator(mode="after")
    def _fill_defaults(self) -> "Settings":
        if not self.DATABASE_URL:
            object.__setattr__(
                self,
                "DATABASE_URL",
                DEV_DATABASE_URL
                if self.ENV_MODE == "dev"
                else (self.PROD_DATABASE_URL or PROD_DATABASE_URL),
            )
        if not self.CACHE_BACKEND:
            object.__setattr__(
                self, "CACHE_BACKEND", "memory" if self.ENV_MODE == "dev" else "redis"
            )
        return self

    # ---------- 派生属性 ----------
    @property
    def is_dev(self) -> bool:
        return self.ENV_MODE == "dev"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sqlite_file(self) -> Path | None:
        """SQLite 场景下解析出物理文件路径，便于建目录 / 清理。"""
        if not self.is_sqlite:
            return None
        raw = self.DATABASE_URL.split("///", 1)[-1]
        p = Path(raw)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
