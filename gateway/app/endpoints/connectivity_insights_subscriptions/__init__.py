from fastapi import APIRouter

from . import (
    create_subscription,
    delete_subscription_by_id,
    get_subscription_by_id,
    get_subscriptions,
)

router = APIRouter(prefix="/connectivity-insights-subscriptions/v0.6")
router.include_router(create_subscription.router)
router.include_router(delete_subscription_by_id.router)
router.include_router(get_subscription_by_id.router)
router.include_router(get_subscriptions.router)
