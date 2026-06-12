import uuid
from typing import override
from uuid import UUID
from app.exceptions import ResourceNotFound, InternalServerError
from app.interfaces.application_profiles import AppProfilesInterface
from app.redis import get_redis
from app.schemas.application_profiles import (
    ApplicationProfile,
    ApplicationProfileRequest, ApplicationProfileId,
)

_prefix = "application_profiles"


class RedisAppProfilesInterface(AppProfilesInterface):

    def __init__(self) -> None:
        self.redis = get_redis()

    @override
    async def create_profile(self, application_profile_req: ApplicationProfileRequest) -> ApplicationProfile:
        application_profile_id = str(uuid.uuid4())
        key = f"{_prefix}:{application_profile_id}"
        application_profile = ApplicationProfile(
            applicationProfileId=application_profile_id,
            networkQualityThresholds=application_profile_req.networkQualityThresholds,
            computeResources=application_profile_req.computeResources,
        )
        res = await self.redis.set(key, application_profile.model_dump_json(exclude_unset=True))
        if not res:
            raise InternalServerError("Failed to create application profile")
        return application_profile

    @override
    async def delete_profile_by_id(self, application_profile_id: ApplicationProfileId) -> None:
        key = f"{_prefix}:{application_profile_id}"
        res = await self.redis.delete(key)
        if res == 0:
            raise ResourceNotFound()
        return None

    @override
    async def get_profile_by_id(self, application_profile_id: ApplicationProfileId) -> ApplicationProfile:
        key = f"{_prefix}:{application_profile_id}"
        data = await self.redis.get(key)
        if data is None:
            raise ResourceNotFound("Application profile not found")
        return ApplicationProfile.model_validate_json(data)

    @override
    async def update_profile(self, application_profile: ApplicationProfile) -> ApplicationProfile:
        application_profile_id = application_profile.applicationProfileId
        key = f"{_prefix}:{application_profile_id}"
        data = await self.redis.get(key)
        if data is None:
            raise ResourceNotFound()

        res = await self.redis.set(key, application_profile.model_dump_json(exclude_unset=True))
        if not res:
            raise InternalServerError("Failed to update application profile")

        return application_profile
