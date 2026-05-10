"""Extract representative screenshots from a video.

Strategy: scene-change detection with a high threshold to catch slide transitions,
combined with a minimum gap between captures to suppress speaker-movement noise.
Falls back to fixed-interval sampling if scene detection yields too few frames.
"""

import subprocess
from pathlib import Path


# A scene score > SCENE_THRESHOLD is considered a significant change (slide flip)
SCENE_THRESHOLD = 0.45
# Never capture two screenshots closer than this many seconds apart
MIN_GAP_SECONDS = 20
# If scene detection finds fewer than this many frames, fall back to fixed interval
MIN_FRAMES_FALLBACK = 3
# Fixed-interval fallback: one screenshot every N seconds
FALLBACK_INTERVAL = 60


def _get_duration(video_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
        capture_output=True, text=True,
    )
    import json
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def _scene_timestamps(video_path: Path) -> list[float]:
    """Return timestamps (seconds) of scene changes above SCENE_THRESHOLD."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-show_frames",
            "-select_streams", "v",
            "-show_entries", "frame=best_effort_timestamp_time,pkt_pts_time",
            "-read_intervals", "%+#99999",
            "-f", "csv",
            "-i", str(video_path),
        ],
        capture_output=True, text=True,
    )
    # Use ffmpeg scene filter instead — more reliable
    proc = subprocess.run(
        [
            "ffmpeg", "-i", str(video_path),
            "-vf", f"select='gt(scene,{SCENE_THRESHOLD})',showinfo",
            "-vsync", "vfr",
            "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    timestamps = []
    last_ts = -MIN_GAP_SECONDS

    for line in proc.stderr.splitlines():
        if "pts_time:" in line:
            try:
                ts_str = line.split("pts_time:")[1].split()[0]
                ts = float(ts_str)
                if ts - last_ts >= MIN_GAP_SECONDS:
                    timestamps.append(ts)
                    last_ts = ts
            except (IndexError, ValueError):
                continue

    return timestamps


def _fixed_interval_timestamps(duration: float) -> list[float]:
    """Return timestamps at fixed FALLBACK_INTERVAL spacing."""
    ts = FALLBACK_INTERVAL
    timestamps = []
    while ts < duration:
        timestamps.append(ts)
        ts += FALLBACK_INTERVAL
    return timestamps


def _capture_frame(video_path: Path, timestamp: float, out_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", f"{timestamp:.2f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",         # JPEG quality
            "-vf", "scale=1280:-1",  # cap width at 1280px
            str(out_path),
        ],
        capture_output=True,
        check=True,
    )


def extract_screenshots(video_path: Path, output_dir: Path) -> list[Path]:
    """
    Extract screenshots from video_path into output_dir/<stem>_screenshots/.
    Returns list of saved image paths (relative to output_dir).
    """
    screenshots_dir = output_dir / f"{video_path.stem}_screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    duration = _get_duration(video_path)
    timestamps = _scene_timestamps(video_path)

    if len(timestamps) < MIN_FRAMES_FALLBACK:
        timestamps = _fixed_interval_timestamps(duration)

    saved = []
    for i, ts in enumerate(timestamps):
        filename = f"frame_{i+1:03d}_{int(ts)}s.jpg"
        out_path = screenshots_dir / filename
        try:
            _capture_frame(video_path, ts, out_path)
            saved.append(out_path)
        except subprocess.CalledProcessError:
            pass  # skip failed frames silently

    return saved
