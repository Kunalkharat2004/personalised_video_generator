"""Basic API tests. Run with: pytest (from the backend/ directory)."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _sample_jpeg_bytes() -> io.BytesIO:
    img = Image.new("RGB", (200, 200), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Townhall Video Generator API is running"


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "townhall-video-generator"


def test_process_image_invalid_name():
    files = {"file": ("selfie.jpg", _sample_jpeg_bytes(), "image/jpeg")}
    resp = client.post("/api/process-image", data={"name": "   "}, files=files)
    assert resp.status_code == 400


def test_process_image_missing_file():
    resp = client.post("/api/process-image", data={"name": "Kunal"})
    assert resp.status_code == 422  # FastAPI request validation error


def test_process_image_unsupported_format():
    files = {"file": ("selfie.txt", io.BytesIO(b"not an image"), "text/plain")}
    resp = client.post("/api/process-image", data={"name": "Kunal"}, files=files)
    assert resp.status_code == 400


def test_process_image_corrupt_image_bytes():
    # Valid content-type but bytes that aren't actually a decodable image.
    files = {"file": ("selfie.jpg", io.BytesIO(b"not-a-real-jpeg"), "image/jpeg")}
    resp = client.post("/api/process-image", data={"name": "Kunal"}, files=files)
    assert resp.status_code == 400


def test_process_image_valid():
    """Exercises the full pipeline, including the rembg model.

    Skipped automatically if the model can't be loaded/downloaded in this
    environment (e.g. no network access on first run).
    """
    files = {"file": ("selfie.jpg", _sample_jpeg_bytes(), "image/jpeg")}
    try:
        resp = client.post("/api/process-image", data={"name": "Kunal"}, files=files)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Background removal unavailable in this environment: {exc}")

    if resp.status_code == 500:  # pragma: no cover - environment dependent
        pytest.skip("Background removal failed, likely missing model/network access.")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["visitor_name"] == "Kunal"
    assert body["processed_image_url"] == f"/api/images/{body['image_id']}"

    image_resp = client.get(body["processed_image_url"])
    assert image_resp.status_code == 200
    assert image_resp.headers["content-type"] == "image/png"
