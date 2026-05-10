"""Whisper transcription with disk caching."""

import json
import os
from pathlib import Path

import whisper


WHISPER_MODELS = {"tiny", "base", "small", "medium", "large"}


def _cache_path(video_path: Path) -> Path:
    return video_path.parent / f".{video_path.name}.transcript.json"


def _is_cache_valid(video_path: Path, cache: Path) -> bool:
    if not cache.exists():
        return False
    return cache.stat().st_mtime >= video_path.stat().st_mtime


def transcribe(
    audio_path: Path,
    video_path: Path,
    whisper_model: str = "base",
    no_cache: bool = False,
) -> dict:
    """
    Transcribe audio and return a dict with keys:
      - text: full transcript string
      - language: detected language code (e.g. 'en')
    """
    if whisper_model not in WHISPER_MODELS:
        raise ValueError(
            f"Unknown Whisper model '{whisper_model}'. "
            f"Choose from: {', '.join(sorted(WHISPER_MODELS))}"
        )

    cache = _cache_path(video_path)

    if not no_cache and _is_cache_valid(video_path, cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)

    model = whisper.load_model(whisper_model)
    result = model.transcribe(str(audio_path), task="transcribe")

    payload = {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
    }

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload
