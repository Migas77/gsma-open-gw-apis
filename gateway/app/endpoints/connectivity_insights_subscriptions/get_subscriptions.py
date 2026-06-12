from fastapi import APIRouter

from app.drivers.connectivity_insights_subscriptions import ConnectivityInsightsSubscriptionsInterfaceDep
from app.schemas.connectivity_insights_subscriptions import CISSubscription

router = APIRouter()


@router.get("/subscriptions")
async def get_subscriptions(
    connectivity_insights_subscriptions_interface: ConnectivityInsightsSubscriptionsInterfaceDep,
) -> list[CISSubscription]:
    return await connectivity_insights_subscriptions_interface.get_all_subscriptions()

