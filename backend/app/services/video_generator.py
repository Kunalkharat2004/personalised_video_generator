"""FFmpeg-based personalized video rendering.

Builds a filter_complex that overlays the visitor's transparent cutout PNG
and their name onto the template video in a single ffmpeg invocation. The
visitor name is never interpolated into the ffmpeg command string — it's
written to a plain text file and referenced via drawtext's ``textfile=``,
which is the safe mechanism recommended for arbitrary user text.
"""
import logging
import subprocess
from pathlib import Path

from PIL import ImageFont

from app import config, video_config
from app.services.video_info import get_video_info

logger = logging.getLogger(__name__)


class VideoGenerationError(Exception):
    """Raised for any failure while rendering a personalized video."""


def _escape_filter_path(path: Path) -> str:
    """Escapes a filesystem path for safe use inside an ffmpeg filtergraph option value."""
    return str(path).replace("\\", "/").replace(":", "\\:")


def _clamp(value: float, upper: float) -> float:
    return max(0.0, min(value, upper))


def _fit_name_font_size(text: str, font_path: Path | None, max_width: int, start_size: int, min_size: int) -> int:
    """Shrinks the name's font size (PIL-measured) so ffmpeg's drawtext never
    overflows the banner's name area — mirrors certificate_generator's
    auto-shrink-to-fit approach, but picks a numeric fontsize for ffmpeg
    instead of rendering directly."""
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(str(font_path), size) if font_path else ImageFont.load_default(size)
        bbox = font.getbbox(text)
        if (bbox[2] - bbox[0]) <= max_width:
            return size
        size -= 2
    return min_size


def _build_filter_complex(
    textfile_path: Path, font_path: Path | None, duration: float, name_font_size: int, outro_name_font_size: int
) -> str:
    photo_start = _clamp(video_config.PHOTO_START_TIME, duration)
    photo_end = _clamp(video_config.PHOTO_END_TIME, duration)
    name_start = _clamp(video_config.NAME_START_TIME, duration)
    name_end = _clamp(video_config.NAME_END_TIME, duration)
    
    outro_photo_start = _clamp(video_config.OUTRO_PHOTO_START_TIME, duration)
    outro_photo_end = _clamp(video_config.OUTRO_PHOTO_END_TIME, duration)
    outro_name_start = _clamp(video_config.OUTRO_NAME_START_TIME, duration)
    outro_name_end = _clamp(video_config.OUTRO_NAME_END_TIME, duration)
    outro_text_start = _clamp(video_config.OUTRO_START_TIME, duration)
    outro_text_end = _clamp(video_config.OUTRO_END_TIME, duration)

    def _drawtext(options: list[str]) -> str:
        if font_path is not None:
            options = [f"fontfile='{_escape_filter_path(font_path)}'", *options]
        return "drawtext=" + ":".join(options)

    welcome_drawtext = _drawtext(
        [
            f"text='{video_config.WELCOME_TEXT}'",
            f"x={video_config.WELCOME_X}",
            f"y={video_config.WELCOME_Y}",
            f"fontsize={video_config.WELCOME_FONT_SIZE}",
            f"fontcolor={video_config.WELCOME_COLOR}",
            f"borderw={video_config.WELCOME_BORDER_WIDTH}",
            f"bordercolor={video_config.WELCOME_BORDER_COLOR}",
            f"enable='between(t,{photo_start},{photo_end})'",
        ]
    )
    name_drawtext = _drawtext(
        [
            f"textfile='{_escape_filter_path(textfile_path)}'",
            "reload=0",
            f"x={video_config.NAME_X}",
            f"y={video_config.NAME_Y}",
            f"fontsize={name_font_size}",
            f"fontcolor={video_config.NAME_COLOR}",
            f"borderw={video_config.NAME_BORDER_WIDTH}",
            f"bordercolor={video_config.NAME_BORDER_COLOR}",
            f"enable='between(t,{name_start},{name_end})'",
        ]
    )
    
    outro_drawtext = _drawtext(
        [
            f"text='{video_config.OUTRO_TEXT}'",
            f"x={video_config.OUTRO_X}",
            f"y={video_config.OUTRO_Y}",
            f"fontsize={video_config.OUTRO_FONT_SIZE}",
            f"fontcolor={video_config.OUTRO_COLOR}",
            f"borderw={video_config.OUTRO_BORDER_WIDTH}",
            f"bordercolor={video_config.OUTRO_BORDER_COLOR}",
            f"enable='between(t,{outro_text_start},{outro_text_end})'",
        ]
    )
    outro_name_drawtext = _drawtext(
        [
            f"textfile='{_escape_filter_path(textfile_path)}'",
            "reload=0",
            f"x={video_config.OUTRO_NAME_X}",
            f"y={video_config.OUTRO_NAME_Y}",
            f"fontsize={outro_name_font_size}",
            f"fontcolor={video_config.OUTRO_NAME_COLOR}",
            f"borderw={video_config.OUTRO_NAME_BORDER_WIDTH}",
            f"bordercolor={video_config.OUTRO_NAME_BORDER_COLOR}",
            f"enable='between(t,{outro_name_start},{outro_name_end})'",
        ]
    )

    photo_x = video_config.PHOTO_CENTER_X - video_config.PHOTO_DIAMETER // 2
    photo_y = video_config.PHOTO_CENTER_Y - video_config.PHOTO_DIAMETER // 2
    
    outro_photo_x = video_config.OUTRO_PHOTO_CENTER_X - video_config.OUTRO_PHOTO_DIAMETER // 2
    outro_photo_y = video_config.OUTRO_PHOTO_CENTER_Y - video_config.OUTRO_PHOTO_DIAMETER // 2

    return (
        f"[1:v]scale={video_config.PHOTO_DIAMETER}:-1[photo_intro];"
        f"[1:v]scale={video_config.OUTRO_PHOTO_DIAMETER}:-1[photo_outro];"
        f"[0:v][photo_intro]overlay=x={photo_x}:y={photo_y}:"
        f"enable='between(t,{photo_start},{photo_end})'[v1];"
        f"[v1][photo_outro]overlay=x={outro_photo_x}:y={outro_photo_y}:"
        f"enable='between(t,{outro_photo_start},{outro_photo_end})'[v2];"
        f"[v2]{welcome_drawtext}[v3];"
        f"[v3]{name_drawtext}[v4];"
        f"[v4]{outro_drawtext}[v5];"
        f"[v5]{outro_name_drawtext}[vout]"
    )


def render_personalized_video(
    template_path: Path,
    photo_path: Path,
    visitor_display_name: str,
    output_path: Path,
    video_id: str,
) -> None:
    """Runs a single ffmpeg pass that overlays the photo + name and preserves audio."""
    video_info = get_video_info(template_path)

    # Kept in temp/ (not deleted) for debugging, matching the other visitor temp files.
    overlay_text = video_config.NAME_TEXT_TEMPLATE.format(name=visitor_display_name)
    textfile_path = config.TEMP_DIR / f"visitor_{video_id}_name.txt"
    textfile_path.parent.mkdir(parents=True, exist_ok=True)
    textfile_path.write_text(overlay_text, encoding="utf-8")

    font_path = video_config.resolve_font_path()
    name_font_size = _fit_name_font_size(
        overlay_text,
        font_path,
        video_config.NAME_MAX_TEXT_WIDTH,
        video_config.NAME_FONT_SIZE,
        video_config.NAME_MIN_FONT_SIZE,
    )
    outro_name_font_size = _fit_name_font_size(
        overlay_text,
        font_path,
        video_config.OUTRO_NAME_MAX_TEXT_WIDTH,
        video_config.OUTRO_NAME_FONT_SIZE,
        video_config.OUTRO_NAME_MIN_FONT_SIZE,
    )
    filter_complex = _build_filter_complex(textfile_path, font_path, video_info["duration"], name_font_size, outro_name_font_size)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(template_path),
        "-i",
        str(photo_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "0:a?",
        "-c:v",
        video_config.OUTPUT_VIDEO_CODEC,
        "-preset",
        video_config.OUTPUT_PRESET,
        "-crf",
        str(video_config.OUTPUT_CRF),
        "-pix_fmt",
        video_config.OUTPUT_PIXEL_FORMAT,
        "-c:a",
        video_config.OUTPUT_AUDIO_CODEC,
        "-shortest",
        str(output_path),
    ]

    logger.info("Running ffmpeg for video_id=%s", video_id)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=video_config.FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise VideoGenerationError("FFmpeg is not installed or not available on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        logger.error("FFmpeg timed out for video_id=%s\ncommand: %s", video_id, cmd)
        raise VideoGenerationError("Video rendering timed out.") from exc

    if result.returncode != 0:
        logger.error(
            "FFmpeg failed for video_id=%s (exit %s)\n"
            "command: %s\ninputs: %s, %s\noutput: %s\nstderr:\n%s",
            video_id,
            result.returncode,
            cmd,
            template_path,
            photo_path,
            output_path,
            result.stderr,
        )
        raise VideoGenerationError("FFmpeg failed to render the video.")

    if not output_path.exists() or output_path.stat().st_size == 0:
        logger.error("FFmpeg exited 0 but produced no output for video_id=%s", video_id)
        raise VideoGenerationError("Video rendering did not produce an output file.")
