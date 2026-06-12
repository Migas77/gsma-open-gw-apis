from typing import Annotated

from fastapi import APIRouter, Body
from app.drivers.application_profiles import ApplicationProfilesInterfaceDep
from app.schemas.application_profiles import (
    ApplicationProfileRequest,
    ApplicationProfile,
)

router = APIRouter()


@router.post("/application-profiles")
async def create_application_profile(
    application_profile_req: Annotated[ApplicationProfileRequest, Body()],
    app_profiles_interface: ApplicationProfilesInterfaceDep,
) -> ApplicationProfile:
    return await app_profiles_interface.create_profile(application_profile_req)
