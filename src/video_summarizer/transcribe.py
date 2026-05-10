"""Whisper transcription with disk caching.

Supports three backends:
  - local               : OpenAI Whisper running on-device (default, free)
  - whisper-1           : OpenAI Whisper API (cloud, $0.006/min)
  - gpt-realtime-whisper: OpenAI GPT Realtime Whisper API (cloud, $0.017/min)
"""

import json
import os
from pathlib import Path


WHISPER_MODELS = {"tiny", "base", "small", "medium", "large"}
OPENAI_API_MODELS = {"whisper-1", "gpt-realtime-whisper"}


def _cache_path(video_path: Path) -> Path:
    return video_path.parent / f".{video_path.name}.transcript.json"


def _is_cache_valid(video_path: Path, cache: Path) -> bool:
    if not cache.exists():
        return False
    return cache.stat().st_mtime >= video_path.stat().st_mtime


def _transcribe_local(audio_path: Path, whisper_model: str) -> dict:
    import whisper as _whisper

    if whisper_model not in WHISPER_MODELS:
        raise ValueError(
            f"Unknown local Whisper model '{whisper_model}'. "
            f"Choose from: {', '.join(sorted(WHISPER_MODELS))}"
        )
    model = _whisper.load_model(whisper_model)
    result = model.transcribe(str(audio_path), task="transcribe")
    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
    }


def _transcribe_openai_api(audio_path: Path, api_model: str) -> dict:
    import openai

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set.\n"
            "Export it with: export OPENAI_API_KEY=sk-..."
        )

    client = openai.OpenAI(api_key=api_key)
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model=api_model,
            file=f,
            response_format="verbose_json",
        )

    return {
        "text": response.text.strip(),
        "language": getattr(response, "language", "unknown") or "unknown",
    }


def transcribe(
    audio_path: Path,
    video_path: Path,
    whisper_model: str = "base",
    transcriber: str = "local",
    no_cache: bool = False,
) -> dict:
    """
    Transcribe audio and return a dict with keys:
      - text: full transcript string
      - language: detected language code (e.g. 'en')

    Args:
        transcriber: 'local', 'whisper-1', or 'gpt-realtime-whisper'
        whisper_model: only used when transcriber='local'
    """
    cache = _cache_path(video_path)

    if not no_cache and _is_cache_valid(video_path, cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)

    if transcriber == "local":
        payload = _transcribe_local(audio_path, whisper_model)
    elif transcriber in OPENAI_API_MODELS:
        payload = _transcribe_openai_api(audio_path, transcriber)
    else:
        raise ValueError(
            f"Unknown transcriber '{transcriber}'. "
            f"Choose from: local, {', '.join(sorted(OPENAI_API_MODELS))}"
        )

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload
