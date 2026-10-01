The WELCOME banner's "Welcome" heading and visitor name are rendered with
`Milesdane Trial.otf` in this folder — see `resolve_font_path()` in
`backend/app/video_config.py`.

If that file is ever removed, the app falls back to a common Windows system
font (Arial) for local development. For a real booth deployment, make sure a
properly licensed font file is present here instead of relying on the OS
default.
