import logging

from app.capif import CAPIF_SDK_CONFIG_PATH
from pathlib import Path
import uvicorn.supervisors.watchfilesreload as wfr

_OrigFileFilter = wfr.FileFilter

IGNORE_FILES = {CAPIF_SDK_CONFIG_PATH}
IGNORE_EXTENSIONS = {".log"}
IGNORE_DIRS = {
    "logs", ".idea", # os.path.join(settings.capif_sdk.invoker_folder, settings.capif_sdk.capif_username)
}

class MyFileFilter(_OrigFileFilter):
    def __call__(self, path: Path) -> bool:
        if path.name in IGNORE_FILES:
            return False
        if path.suffix in IGNORE_EXTENSIONS:
            return False
        if any(part in IGNORE_DIRS for part in path.parts):
            return False
        return super().__call__(path)


wfr.FileFilter = MyFileFilter                               # type: ignore[misc]

logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
