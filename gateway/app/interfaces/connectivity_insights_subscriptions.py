from abc import ABC, abstractmethod
from typing import Any

from app.schemas.application_profiles import ApplicationProfile
from app.schemas.connectivity_insights_subscriptions import (
    CISSubscription,
    SubscriptionRequest,
)


class ConnectivityInsightsSubscriptionsInterface(ABC):

    @abstractmethod
    async def create_subscription(self, req: SubscriptionRequest, app_profile: ApplicationProfile, **kwargs: Any) -> CISSubscription:
        pass

    @abstractmethod
    async def delete_subscription_by_id(self, sub_id: str) -> None:
        pass

    @abstractmethod
    async def get_subscription_by_id(self, sub_id: str) -> CISSubscription:
        pass

    @abstractmethod
    async def get_all_subscriptions(self) -> list[CISSubscription]:
        pass