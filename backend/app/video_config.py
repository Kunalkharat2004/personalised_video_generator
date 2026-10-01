"""Video generation configuration for the real townhall_final.mp4 template.

Tune these values (and re-run) after visually inspecting a generated video —
nothing overlay/position/timing-related is scattered elsewhere in the code.

The WELCOME banner (photo + name) coordinates below were measured (not
guessed) against templates/bg_2.png — a 668x373 mockup of the intended
11-13s banner frame — via OpenCV (HoughCircles for the photo circle,
connected-components on an HSV white-text mask for the "Welcome"/name text
bands), then scaled up to townhall_final.mp4's real 1920x1080 resolution
(confirmed via ffprobe). Re-measure and rescale these if either the banner
design or the video's resolution ever changes.
"""
from pathlib import Path

from app.config import BASE_DIR

# --- Template & output locations -----------------------------------------
VIDEO_TEMPLATE_PATH = BASE_DIR / "templates" / "townhall_final.mp4"
OUTPUT_DIRECTORY = BASE_DIR / "generated"

# --- WELCOME banner timing --------------------------------------------------
# The photo + name only appear during this window of townhall_final.mp4 (the
# intro banner scene); the rest of the video is untouched.
# Verified by frame inspection: the BMW roundel "bubble" dissolves into the
# neon starburst by ~10.0s, a ring-burst pulse plays ~11.25-11.6s, then the
# scene hard-cuts to an unrelated blue hex-tunnel scene by ~11.75s. This
# window keeps the banner fully inside the neon starburst scene, starting
# right after the bubble burst.
BANNER_START_TIME = 11.6  # seconds
BANNER_END_TIME = 14.8  # seconds

# --- Visitor photo overlay (circular, matches the WELCOME banner design) ---
PHOTO_CENTER_X = 960  # px, horizontal center of the banner's photo circle
PHOTO_CENTER_Y = 560  # px, vertical center of the banner's photo circle
PHOTO_DIAMETER = 460  # px
# Solid backdrop the extracted person is composited onto before cropping —
# the circular photo must never show transparency behind the subject.
PHOTO_BACKGROUND_COLOR = (220, 220, 220)
# Portrait "zoom" applied on top of the auto-detected head+shoulders crop.
# >1.0 crops tighter (person fills more of the circle); <1.0 zooms out.
PHOTO_SCALE = 1.08
# Small backdrop-colored headroom above the head, as a fraction of the crop's
# side length, so the hair doesn't touch the very top of the circle.
PHOTO_HEADROOM_RATIO = 0.08
PHOTO_START_TIME = BANNER_START_TIME
PHOTO_END_TIME = BANNER_END_TIME

# --- "Welcome" heading text --------------------------------------------------
WELCOME_TEXT = "Welcome"
WELCOME_X = "(w-text_w)/2"  # ffmpeg expression: horizontally centered
WELCOME_Y = "162-(text_h/2)"  # vertically centers the text on the measured band
WELCOME_FONT_SIZE = 180
WELCOME_COLOR = "white"
WELCOME_BORDER_COLOR = "black"
WELCOME_BORDER_WIDTH = 2

# --- Visitor name overlay ---------------------------------------------------
NAME_TEXT_TEMPLATE = "{name}"
NAME_X = "(w-text_w)/2"  # ffmpeg expression: horizontally centered
NAME_Y = "944-(text_h/2)"  # vertically centers the text on the measured band
NAME_FONT_SIZE = 170  # starting size; auto-shrinks to fit NAME_MAX_TEXT_WIDTH
NAME_MIN_FONT_SIZE = 40
NAME_MAX_TEXT_WIDTH = 1700  # px, leaves margin within the 1920px-wide frame
NAME_COLOR = "white"
NAME_BORDER_COLOR = "black"
NAME_BORDER_WIDTH = 2
NAME_START_TIME = BANNER_START_TIME
NAME_END_TIME = BANNER_END_TIME

# --- OUTRO banner timing (end card) ------------------------------------------
# Visitor photo + name appear on the dark blue outro background at the end.
OUTRO_START_TIME = 96.8  # seconds (1:36.8)
OUTRO_END_TIME = 98.5  # seconds (1:38.5)

# --- Outro visitor photo overlay (circular, same as intro) -------------------
OUTRO_PHOTO_CENTER_X = 960
OUTRO_PHOTO_CENTER_Y = 540
OUTRO_PHOTO_DIAMETER = 380
OUTRO_PHOTO_BACKGROUND_COLOR = (220, 220, 220)
OUTRO_PHOTO_SCALE = 1.08
OUTRO_PHOTO_HEADROOM_RATIO = 0.08
OUTRO_PHOTO_START_TIME = OUTRO_START_TIME
OUTRO_PHOTO_END_TIME = OUTRO_END_TIME

# --- Outro "Thank You" heading text ------------------------------------------
OUTRO_TEXT = "Thank You"
OUTRO_X = "(w-text_w)/2"
OUTRO_Y = "280-(text_h/2)"
OUTRO_FONT_SIZE = 140
OUTRO_COLOR = "white"
OUTRO_BORDER_COLOR = "black"
OUTRO_BORDER_WIDTH = 2

# --- Outro visitor name overlay ----------------------------------------------
OUTRO_NAME_TEXT_TEMPLATE = "{name}"
OUTRO_NAME_X = "(w-text_w)/2"
OUTRO_NAME_Y = "800-(text_h/2)"
OUTRO_NAME_FONT_SIZE = 130
OUTRO_NAME_MIN_FONT_SIZE = 40
OUTRO_NAME_MAX_TEXT_WIDTH = 1700
OUTRO_NAME_COLOR = "white"
OUTRO_NAME_BORDER_COLOR = "black"
OUTRO_NAME_BORDER_WIDTH = 2
OUTRO_NAME_START_TIME = OUTRO_START_TIME
OUTRO_NAME_END_TIME = OUTRO_END_TIME

# --- Font -------------------------------------------------------------------
# Used for all text overlays (welcome, name, outro, etc).
CUSTOM_FONT_PATH = BASE_DIR / "assests" / "fonts" / "Milesdane Trial.otf"
_FALLBACK_FONT_PATHS = [
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
]


def resolve_font_path() -> Path | None:
    """Returns the font file to use, or None to let ffmpeg pick a default."""
    if CUSTOM_FONT_PATH.exists():
        return CUSTOM_FONT_PATH
    for candidate in _FALLBACK_FONT_PATHS:
        if candidate.exists():
            return candidate
    return None


# --- Output encoding ---------------------------------------------------------
OUTPUT_VIDEO_CODEC = "libx264"
OUTPUT_AUDIO_CODEC = "aac"
OUTPUT_PIXEL_FORMAT = "yuv420p"
OUTPUT_CRF = 20
OUTPUT_PRESET = "veryfast"
FFMPEG_TIMEOUT_SECONDS = 120
