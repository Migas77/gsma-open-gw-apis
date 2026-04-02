from uuid import UUID
from fastapi import APIRouter
from app.crud import crud_mongo
from app.db.session import db_mongo
from app.db.collections import APPLICATION_PROFILES
from app.exceptions import ResourceNotFound
from app.schemas.application_profiles import ApplicationProfile

router = APIRouter()
db_collection = APPLICATION_PROFILES

@router.get("/application-profiles/{applicationProfileId}", response_model=ApplicationProfile)
async def get_application_profile_by_id(applicationProfileId: UUID):
    app_prof = await crud_mongo.read_by_id(db_mongo, db_collection, applicationProfileId)
    if app_prof is None:
        raise ResourceNotFound()

    app_prof["applicationProfileId"] = applicationProfileId
    return app_prof

