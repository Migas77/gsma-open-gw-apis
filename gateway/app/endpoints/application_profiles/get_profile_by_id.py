from fastapi import APIRouter

from app.drivers.application_profiles import ApplicationProfilesInterfaceDep
from app.schemas.application_profiles import ApplicationProfile, ApplicationProfileId

router = APIRouter()


@router.get("/application-profiles/{applicationProfileId}")
async def get_application_profile_by_id(
    applicationProfileId: ApplicationProfileId,
    app_profiles_interface: ApplicationProfilesInterfaceDep
) -> ApplicationProfile:
    return await app_profiles_interface.get_profile_by_id(applicationProfileId)
