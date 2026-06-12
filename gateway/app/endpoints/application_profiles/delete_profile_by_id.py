from http import HTTPStatus
from fastapi import APIRouter
from app.drivers.application_profiles import ApplicationProfilesInterfaceDep
from app.schemas.application_profiles import ApplicationProfileId

router = APIRouter()


@router.delete(
    "/application-profiles/{applicationProfileId}", status_code=HTTPStatus.NO_CONTENT
)
async def delete_application_profile_by_id(
    applicationProfileId: ApplicationProfileId,
    app_profiles_interface: ApplicationProfilesInterfaceDep
) -> None:
    await app_profiles_interface.delete_profile_by_id(applicationProfileId)
