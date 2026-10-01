"""Filesystem helpers for temporary selfie storage."""
import uuid
from pathlib import Path

from fastapi import UploadFile

from app import config, video_config


def ensure_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


def generate_visitor_id() -> str:
    """Opaque id used in filenames/URLs — never derived from the visitor's name."""
    return uuid.uuid4().hex


async def read_upload_within_limit(upload: UploadFile, max_bytes: int) -> bytes:
    """Reads an UploadFile in chunks, aborting early once max_bytes is exceeded."""
    chunk_size = 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            return b""  # caller treats an empty result as "too large"
        chunks.append(chunk)
    return b"".join(chunks)


def delete_file_if_exists(path: Path) -> None:
    """Best-effort delete.

    NOTE: For this MVP step, processed/original files are intentionally kept
    around (the frontend needs to fetch the processed image after the API
    call returns). This helper exists so a scheduled cleanup job can be
    wired up in a later step without changing the processing pipeline.
    """
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def cleanup_visitor_artifacts(image_id: str | None = None, video_id: str | None = None) -> None:
    """Deletes all temp/generated files tied to a visitor's image_id/video_id.

    NOTE: Not called automatically anywhere yet — this MVP intentionally
    keeps every artifact around for debugging. Wire this into a scheduled
    cleanup job once automatic expiry is needed.
    """
    if image_id:
        delete_file_if_exists(config.TEMP_DIR / f"visitor_{image_id}_original.jpg")
        delete_file_if_exists(config.TEMP_DIR / f"visitor_{image_id}_processed.png")
    if video_id:
        delete_file_if_exists(config.TEMP_DIR / f"visitor_{video_id}_name.txt")
        delete_file_if_exists(video_config.OUTPUT_DIRECTORY / f"video_{video_id}.mp4")
