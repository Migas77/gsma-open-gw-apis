from app.drivers.connectivity_insights_subscriptions.nef.nef import NefConnectivityInsightsSubscriptionsInterface
from app.settings import settings, ConnectivityInsightsSubscriptionsBackend

if settings.connectivity_insights_subscriptions.backend != ConnectivityInsightsSubscriptionsBackend.NEF:
    raise RuntimeError(
        "Connectivity Insights Subscriptions NEF driver instantiated but backend isn't nef"
    )

nef_connectivity_insights_subscriptions_interface = NefConnectivityInsightsSubscriptionsInterface(
    settings.connectivity_insights_subscriptions, str(settings.gateway_public_url)
)

