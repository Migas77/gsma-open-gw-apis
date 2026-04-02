from uuid import UUID
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from app.crud import crud_mongo
from app.db.session import db_mongo
from app.db.collections import APPLICATION_PROFILES
from app.exceptions import ResourceNotFound, BadRequest
from app.schemas.application_profiles import ApplicationProfile

router = APIRouter()
db_collection = APPLICATION_PROFILES

@router.patch("/application-profiles/{applicationProfileId}", response_model=ApplicationProfile)
async def patch_application_profile_by_id(
    applicationProfileId: UUID,
    application_profile: ApplicationProfile
):
    if applicationProfileId != application_profile.root.applicationProfileId:
        raise BadRequest("Client specified incompatible applicationProfileIds in path and body")
    json_data = jsonable_encoder(application_profile, exclude={'applicationProfileId'})

    updated_app_prof = await crud_mongo.replace_update_by_id(db_mongo, db_collection, applicationProfileId, json_data)
    if updated_app_prof is None:
        raise ResourceNotFound()

    updated_app_prof["applicationProfileId"] = applicationProfileId
    return updated_app_prof

