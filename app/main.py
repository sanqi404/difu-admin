"""地府生死铺后台管理系统 —— 应用入口。"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import api_router
from app.cache import get_cache, shutdown_cache
from app.config import settings
from app.core.response import (
    CODE_BAD_REQUEST,
    CODE_SERVER_ERROR,
    AppError,
    resp_fail,
)
from app.database import close_db, init_db, ping_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"起一座生死铺：ENV_MODE={settings.ENV_MODE} DB={settings.DATABASE_URL.split('://')[0]}")
    await init_db()
    ok = await ping_db()
    logger.info(f"忘川河畔数据库连通：{ok}")
    cache = get_cache()
    logger.info(f"缓存通道：{cache.name}")

    from app.database import SessionLocal
    from app.seed import seed_once

    async with SessionLocal() as session:
        created = await seed_once(session)
        if created:
            logger.info("检测到空库，已自动灌入基础数据（角色/权限/菜单/城隍网点/基础账号，含超管 admin / 123123）")

    yield

    await shutdown_cache()
    await close_db()
    logger.info("生死铺闭门，诸魂退散")


app = FastAPI(
    title="地府生死铺后台管理系统",
    description=(
        "幽冥地府主题的亡魂全生命周期管理后台：勾魂工单 → 城隍备案签路引 → 鬼门关验引 → "
        "迷魂殿录供 → 孽镜台评分 → 十殿审判 → 刑期执行 → 孟婆汤 → 六道轮回 → 归档。\n\n"
        "角色映射：酆都大帝=超管、地藏王=审计只读、五方鬼帝=大区管理员、十殿阎罗=审批角色、"
        "崔珏=生死簿管理员、黑白无常/牛头马面=外勤执行员、城隍=分支网点、孟婆=轮回办理员。"
    ),
    version="1.0.0-p1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    cost = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{cost:.2f}ms"
    if request.url.path.startswith("/api"):
        logger.debug(f"{request.method} {request.url.path} -> {response.status_code} ({cost:.1f}ms)")
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content=resp_fail(exc.msg, exc.code, exc.data),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []) if x not in ("body", "query", "path"))
        errors.append(f"{loc}: {err.get('msg')}")
    return JSONResponse(
        status_code=400,
        content=resp_fail("参数校验失败：" + "；".join(errors), CODE_BAD_REQUEST, {"errors": errors}),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception(f"未捕获异常 {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content=resp_fail(f"阴司内务故障：{exc}", CODE_SERVER_ERROR),
    )


@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    return {
        "code": 0,
        "msg": "生死铺营业中",
        "data": {
            "env_mode": settings.ENV_MODE,
            "db": "ok" if await ping_db() else "down",
            "cache": get_cache().name,
            "version": app.version,
        },
    }


app.include_router(api_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
