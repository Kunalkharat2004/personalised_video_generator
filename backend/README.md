# Townhall Video Generator — Backend (Step 3: FFmpeg Video Compositing)

FastAPI backend that receives a visitor's selfie, removes the background,
crops it into a circular head-and-shoulders portrait, and then composites it
— together with the visitor's name — onto the real `townhall_final.mp4`
townhall video with FFmpeg to produce a personalized MP4. The photo + name
only appear during the 11s-13s WELCOME banner scene; the rest of the video
is untouched.

**Requires FFmpeg + ffprobe on PATH.** `app/config.py` auto-detects a
winget-installed FFmpeg (`Gyan.FFmpeg`) if it isn't already resolvable, so a
fresh shell isn't required after installing it that way.

## Setup

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

> `rembg` requires the `cpu` extra to install its inference backend
> (`onnxruntime`); it's already pinned as `rembg[cpu]` in `requirements.txt`.

## Run

```powershell
uvicorn app.main:app --reload --reload-dir app
```

`--reload-dir app` restricts the auto-reload file watcher to the `app/`
package. Without it, the watcher also scans `venv/`, and on a OneDrive-synced
project folder OneDrive's background sync keeps touching files under
`venv/Lib/site-packages`, which triggers an endless reload loop.

- API: http://localhost:8000
- Docs (Swagger): http://localhost:8000/docs

## Endpoints

| Method | Path                      | Description                                         |
|--------|---------------------------|------------------------------------------------------|
| GET    | `/`                       | Root status message                                 |
| GET    | `/api/health`             | Health check                                        |
| POST   | `/api/process-image`      | Upload `name` + `file`, returns processed PNG info  |
| GET    | `/api/images/{image_id}`  | Fetch the processed transparent PNG                 |
| POST   | `/api/generate-video`     | JSON `{visitor_name, image_id}` → personalized MP4 |
| GET    | `/api/videos/{video_id}`  | Fetch the generated MP4 (`video/mp4`)               |

`POST /api/process-image` expects `multipart/form-data` with fields `name`
and `file` (JPEG/PNG/WEBP, max size from `MAX_UPLOAD_SIZE_MB`, default 10MB).

`POST /api/generate-video` expects JSON with `visitor_name` and the
`image_id` returned by `/api/process-image`. It does **not** re-accept the
selfie file.

## Processing pipeline

1. Validate visitor name (non-empty after trim) and image (content-type +
   Pillow-verified format).
2. Save the original upload to `../temp/visitor_<id>_original.jpg`.
3. Remove the background with `rembg` (U^2-Net model, downloaded on first use).
4. Smooth cutout edges slightly with OpenCV (`GaussianBlur` on the alpha
   channel).
5. Composite the cutout onto a solid light-grey backdrop (no transparency
   behind the subject), then crop to a head-and-shoulders portrait driven by
   the subject's shoulder-span width (same heuristic as `certificate_generator`),
   resize to the banner's photo-circle diameter, and apply a circular alpha
   mask so ffmpeg can overlay it directly — corners outside the circle are
   transparent.
6. Save as `../temp/visitor_<id>_processed.png` and return its URL.

## Temporary files & cleanup

Files are written to the project-level `temp/` and `generated/` directories
(not inside `backend/`). For this MVP step, files are intentionally **not
deleted** after processing/generation — `temp/` keeps `visitor_<id>_original.jpg`,
`visitor_<id>_processed.png`, and `visitor_<video_id>_name.txt` (the drawtext
source file, kept for debugging); `generated/` keeps `video_<video_id>.mp4`.
`app/utils/file_utils.py` has `cleanup_visitor_artifacts()` for a future
scheduled cleanup job — none is wired up yet.

## Video generation pipeline

1. Validate `visitor_name` (non-empty, collapsed whitespace, then
   `.title()`-cased) and `image_id` (must match the processed PNG's uuid
   pattern — rejects path traversal).
2. Probe the template video with `ffprobe` (`app/services/video_info.py`) for
   its real resolution/fps/duration — nothing is hard-coded.
3. Write the visitor's name to a temp `.txt` file — `drawtext=textfile=...`
   is used instead of interpolating the name into the command string, so
   apostrophes/hyphens/spaces are always safe. The name's font size is
   auto-shrunk (PIL-measured) to fit the banner's name area, mirroring
   `certificate_generator`'s auto-shrink-to-fit approach.
4. Run a single `ffmpeg` call (`app/services/video_generator.py`) via
   `subprocess.run([...])` (never `shell=True`) with one `filter_complex`:
   overlay the pre-masked circular photo → `drawtext` a static "Welcome"
   heading → `drawtext` the visitor name → map the original audio through
   unchanged. All three (photo, heading, name) are gated to the 11s-13s
   WELCOME banner window via `enable='between(t,11,13)'`. Output is
   H.264/AAC/yuv420p MP4.
5. Validate the ffmpeg exit code and that a non-empty output file exists
   before returning success.

All tunable values (photo circle position/size, banner timing, text
position/size, font, encoding) live in `app/video_config.py` — nothing is
scattered elsewhere. The photo-circle and text-band coordinates were
measured (not guessed) against `templates/bg_2.png`, a mockup of the
intended banner frame, via OpenCV, then scaled to `townhall_final.mp4`'s
real 1920x1080 resolution. See that file's comments for how to retune them
if the banner design or video resolution changes.

### Font

The "Welcome" heading and visitor name are rendered with
`assests/fonts/Milesdane Trial.otf` (note: the project's assets folder is
actually named `assests/`, not `assets/`). If that file is ever removed,
`resolve_font_path()` falls back to a common Windows system font for local dev.

## Configuration

All configuration is environment-driven (see `.env.example`):

- `HOST`, `PORT` — Uvicorn bind address
- `FRONTEND_URL` — primary allowed CORS origin
- `CORS_ORIGINS` — optional comma-separated extra allowed origins
- `MAX_UPLOAD_SIZE_MB` — upload size cap

## Tests

```powershell
pytest
```

The full-pipeline test (`test_process_image_valid`) exercises `rembg` and is
skipped automatically if the background-removal model can't be loaded in the
current environment (e.g. no network on first run, since the model is
downloaded on demand).

## FFmpeg

Required for this step. Installed via `winget install Gyan.FFmpeg` on this
machine (FFmpeg 9.0.2, includes `ffprobe`, libx264/libx265/AAC/fontconfig).
`app/config.py` will auto-discover a winget install even if the launching
shell's PATH hasn't been refreshed.
