"""Basic tests for the video generation endpoints. Run with: pytest"""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.video_info import VideoInfoError, get_video_info
from app.video_config import VIDEO_TEMPLATE_PATH

client = TestClient(app)


def _sample_jpeg_bytes() -> io.BytesIO:
    img = Image.new("RGB", (200, 200), color=(80, 140, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _process_sample_selfie() -> str:
    """Runs the real Step 2 pipeline so we have a valid image_id to generate from."""
    files = {"file": ("selfie.jpg", _sample_jpeg_bytes(), "image/jpeg")}
    resp = client.post("/api/process-image", data={"name": "Kunal"}, files=files)
    if resp.status_code != 200:
        pytest.skip(f"Could not create a processed image in this environment: {resp.text}")
    return resp.json()["image_id"]


def test_generate_video_blank_name():
    resp = client.post(
        "/api/generate-video",
        json={"visitor_name": "   ", "image_id": "f" * 32},
    )
    assert resp.status_code == 400


def test_generate_video_invalid_image_id_format():
    resp = client.post(
        "/api/generate-video",
        json={"visitor_name": "Kunal", "image_id": "not-a-valid-id"},
    )
    assert resp.status_code == 400


def test_generate_video_missing_image():
    resp = client.post(
        "/api/generate-video",
        json={"visitor_name": "Kunal", "image_id": "f" * 32},
    )
    assert resp.status_code == 404


def test_get_video_not_found():
    resp = client.get(f"/api/videos/{'a' * 32}")
    assert resp.status_code == 404


def test_get_video_rejects_path_traversal():
    resp = client.get("/api/videos/..%2f..%2f..%2fetc%2fpasswd")
    assert resp.status_code in (404, 400)


def test_generate_video_end_to_end():
    """Exercises the real ffmpeg pipeline; skipped if ffmpeg/ffprobe aren't available."""
    if not VIDEO_TEMPLATE_PATH.exists():
        pytest.skip("Test video template not found.")
    try:
        get_video_info(VIDEO_TEMPLATE_PATH)
    except VideoInfoError as exc:
        pytest.skip(f"ffprobe unavailable in this environment: {exc}")

    image_id = _process_sample_selfie()
    resp = client.post(
        "/api/generate-video",
        json={"visitor_name": "kunal kharat", "image_id": image_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["visitor_name"] == "Kunal Kharat"  # always capitalized
    assert body["video_url"] == f"/api/videos/{body['video_id']}"

    video_resp = client.get(body["video_url"])
    assert video_resp.status_code == 200
    assert video_resp.headers["content-type"] == "video/mp4"
    assert len(video_resp.content) > 0
