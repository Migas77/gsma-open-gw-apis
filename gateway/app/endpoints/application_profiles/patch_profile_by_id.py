from typing import Annotated
from fastapi import APIRouter, Body
from app.drivers.application_profiles import ApplicationProfilesInterfaceDep
from app.exceptions import BadRequest
from app.schemas.application_profiles import ApplicationProfile, ApplicationProfileId

router = APIRouter()


@router.patch("/application-profiles/{applicationProfileId}")
async def patch_application_profile_by_id(
    applicationProfileId: ApplicationProfileId,
    application_profile: Annotated[ApplicationProfile, Body()],
    app_profiles_interface: ApplicationProfilesInterfaceDep,
) -> ApplicationProfile:
    if applicationProfileId != application_profile.applicationProfileId:
        raise BadRequest(
            "Client specified incompatible applicationProfileIds in path and body"
        )

    return await app_profiles_interface.update_profile(application_profile)
