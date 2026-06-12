import asyncio
import logging
from http import HTTPStatus
from typing import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.drivers.connectivity_insights_subscriptions.nef import nef_connectivity_insights_subscriptions_interface
from app.drivers.application_profiles import get_app_profiles_interface
from app.exceptions import ResourceNotFound
from app.schemas.application_profiles import NetworkQualityThresholds, Rate
from app.schemas.connectivity_insights_subscriptions import (
    EventTypeNotification,
    NetworkQualityInsight,
    NetworkQualityThresholdsConfidence,
)
from app.schemas.subscriptions import TerminationReason
from app.schemas.nef_schemas.analytics_exposure import AnalyticsEventNotification, AnalyticsEvent, TrafficInformation, \
    BitRate

from app.utils.camara_nef_converters import align_rates


LOG = logging.getLogger(__name__)


_REQUIREMENTS_MET = NetworkQualityThresholdsConfidence.meets_the_application_requirements
_REQUIREMENTS_UNMET = NetworkQualityThresholdsConfidence.unable_to_meet_the_application_requirements


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(nef_connectivity_insights_subscriptions_interface.clear_loop())

    yield

    task.cancel()


router = APIRouter(lifespan=lifespan)


@router.post("/connectivity-insights-subscriptions/{sub_id}", status_code=HTTPStatus.NO_CONTENT)
async def webhook(sub_id: str, notification: AnalyticsEventNotification) -> None:
    LOG.debug(notification)

    notif_id = notification.notifId

    if notification.termCause is not None:
        try:
            await nef_connectivity_insights_subscriptions_interface.delete_subscription(
                sub_id, termination_reason=TerminationReason.NETWORK_TERMINATED
            )
        except ResourceNotFound:
            LOG.warning("sub=%s, notifId=%s: Received termination notification for non-existing subscription", sub_id, notif_id)
            pass
        return

    try:
        subscription = await nef_connectivity_insights_subscriptions_interface.get_subscription(sub_id)
    except ResourceNotFound:
        LOG.warning("sub=%s, notifId=%s: Received notification for non-existing subscription", sub_id, notif_id)
        return

    subscription_detail = subscription.config.subscriptionDetail
    app_profile_id = subscription_detail.applicationProfileId
    try:
        profile = await get_app_profiles_interface().get_profile_by_id(app_profile_id)
    except ResourceNotFound:
        LOG.warning("sub=%s, notifId=%s: Application profile %s not found", sub_id, notif_id, app_profile_id)
        return

    try:
        device_gpsi = nef_connectivity_insights_subscriptions_interface.get_device_gpsi(subscription_detail.device)
    except ResourceNotFound:
        LOG.warning("sub=%s, notifId=%s: Device identifier not found", sub_id, notif_id)
        return

    thresholds = profile.networkQualityThresholds
    if thresholds is None or not thresholds.model_dump(exclude_none=True):
        LOG.info(
            "sub=%s, notifId=%s: Empty/None thresholds for application profile %s",
            sub_id, notif_id, app_profile_id
        )
        return

    insight = NetworkQualityInsight(
        papplicationProfileId=subscription.config.subscriptionDetail.applicationProfileId,
        # Defaults to _REQUIREMENTS_MET (only implemented targetMinDownstreamRate and targetMinUpstreamRate)
        targetMinDownstreamRate=_REQUIREMENTS_MET,
        targetMinUpstreamRate=_REQUIREMENTS_MET,
    )
    notif = notification.analyEventNotifs[0]                    # should only return one notification at a time
    if notif.analyEvent != AnalyticsEvent.WLAN_PERFORMANCE:
        # should never happen (subscription is for WLAN_PERFORMANCE only)
        LOG.warning(
            "sub=%s, notifId=%s: Received notification for unsupported event (not WLAN_PERFORMANCE) %s",
            sub_id, notif_id, notif.analyEvent
        )
        return
    if not notif.wlanInfos:
        # should never happen (NEF returning empty wlanInfos)
        LOG.warning(
            "sub=%s, notifId=%s: wlanInfos empty/none for WLAN_PERFORMANCE notification %s",
            sub_id, notif_id, notif.analyEvent
        )
        return

    # given subscription will, at max, return one wlanInfo (as config enforces temporalGranSize >= offsetPeriod)
    number_wlan_infos = len(notif.wlanInfos)
    if number_wlan_infos != 1:
        # should never happen
        LOG.warning(
            "sub=%s, notifId=%s: Received %d wlanInfos for notification %s, expected 1. Processing first one.",
            sub_id, notif_id, number_wlan_infos, notif.analyEvent
        )

    wlan_info = notif.wlanInfos[0]
    ue_info = next(
        (ue.root for ue in wlan_info.wlanPerUeIdInfos if ue.root.gpsi and ue.root.gpsi == device_gpsi),
        None,
    ) if wlan_info.wlanPerUeIdInfos else None

    if not ue_info:
        # should never happen (missing UE info - no traffic UEs will return zeroed metric values)
        LOG.warning(
            "sub=%s, notifId=%s: No matching UE info found for GPSI %s in notification %s, skipping",
            sub_id, notif_id, device_gpsi, notif.analyEvent
        )
        return

    for ts_info in ue_info.wlanPerTsInfos:
        wlan_ts_info = ts_info.root
        traffic = wlan_ts_info.trafficInfo if wlan_ts_info.trafficInfo is not None else None
        if not traffic:
            LOG.warning(
                "sub=%s, notifId=%s: Unexpected missing traffic information in notification %s, skipping",
                sub_id, notif_id, notif.analyEvent
            )
            continue

        was_updated = _update_insight(thresholds, insight, traffic)

        if was_updated and _all_requirements_unmet(insight):
            break

    await nef_connectivity_insights_subscriptions_interface.send_report(
        subscription,
        EventTypeNotification.org_camaraproject_connectivity_insights_subscriptions_v0_network_quality,
        insight,
        x_correlator=notif_id,
    )


def _all_requirements_unmet(insight: NetworkQualityInsight) -> bool:
    """
    Check if all requirements are unmet, meaning that the application requirements are not satisfied.
    Currently only targetMinDownstreamRate and targetMinUpstreamRate are checked and enforced.
    """
    checks = [
        insight.targetMinDownstreamRate,
        insight.targetMinUpstreamRate,
    ]
    return all(v == _REQUIREMENTS_UNMET for v in checks)


def _update_insight(thresholds: NetworkQualityThresholds, insight: NetworkQualityInsight, traffic: TrafficInformation) -> bool:
    """
    Updates the insight with the latest traffic measurements against thresholds. Once unmet, it stays unmet.
    Currently only targetMinDownstreamRate and targetMinUpstreamRate are checked and enforced.
    """
    updated = False
    target_min_downstream_rate = thresholds.targetMinDownstreamRate
    target_min_upstream_rate = thresholds.targetMinUpstreamRate

    if target_min_downstream_rate is not None:
        nef_downlink_rate = traffic.root.downlinkRate
        if nef_downlink_rate is not None:
            previous_threshold_confidence = insight.targetMinDownstreamRate
            if previous_threshold_confidence == _REQUIREMENTS_MET:
                new_threshold_confidence = _check_min_rate(target_min_downstream_rate, nef_downlink_rate)
                insight.targetMinDownstreamRate = _worst_confidence(previous_threshold_confidence, new_threshold_confidence)
                updated |= (previous_threshold_confidence != insight.targetMinDownstreamRate)
        else:
            LOG.warning("Missing downlinkRate in traffic information, skipping targetMinDownstreamRate check")

    if target_min_upstream_rate is not None:
        nef_uplink_rate = traffic.root.uplinkRate
        if nef_uplink_rate is not None:
            previous_threshold_confidence = insight.targetMinUpstreamRate
            if previous_threshold_confidence == _REQUIREMENTS_MET:
                new_threshold_confidence = _check_min_rate(target_min_upstream_rate, nef_uplink_rate)
                insight.targetMinUpstreamRate = _worst_confidence(previous_threshold_confidence, new_threshold_confidence)
                updated |= (previous_threshold_confidence != insight.targetMinUpstreamRate)
        else:
            LOG.warning("Missing uplinkRate in traffic information, skipping targetMinUpstreamRate check")

    return updated


def _check_min_rate(threshold: Rate, bitrate: BitRate) -> NetworkQualityThresholdsConfidence:
    # Rate (CAMARA Model), BitRate (NEF AnalyticsExposure Model)
    camara_threshold_value, nef_bitrate_value = align_rates(threshold, bitrate)
    return _REQUIREMENTS_MET if nef_bitrate_value >= camara_threshold_value else _REQUIREMENTS_UNMET


def _worst_confidence(
    current: NetworkQualityThresholdsConfidence,
    new: NetworkQualityThresholdsConfidence
) -> NetworkQualityThresholdsConfidence:
    if current == _REQUIREMENTS_UNMET or new == _REQUIREMENTS_UNMET:
        return _REQUIREMENTS_UNMET
    return new

