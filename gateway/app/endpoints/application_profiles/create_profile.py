from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from app.crud import crud_mongo
from app.db.session import db_mongo
from app.db.collections import APPLICATION_PROFILES
from app.schemas.application_profiles import ApplicationProfileRequest, ApplicationProfile

router = APIRouter()
db_collection = APPLICATION_PROFILES

@router.post("/application-profiles", response_model=ApplicationProfile)
async def create_application_profile(application_profile_req: ApplicationProfileRequest):
    json_data = jsonable_encoder(application_profile_req)

    inserted_doc = await crud_mongo.create(db_mongo, db_collection, json_data, generate_uuid=True)
    if not inserted_doc.acknowledged:
        raise HTTPException(status_code=500, detail="Failed to create application profile")

    app_prof = await crud_mongo.read_by_id(db_mongo, db_collection, inserted_doc.inserted_id)
    app_prof["applicationProfileId"] = inserted_doc.inserted_id
    return app_prof

