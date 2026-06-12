import httpx
import logging

from pydantic import AnyUrl

from app.drivers.nef_auth import NEFAuth
from app.exceptions import ResourceNotFound
from app.schemas.nef_schemas.analytics_exposure import Gpsi
from app.settings import NEFSettings
from app.schemas.device import Device
from app.schemas.nef_schemas.monitoringevent import MonitoringEventSubscription


class NefDriverBase:
    def __init__(self, nef_settings: NEFSettings) -> None:
        nef_auth = NEFAuth(
            nef_settings.url, nef_settings.username, nef_settings.password
        )
        self.httpx_client = httpx.AsyncClient(
            base_url=nef_settings.get_base_url(), auth=nef_auth
        )

        self.af_id = nef_settings.gateway_af_id

    def install_device_identifiers(
        self, sub: MonitoringEventSubscription, device: Device
    ) -> MonitoringEventSubscription:
        if device.phoneNumber is not None:
            sub.msisdn = device.phoneNumber.lstrip("+")
        elif device.ipv4Address is not None:
            sub.ipv4Addr = device.ipv4Address.publicAddress
        elif device.ipv6Address is not None:
            sub.ipv6Addr = device.ipv6Address
        elif device.networkAccessIdentifier is not None:
            sub.externalId = device.networkAccessIdentifier

        return sub

    def get_device_gpsi(self, device: Device) -> Gpsi:
        if device.phoneNumber is not None:
            return f"msisdn-{device.phoneNumber.lstrip('+')}"
        elif device.networkAccessIdentifier is not None:
            return f"extid-{device.networkAccessIdentifier}"
        raise ResourceNotFound("Device does not have valid identifier for NEF subscription."
                               "One of the following must be provided and valid: phoneNumber, networkAccessIdentifier")

    async def delete_nef_subscription(self, sub_url: AnyUrl | str) -> None:
        res = await self.httpx_client.delete(str(sub_url))

        if res.status_code == 404:
            logging.warning("Subscription not found")
            return

        if not res.is_success:
            logging.error(
                "Failed to delete NEF subscription (code: {%d}): %s",
                res.status_code,
                res.text,
            )
