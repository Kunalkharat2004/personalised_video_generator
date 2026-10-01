"""ffprobe-based video metadata retrieval."""
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoInfoError(Exception):
    """Raised when ffprobe is unavailable or fails to read a video file."""


def get_video_info(video_path: Path) -> dict:
    """Returns {width, height, fps, duration, video_codec, audio_codec, has_audio}."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    except FileNotFoundError as exc:
        raise VideoInfoError("ffprobe is not installed or not available on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoInfoError("ffprobe timed out inspecting the video.") from exc

    if result.returncode != 0:
        logger.error("ffprobe failed for %s: %s", video_path, result.stderr)
        raise VideoInfoError(f"ffprobe could not read the video: {video_path.name}")

    data = json.loads(result.stdout)
    video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)

    if video_stream is None:
        raise VideoInfoError(f"No video stream found in {video_path.name}")

    duration = float(data.get("format", {}).get("duration") or video_stream.get("duration") or 0)

    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": _parse_frame_rate(video_stream.get("r_frame_rate", "0/1")),
        "duration": duration,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "has_audio": audio_stream is not None,
    }


def _parse_frame_rate(rate_str: str) -> float:
    if "/" in rate_str:
        num, den = rate_str.split("/")
        den = float(den)
        return round(float(num) / den, 3) if den else 0.0
    return float(rate_str)
