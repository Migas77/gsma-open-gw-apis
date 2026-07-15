import logging
import uuid
import asyncio
from datetime import datetime, timezone

import httpx
from fastapi.encoders import jsonable_encoder

from app.schemas.common import XCorrelator
from app.schemas.subscriptions import CloudEvent, Subscription

LOG = logging.getLogger(__name__)


class SubscriptionDriverBase[NotificationEventType: str, CloudEventData]:
    def __init__(self, source: str) -> None:
        super().__init__()

        self.httpx_client_callback = httpx.AsyncClient()

        self.source = source

    def send_cloud_event(
        self, sink: str, event: CloudEvent[NotificationEventType, CloudEventData], x_correlator: XCorrelator | None = None
    ) -> None:
        headers = {"x-correlator": x_correlator} if x_correlator is not None else {}
        asyncio.create_task(self._safe_post_request(sink, event, headers))

    async def notify_sink[SubscriptionEventType: str, SubscriptionDetail](
        self,
        subscription: Subscription[SubscriptionEventType, SubscriptionDetail],
        type: NotificationEventType,
        data: CloudEventData,
        x_correlator: XCorrelator | None = None,
    ) -> None:
        res: CloudEvent[NotificationEventType, CloudEventData] = CloudEvent(
            id=str(uuid.uuid4()),
            source=self.source,
            type=type,
            time=datetime.now(
                timezone.utc
                if subscription.config.subscriptionExpireTime is None
                else subscription.config.subscriptionExpireTime.tzinfo
            ),
            data=data,
        )

        self.send_cloud_event(str(subscription.sink), res, x_correlator)

    async def _safe_post_request(
        self,
        sink: str,
        event: CloudEvent[NotificationEventType, CloudEventData],
        headers: dict[str, str]
    ) -> None:
        try:
            response = await self.httpx_client_callback.post(
                sink,
                json=jsonable_encoder(event, exclude_unset=True),
                headers=headers,
            )
            if response.is_error:
                LOG.error("Error sending cloud event to %s: HTTP %s %s", response.url, response.status_code, response.content)
        except httpx.TimeoutException:
            LOG.error("Timeout while sending notification to sink %s", sink)
        except httpx.RequestError as e:
            LOG.error("Request error sending cloud event to %s: %s", sink, e)
        except Exception as e:
            LOG.exception("Unexpected error sending cloud event to %s", sink)
