from fastapi import APIRouter

from app.settings import ConnectivityInsightsSubscriptionsBackend, settings


router = APIRouter(prefix="/callbacks/v1")
match settings.geofencing.backend:
    case ConnectivityInsightsSubscriptionsBackend.NEF:
        from .nef import router as nef_router

        router.include_router(nef_router)
