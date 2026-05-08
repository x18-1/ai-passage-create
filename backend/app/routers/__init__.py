"""API 路由"""

from app.routers.user import router as user_router
from app.routers.health import router as health_router
from app.routers.article import router as article_router
from app.routers.article_sync import router as article_sync_router
from app.routers.hotspot import router as hotspot_router
from app.routers.hotspot_monitor import router as hotspot_monitor_router
from app.routers.payment import payment_router, webhook_router
from app.routers.statistics import router as statistics_router

__all__ = [
    "user_router",
    "health_router",
    "article_router",
    "article_sync_router",
    "hotspot_router",
    "hotspot_monitor_router",
    "payment_router",
    "webhook_router",
    "statistics_router",
]
