"""Selfie upload, processing, and retrieval endpoints."""
import io
import logging
import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app import config
from app.services.image_processor import process_selfie
from app.utils.file_utils import (
    ensure_dir,
    generate_visitor_id,
    read_upload_within_limit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["image"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_PILLOW_FORMATS = {"JPEG", "PNG", "WEBP"}
# image ids are always uuid4 hex strings — reject anything else before touching the filesystem
IMAGE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

GENERIC_PROCESSING_ERROR = (
    "Something went wrong while processing your selfie. Please try again."
)


@router.post("/process-image")
async def process_image(name: str = Form(...), file: UploadFile = File(...)):
    visitor_name = name.strip()
    if not visitor_name:
        raise HTTPException(
            status_code=400, detail="Visitor name is required and cannot be blank."
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Please upload a JPEG, PNG, or WEBP image.",
        )

    raw_bytes = await read_upload_within_limit(file, config.MAX_UPLOAD_SIZE_BYTES)
    if not raw_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Image exceeds the maximum allowed size of {config.MAX_UPLOAD_SIZE_MB}MB.",
        )

    try:
        probe = Image.open(io.BytesIO(raw_bytes))
        probe.verify()
        if probe.format not in ALLOWED_PILLOW_FORMATS:
            raise ValueError(f"Unexpected format: {probe.format}")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=400, detail="The uploaded file is not a valid image."
        )

    # verify() invalidates the Image object, so re-open it for actual use.
    image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")

    image_id = generate_visitor_id()
    ensure_dir(config.TEMP_DIR)
    original_path = config.TEMP_DIR / f"visitor_{image_id}_original.jpg"
    image.save(original_path, format="JPEG")

    try:
        processed = process_selfie(image)
    except Exception:
        logger.exception("Background removal/processing failed for image_id=%s", image_id)
        raise HTTPException(status_code=500, detail=GENERIC_PROCESSING_ERROR)

    processed_path = config.TEMP_DIR / f"visitor_{image_id}_processed.png"
    processed.save(processed_path, format="PNG")

    return {
        "success": True,
        "visitor_name": visitor_name,
        "image_id": image_id,
        "processed_image_url": f"/api/images/{image_id}",
    }


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    if not IMAGE_ID_PATTERN.fullmatch(image_id):
        raise HTTPException(status_code=404, detail="Image not found.")

    path = config.TEMP_DIR / f"visitor_{image_id}_processed.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found.")

    return FileResponse(path, media_type="image/png")
