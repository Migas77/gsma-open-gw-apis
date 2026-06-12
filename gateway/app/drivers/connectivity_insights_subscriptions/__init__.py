from typing import Annotated

from fastapi import Depends

from app.interfaces.connectivity_insights_subscriptions import ConnectivityInsightsSubscriptionsInterface
from app.settings import ConnectivityInsightsSubscriptionsBackend, settings

connectivity_insights_subscriptions_interface: ConnectivityInsightsSubscriptionsInterface
match settings.connectivity_insights_subscriptions.backend:

    case ConnectivityInsightsSubscriptionsBackend.NEF:
        from .nef import nef_connectivity_insights_subscriptions_interface

        connectivity_insights_subscriptions_interface = nef_connectivity_insights_subscriptions_interface


def get_connectivity_insights_subscriptions_interface() -> ConnectivityInsightsSubscriptionsInterface:
    return connectivity_insights_subscriptions_interface


ConnectivityInsightsSubscriptionsInterfaceDep = Annotated[
    ConnectivityInsightsSubscriptionsInterface, Depends(get_connectivity_insights_subscriptions_interface)
]

