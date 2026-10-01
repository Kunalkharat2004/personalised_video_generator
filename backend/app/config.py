"""Centralized configuration loaded from environment variables (.env)."""
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# numba (a pymatting/rembg dependency) JIT-caches compiled code to disk next
# to its source files by default. That breaks when the project lives inside
# a cloud-synced folder (e.g. OneDrive), whose placeholder/locking behavior
# can make the cache write fail. Redirect it to a plain local temp dir before
# rembg (and therefore numba) gets imported anywhere.
os.environ.setdefault(
    "NUMBA_CACHE_DIR", str(Path(tempfile.gettempdir()) / "townhall_numba_cache")
)


def _ensure_ffmpeg_on_path() -> None:
    """Dev convenience: a winget install only updates the persistent PATH
    registry value, which shells/processes already running at install time
    never pick up without a restart. If ffmpeg/ffprobe aren't resolvable,
    search the common winget install location and prepend it for this
    process only, so the app doesn't depend on the launching shell's PATH.
    """
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    winget_packages = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if not winget_packages.exists():
        return
    for candidate in winget_packages.glob("Gyan.FFmpeg_*/ffmpeg-*/bin"):
        if (candidate / "ffmpeg.exe").exists():
            os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
            return


_ensure_ffmpeg_on_path()

# app/config.py -> app/ -> backend/ -> project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = BASE_DIR / "temp"
GENERATED_DIR = BASE_DIR / "generated"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

_default_dev_origins = {"http://localhost:5173", "http://127.0.0.1:5173"}
_extra_origins = {
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
}
CORS_ALLOW_ALL = "*" in _extra_origins
ALLOWED_ORIGINS = ["*"] if CORS_ALLOW_ALL else sorted(
    {FRONTEND_URL, *_default_dev_origins, *_extra_origins}
)
