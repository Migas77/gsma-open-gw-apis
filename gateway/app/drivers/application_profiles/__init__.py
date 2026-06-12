from typing import Annotated

from fastapi import Depends

from app.interfaces.application_profiles import AppProfilesInterface
from app.settings import settings, AppProfilesBackend

_app_profiles_interface: AppProfilesInterface
match settings.application_profiles.backend:
    case AppProfilesBackend.Redis:
        from .redis import RedisAppProfilesInterface

        _app_profiles_interface = RedisAppProfilesInterface()


def get_app_profiles_interface() -> AppProfilesInterface:
    return _app_profiles_interface


ApplicationProfilesInterfaceDep = Annotated[
    AppProfilesInterface, Depends(get_app_profiles_interface)
]
