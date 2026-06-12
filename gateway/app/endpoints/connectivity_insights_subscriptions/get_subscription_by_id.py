from fastapi import APIRouter

from app.drivers.connectivity_insights_subscriptions import ConnectivityInsightsSubscriptionsInterfaceDep
from app.schemas.connectivity_insights_subscriptions import CISSubscription

router = APIRouter()


@router.get("/subscriptions/{subscriptionId}", response_model_exclude_unset=True)
async def get_subscription_by_id(
    subscriptionId: str,
    connectivity_insights_subscriptions_interface: ConnectivityInsightsSubscriptionsInterfaceDep,
) -> CISSubscription:
    return await connectivity_insights_subscriptions_interface.get_subscription_by_id(subscriptionId)

