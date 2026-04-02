from fastapi import APIRouter

from . import (
    create_profile,
    delete_profile_by_id,
    get_profile_by_id,
    patch_profile_by_id
)

router = APIRouter(prefix="/application-profiles/v0.5")
router.include_router(create_profile.router)
router.include_router(delete_profile_by_id.router)
router.include_router(get_profile_by_id.router)
router.include_router(patch_profile_by_id.router)
