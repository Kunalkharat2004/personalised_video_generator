"""Personalized video generation and retrieval endpoints."""
import logging
import re
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import config, video_config
from app.services.video_generator import VideoGenerationError, render_personalized_video
from app.services.video_info import VideoInfoError
from app.utils.file_utils import ensure_dir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["video"])

# image/video ids are always uuid4 hex strings — reject anything else before touching the filesystem
ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

GENERIC_VIDEO_ERROR = "Something went wrong while creating your video. Please try again."


class GenerateVideoRequest(BaseModel):
    visitor_name: str = Field(..., min_length=1, max_length=80)
    image_id: str


@router.post("/generate-video")
async def generate_video(payload: GenerateVideoRequest):
    # Collapse internal whitespace, trim, then always capitalize for display.
    visitor_name = " ".join(payload.visitor_name.split())
    if not visitor_name:
        raise HTTPException(status_code=400, detail="Visitor name is required and cannot be blank.")
    display_name = visitor_name.title()

    if not ID_PATTERN.fullmatch(payload.image_id):
        raise HTTPException(status_code=400, detail="Invalid image_id.")

    processed_path = config.TEMP_DIR / f"visitor_{payload.image_id}_processed.png"
    if not processed_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed image not found. Please retake your selfie and try again.",
        )

    if not video_config.VIDEO_TEMPLATE_PATH.exists():
        logger.error("Video template missing at %s", video_config.VIDEO_TEMPLATE_PATH)
        raise HTTPException(status_code=500, detail=GENERIC_VIDEO_ERROR)

    video_id = uuid.uuid4().hex
    ensure_dir(video_config.OUTPUT_DIRECTORY)
    output_path = video_config.OUTPUT_DIRECTORY / f"video_{video_id}.mp4"

    try:
        render_personalized_video(
            template_path=video_config.VIDEO_TEMPLATE_PATH,
            photo_path=processed_path,
            visitor_display_name=display_name,
            output_path=output_path,
            video_id=video_id,
        )
    except (VideoGenerationError, VideoInfoError):
        logger.exception("Video generation failed for video_id=%s", video_id)
        raise HTTPException(status_code=500, detail=GENERIC_VIDEO_ERROR)

    return {
        "success": True,
        "video_id": video_id,
        "visitor_name": display_name,
        "video_url": f"/api/videos/{video_id}",
    }


@router.get("/videos/{video_id}")
async def get_video(video_id: str):
    if not ID_PATTERN.fullmatch(video_id):
        raise HTTPException(status_code=404, detail="Video not found.")

    path = video_config.OUTPUT_DIRECTORY / f"video_{video_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found.")

    return FileResponse(path, media_type="video/mp4")
