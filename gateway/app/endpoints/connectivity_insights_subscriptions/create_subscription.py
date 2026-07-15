from typing import Annotated

from fastapi import APIRouter, Request, Body

from app.drivers.application_profiles import ApplicationProfilesInterfaceDep
from app.drivers.connectivity_insights_subscriptions import ConnectivityInsightsSubscriptionsInterfaceDep
from app.exceptions import BadRequest
from app.schemas.connectivity_insights_subscriptions import SubscriptionRequest, CISSubscription

router = APIRouter()


@router.post("/subscriptions", response_model_exclude_unset=True, response_model_by_alias=True)
async def create_subscription(
    request: Request,
    subscription_req: Annotated[SubscriptionRequest, Body()],
    app_profiles_interface: ApplicationProfilesInterfaceDep,
    connectivity_insights_subscriptions_interface: ConnectivityInsightsSubscriptionsInterfaceDep,
) -> CISSubscription:
    if subscription_req.protocol != "HTTP":
        raise BadRequest("Only HTTP protocol is allowed for now")

    subscription_detail = subscription_req.config.subscriptionDetail
    device = subscription_detail.device
    print(device)
    if device.phoneNumber is None and device.networkAccessIdentifier is None:
        raise BadRequest("Device must be identified by phoneNumber or networkAccessIdentifier")

    app_server = subscription_detail.applicationServer
    if not app_server or app_server.ipv4Address is None:
        raise BadRequest("applicationServer must include an ipv4Address")

    application_profile_id = subscription_detail.applicationProfileId
    application_profile = await app_profiles_interface.get_profile_by_id(application_profile_id)

    subscription = await connectivity_insights_subscriptions_interface.create_subscription(
        subscription_req, application_profile,
        x_correlator=request.state.x_correlator
    )
    return subscription

