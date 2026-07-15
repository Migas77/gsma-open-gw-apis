import asyncio
import logging
from typing import override, Any, Optional

from fastapi.encoders import jsonable_encoder

from app.exceptions import InternalServerError, ResourceNotFound
from app.interfaces.connectivity_insights_subscriptions import ConnectivityInsightsSubscriptionsInterface
from app.schemas.application_profiles import ApplicationProfile
from app.schemas.connectivity_insights_subscriptions import (
    CISSubscription,
    CISSubscriptionTypeAdapter,
    EventTypeNotification,
    SubscriptionEnded,
    SubscriptionEventType,
    CreateSubscriptionDetail,
    TerminationReason as CITerminationReason,
    CloudEventData, SubscriptionTypeAdapter, SubscriptionRequest, Subscription,
)
from app.schemas.nef_schemas.analytics_exposure import AnalyticsExposureSubsc, AnalyticsEventSubsc, AnalyticsEvent, \
    AnalyticsEventFilterSubsc, AddrFqdn, IpAddr, IpAddr1, AnalyticsSubset, EventReportingRequirement, TargetUeId, \
    ReportingInformation, NotificationMethod
from app.schemas.subscriptions import TerminationReason

from app.drivers.nef_auth import discover_nef_url
from app.settings import NEFConnectivityInsightsSubscriptionsSettings
from app.utils.nef_driver_base import NefDriverBase
from app.utils.subscription_driver_redis import SubscriptionDriverRedis

LOG = logging.getLogger(__name__)


_prefix_nef_url = "connectivity_insights_subscriptions_nef_url"


class NefConnectivityInsightsSubscriptionsInterface(
    ConnectivityInsightsSubscriptionsInterface,
    NefDriverBase,
    SubscriptionDriverRedis[
        SubscriptionEventType,
        CreateSubscriptionDetail,
        EventTypeNotification,
        CloudEventData
    ]
):
    def __init__(self, cis_settings: NEFConnectivityInsightsSubscriptionsSettings, source: str) -> None:
        NefDriverBase.__init__(self, cis_settings.nef)
        SubscriptionDriverRedis.__init__(
            self, source, "connectivity_insights_subscriptions", SubscriptionTypeAdapter
        )
        self.notification_url = cis_settings.nef.get_notification_url()
        self.offset_period = cis_settings.offset_period
        self.temporal_gran_size = cis_settings.temporal_gran_size
        self.rep_period = cis_settings.rep_period

    @override
    async def create_subscription(self, req: SubscriptionRequest, app_profile: ApplicationProfile, **kwargs: Any) -> CISSubscription:

        x_correlator = kwargs.get("x_correlator")
        if x_correlator is None:
            LOG.error("Missing x-correlator")
            raise InternalServerError()

        sub = await self.create_gateway_subscription(req)
        expire_time = req.config.subscriptionExpireTime
        device = req.config.subscriptionDetail.device
        app_server = req.config.subscriptionDetail.applicationServer
        app_server_ipv4_address = app_server.ipv4Address.split("/")[0] if app_server and app_server.ipv4Address else ""
        try:

            body = AnalyticsExposureSubsc(
                analyEventsSubs=[
                    AnalyticsEventSubsc(
                        analyEvent=AnalyticsEvent.WLAN_PERFORMANCE,
                        analyEventFilter=AnalyticsEventFilterSubsc(
                            appServerAddrs=[
                                # Needed for current implementations of WLAN_PERFORMANCE event
                                # to specify target server address
                                AddrFqdn(ipAddr=IpAddr(root=IpAddr1(ipv4Addr=app_server_ipv4_address)))
                            ],
                            listOfAnaSubsets=[
                                AnalyticsSubset.TRAFFIC_INFO,
                                AnalyticsSubset.NUMBER_OF_UES,
                            ],
                            extraReportReq=EventReportingRequirement(
                                # Report of the last n seconds prior to reporting time
                                offsetPeriod=self.offset_period
                            ),
                            temporalGranSize=self.temporal_gran_size,
                        ),
                        tgtUe=TargetUeId(gpsi=self.get_device_gpsi(device))
                    ),
                ],
                analyRepInfo=ReportingInformation(
                    notifMethod=NotificationMethod.PERIODIC,
                    maxReportNbr=req.config.subscriptionMaxEvents,
                    monDur=expire_time,
                    immRep=req.config.initialEvent,
                    repPeriod=self.rep_period,
                ),
                notifUri=f"{self.notification_url}/callbacks/v1/connectivity-insights-subscriptions/{sub.id}",
                notifId=x_correlator
            )

            res = await self.httpx_client.post(
                discover_nef_url(
                    nef_settings=self.nef_settings,
                    fallback="/3gpp-analyticsexposure/v1/{afId}/subscriptions",
                    resource_name="Create Subscription",
                    api_name_filter="analyticsexposure",
                    operation="POST",
                ).format(afId=self.af_id),
                json=jsonable_encoder(body.model_dump(exclude_none=True)),
            )

            if not res.is_success:
                LOG.error("Error communicating with the core: %d - %s", res.status_code, res.text)
                if res.status_code == 404:
                    raise ResourceNotFound("Device Not Found")
                raise InternalServerError("Error communicating with the core")

            subscription_result = AnalyticsExposureSubsc.model_validate_json(res.content)
            if subscription_result.self is None:
                LOG.error("No 'self' in monitoring subscription response")
                raise InternalServerError("Error communicating with the core")

            nef_url_key = f"{_prefix_nef_url}:{sub.id}"
            await self.redis.set(nef_url_key, subscription_result.self)

            return self._to_cis_subscription(sub)

        except BaseException as e:
            await self.permanently_delete_subscription(sub)
            raise e


    @override
    async def delete_subscription_by_id(self, sub_id: str) -> None:
        await self.delete_subscription(sub_id)

    @override
    async def get_subscription_by_id(self, sub_id: str) -> CISSubscription:
        sub = await SubscriptionDriverRedis.get_subscription(self, sub_id)
        return self._to_cis_subscription(sub)

    @override
    async def get_all_subscriptions(self) -> list[CISSubscription]:
        subs = await SubscriptionDriverRedis.get_subscriptions(self)
        return [self._to_cis_subscription(s) for s in subs]

    async def delete_subscription(
        self,
        sub_id: str,
        *,
        nef_subscription_url: Optional[str] = None,
        termination_reason: TerminationReason = TerminationReason.SUBSCRIPTION_DELETED,
    ) -> None:
        subscription = await self.delete_gateway_subscription(sub_id, termination_reason)

        if subscription is None:
            return

        nef_url_key = f"{_prefix_nef_url}:{sub_id}"

        if nef_subscription_url is None:
            nef_subscription_url = await self.redis.get(nef_url_key)

        if nef_subscription_url is not None:
            asyncio.create_task(self.delete_nef_subscription(nef_subscription_url))

        await self.redis.delete(nef_url_key)

        await self.notify_sink(
            subscription,
            EventTypeNotification.org_camaraproject_connectivity_insights_subscriptions_v0_subscription_ended,
            SubscriptionEnded(
                terminationReason=CITerminationReason(termination_reason.value),
                subscriptionId=sub_id,
            ),
        )

    @staticmethod
    def _to_cis_subscription(sub: Subscription) -> CISSubscription:
        return CISSubscriptionTypeAdapter.validate_python(sub, from_attributes=True)

