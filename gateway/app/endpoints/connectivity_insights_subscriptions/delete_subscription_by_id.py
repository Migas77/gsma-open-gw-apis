from http import HTTPStatus

from fastapi import APIRouter

from app.drivers.connectivity_insights_subscriptions import ConnectivityInsightsSubscriptionsInterfaceDep

router = APIRouter()


@router.delete("/subscriptions/{subscriptionId}", status_code=HTTPStatus.NO_CONTENT)
async def delete_subscription_by_id(
    subscriptionId: str,
    connectivity_insights_subscriptions_interface: ConnectivityInsightsSubscriptionsInterfaceDep,
) -> None:
    await connectivity_insights_subscriptions_interface.delete_subscription_by_id(subscriptionId)

