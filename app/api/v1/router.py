"""v1 路由汇总。"""

from fastapi import APIRouter

from app.api.v1 import (
    audit_logs,
    auth,
    city_gods,
    documents,
    karma_records,
    life_books,
    mobile,
    officers,
    punishments,
    rbac,
    reincarnations,
    souls,
    stats,
    summon_orders,
    trials,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(souls.router)
api_router.include_router(life_books.router)
api_router.include_router(summon_orders.router)
api_router.include_router(trials.router)
api_router.include_router(punishments.router)
api_router.include_router(reincarnations.router)
api_router.include_router(karma_records.router)
api_router.include_router(officers.router)
api_router.include_router(rbac.roles_router)
api_router.include_router(rbac.perms_router)
api_router.include_router(rbac.menus_router)
api_router.include_router(city_gods.router)
api_router.include_router(documents.router)
api_router.include_router(audit_logs.router)
api_router.include_router(stats.router)
api_router.include_router(mobile.router)

__all__ = ["api_router"]
