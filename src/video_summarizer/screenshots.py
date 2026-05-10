"""Extract representative screenshots from a video.

Strategy: fixed interval (one frame per minute by default), configurable
via SCREENSHOT_INTERVAL. Simple, predictable, works well for presentations
with a speaker where scene detection fires too rarely or too often.
"""

import json
import subprocess
from pathlib import Path


SCREENSHOT_INTERVAL = 60  # seconds between captures


def _get_duration(video_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def _capture_frame(video_path: Path, timestamp: float, out_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", f"{timestamp:.2f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            "-vf", "scale=1280:-1",
            str(out_path),
        ],
        capture_output=True,
        check=True,
    )


def extract_screenshots(video_path: Path, output_dir: Path, interval: int = SCREENSHOT_INTERVAL) -> list[Path]:
    """
    Extract one screenshot every `interval` seconds from video_path.
    Saves to output_dir/<stem>_screenshots/ and returns list of saved paths.
    """
    screenshots_dir = output_dir / f"{video_path.stem}_screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    duration = _get_duration(video_path)
    timestamps = []
    ts = interval
    while ts < duration:
        timestamps.append(ts)
        ts += interval

    saved = []
    for i, ts in enumerate(timestamps):
        filename = f"frame_{i+1:03d}_{int(ts)}s.jpg"
        out_path = screenshots_dir / filename
        try:
            _capture_frame(video_path, ts, out_path)
            saved.append(out_path)
        except subprocess.CalledProcessError:
            pass

    return saved

