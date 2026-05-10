"""Audio extraction from video using ffmpeg."""

import subprocess
import tempfile
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts", ".mts"
}


def check_ffmpeg() -> None:
    """Raise RuntimeError if ffmpeg is not installed."""
    result = subprocess.run(
        ["ffmpeg", "-version"], capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg not found. Install it with:\n"
            "  macOS:  brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


def validate_video(path: Path) -> None:
    """Raise ValueError if the file extension is not supported."""
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file format '{path.suffix}'. "
            f"Supported formats: {supported}"
        )


def extract_audio(video_path: Path, tmp_dir: str) -> Path:
    """Extract audio from video_path into a WAV file in tmp_dir."""
    check_ffmpeg()
    validate_video(video_path)

    audio_path = Path(tmp_dir) / f"{video_path.stem}.wav"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",                  # no video
            "-acodec", "pcm_s16le", # WAV
            "-ar", "16000",         # 16 kHz — optimal for Whisper
            "-ac", "1",             # mono
            str(audio_path),
        ],
        capture_output=True,
        check=True,
    )
    return audio_path
