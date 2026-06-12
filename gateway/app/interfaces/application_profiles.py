from abc import ABC, abstractmethod
from app.schemas.application_profiles import (
    ApplicationProfileRequest,
    ApplicationProfile, ApplicationProfileId,
)


class AppProfilesInterface(ABC):

    @abstractmethod
    async def create_profile(self, application_profile_req: ApplicationProfileRequest) -> ApplicationProfile:
        pass

    @abstractmethod
    async def delete_profile_by_id(self, application_profile_id: ApplicationProfileId) -> None:
        pass

    @abstractmethod
    async def get_profile_by_id(self, application_profile_id: ApplicationProfileId) -> ApplicationProfile:
        pass

    @abstractmethod
    async def update_profile(self, application_profile: ApplicationProfile) -> ApplicationProfile:
        pass
