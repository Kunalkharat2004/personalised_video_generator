"""Selfie processing pipeline: background removal -> composite on a light-grey
backdrop -> crop to a head-and-shoulders portrait, scaled to fill the WELCOME
banner's photo circle -> circular alpha mask, ready for ffmpeg to overlay
directly onto the video.

Uploaded selfie
      v
Background removal using rembg
      v
Composite onto a solid light-grey backdrop (no transparency behind the subject)
      v
Crop to a head-and-shoulders portrait, scaled to fill the photo circle
      v
Resize to PHOTO_DIAMETER and apply a circular alpha mask

Zoom/crop logic mirrors certificate_generator's image_processor (same
head+shoulders portrait heuristic), since both projects fit a selfie into a
circular slot. The circular mask is applied here (not at video-composite
time) because ffmpeg has no easy equivalent of PIL's per-frame masking — the
transparent-outside-the-circle PNG is what ffmpeg's overlay filter composites
onto the video.
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw

from app import video_config
from app.services.background_remover import remove_background


def _smooth_alpha_edges(image: Image.Image, ksize: int = 3) -> Image.Image:
    """Softens rembg's cutout edges with a small Gaussian blur on the alpha channel."""
    r, g, b, a = image.split()
    alpha = cv2.GaussianBlur(np.array(a), (ksize, ksize), 0)
    return Image.merge("RGBA", (r, g, b, Image.fromarray(alpha)))


def _composite_on_background(image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """Flattens an RGBA cutout onto a solid-color RGB canvas — the photo circle
    must never show transparency behind the subject."""
    canvas = Image.new("RGB", image.size, color)
    canvas.paste(image, (0, 0), image)
    return canvas


def _largest_subject_bbox(alpha: Image.Image, threshold: int = 128) -> tuple[int, int, int, int] | None:
    """Returns the bounding box of the LARGEST connected alpha blob, ignoring
    small disconnected noise specks that would otherwise blow up a naive
    `Image.getbbox()` (e.g. a stray high-alpha pixel elsewhere in the frame)."""
    mask = (np.array(alpha) >= threshold).astype(np.uint8)
    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num_labels <= 1:
        return None  # only the background label — nothing detected

    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, area = stats[largest_label]
    if area < 500:  # too small to plausibly be the subject
        return None
    return (int(x), int(y), int(x + w), int(y + h))


def _portrait_crop_box(alpha: Image.Image) -> tuple[int, int, int, int]:
    """Returns a square (left, top, right, bottom) box framing head+shoulders.

    Derived from the subject silhouette's WIDTH (shoulder span) rather than
    its full height, so it isn't thrown off by a zoomed-out selfie. Clamped
    to the source image bounds so the crop never runs past its edges.
    """
    img_width, img_height = alpha.size
    bbox = _largest_subject_bbox(alpha)
    if bbox is None:
        # Nothing detected (e.g. a blank/solid test image) — fall back to the full frame.
        return (0, 0, img_width, img_height)

    left, top, right, _bottom = bbox
    width = right - left
    side = max(1, width / video_config.PHOTO_SCALE)
    center_x = (left + right) / 2

    ratio = video_config.PHOTO_HEADROOM_RATIO
    max_side_by_height = (img_height - top) / (1 - ratio)
    max_side_by_width = 2 * min(center_x, img_width - center_x)
    side = round(min(side, max_side_by_height, max_side_by_width))

    headroom = side * ratio
    box_top = round(top - headroom)
    box_left = round(center_x - side / 2)
    return (box_left, box_top, box_left + side, box_top + side)


def _crop_with_padding(image: Image.Image, box: tuple[int, int, int, int], fill) -> Image.Image:
    """Crops `box` out of `image`, padding with `fill` for any part that falls
    outside the original bounds (instead of raising or clamping/distorting)."""
    left, top, right, bottom = box
    side = right - left
    canvas = Image.new(image.mode, (side, bottom - top), fill)
    canvas.paste(image, (-left, -top))
    return canvas


def _circular_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    return mask


def process_selfie(image: Image.Image) -> Image.Image:
    """Full pipeline: remove background, composite onto a light-grey backdrop,
    crop to a head-and-shoulders portrait, resize to the banner's photo circle
    diameter, and apply a circular alpha mask. Returns an RGBA image — never
    mutates `image`.
    """
    removed = remove_background(image)
    smoothed = _smooth_alpha_edges(removed)
    on_background = _composite_on_background(smoothed, video_config.PHOTO_BACKGROUND_COLOR)

    crop_box = _portrait_crop_box(smoothed.getchannel("A"))
    cropped = _crop_with_padding(on_background, crop_box, video_config.PHOTO_BACKGROUND_COLOR)

    diameter = video_config.PHOTO_DIAMETER
    resized = cropped.resize((diameter, diameter), Image.LANCZOS).convert("RGBA")
    resized.putalpha(_circular_mask(diameter))
    return resized
