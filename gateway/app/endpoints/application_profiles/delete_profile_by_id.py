from uuid import UUID
from http import HTTPStatus
from fastapi import APIRouter
from app.crud import crud_mongo
from app.db.session import db_mongo
from app.db.collections import APPLICATION_PROFILES
from app.exceptions import ResourceNotFound


router = APIRouter()
db_collection = APPLICATION_PROFILES

@router.delete("/application-profiles/{applicationProfileId}", status_code=HTTPStatus.NO_CONTENT)
async def delete_application_profile_by_id(applicationProfileId: UUID):
    delete_result = await crud_mongo.delete_by_id(db_mongo, db_collection, applicationProfileId)
    if delete_result.deleted_count == 0:
        raise ResourceNotFound()
    return

