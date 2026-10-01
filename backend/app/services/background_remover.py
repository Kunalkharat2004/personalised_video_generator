"""Background removal via rembg (U^2-Net)."""
import logging

from PIL import Image
from rembg import new_session, remove

logger = logging.getLogger(__name__)

_session = None


def _get_session():
    """Lazily creates the rembg session (downloads the model on first use)."""
    global _session
    if _session is None:
        logger.info("Loading rembg u2net model session...")
        _session = new_session("u2net")
    return _session


def remove_background(image: Image.Image) -> Image.Image:
    """Returns an RGBA image with the background removed (transparent)."""
    result = remove(image, session=_get_session())
    return result.convert("RGBA")
