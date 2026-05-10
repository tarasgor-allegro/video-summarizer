"""Whisper transcription with disk caching.

Supports three backends:
  - local                 : OpenAI Whisper running on-device (default, free)
  - whisper-1             : OpenAI Whisper API (cloud, $0.006/min)
  - gpt-4o-transcribe     : OpenAI GPT-4o Transcribe API (cloud, $0.006/min)
  - gpt-4o-mini-transcribe: OpenAI GPT-4o Mini Transcribe API (cloud, $0.003/min)
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import click

WHISPER_MODELS = {"tiny", "base", "small", "medium", "large"}
OPENAI_API_MODELS = {"whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"}

# Max audio seconds per API request (OpenAI limit is 1400s; use 1200s for safety)
CHUNK_SECONDS = 1200


def _cache_path(video_path: Path) -> Path:
    return video_path.parent / f".{video_path.name}.transcript.json"


def _is_cache_valid(video_path: Path, cache: Path) -> bool:
    if not cache.exists():
        return False
    return cache.stat().st_mtime >= video_path.stat().st_mtime


def _audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def _split_audio(audio_path: Path, tmp_dir: str, chunk_seconds: int) -> list[Path]:
    """Split audio into chunks of at most chunk_seconds. Returns list of chunk paths."""
    duration = _audio_duration(audio_path)
    if duration <= chunk_seconds:
        return [audio_path]

    chunks = []
    start = 0
    idx = 0
    while start < duration:
        chunk_path = Path(tmp_dir) / f"chunk_{idx:03d}.wav"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-t", str(chunk_seconds),
                "-i", str(audio_path),
                str(chunk_path),
            ],
            capture_output=True, check=True,
        )
        chunks.append(chunk_path)
        start += chunk_seconds
        idx += 1

    return chunks


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


def _transcribe_chunk(client, audio_path: Path, api_model: str, response_format: str) -> tuple[str, str]:
    """Transcribe a single audio chunk. Returns (text, language)."""
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model=api_model,
            file=f,
            response_format=response_format,
        )
    if response_format == "verbose_json":
        return response.text.strip(), getattr(response, "language", "unknown") or "unknown"
    else:
        text = (response.text if hasattr(response, "text") else str(response)).strip()
        return text, "unknown"


def _transcribe_openai_api(audio_path: Path, api_model: str, api_key: str | None = None) -> dict:
    import openai

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set.\n"
            "Run `summarize` without --model to set it up interactively, "
            "or export it with: export OPENAI_API_KEY=sk-..."
        )

    client = openai.OpenAI(api_key=key)
    # verbose_json is only supported by whisper-1
    response_format = "verbose_json" if api_model == "whisper-1" else "json"

    with tempfile.TemporaryDirectory() as tmp:
        chunks = _split_audio(audio_path, tmp, CHUNK_SECONDS)
        total = len(chunks)

        texts = []
        language = "unknown"

        for i, chunk in enumerate(chunks, 1):
            if total > 1:
                click.echo(f"    Chunk {i}/{total}…", nl=False)
            chunk_text, chunk_lang = _transcribe_chunk(client, chunk, api_model, response_format)
            if total > 1:
                click.echo(f" ✓ ({len(chunk_text.split())} words)")
            texts.append(chunk_text)
            if chunk_lang != "unknown":
                language = chunk_lang

    return {"text": " ".join(texts).strip(), "language": language}


def transcribe(
    audio_path: Path,
    video_path: Path,
    whisper_model: str = "base",
    transcriber: str = "local",
    no_cache: bool = False,
    api_key: str | None = None,
) -> dict:
    """
    Transcribe audio and return a dict with keys:
      - text: full transcript string
      - language: detected language code (e.g. 'en')

    Args:
        transcriber: 'local', 'whisper-1', 'gpt-4o-transcribe', or 'gpt-4o-mini-transcribe'
        whisper_model: only used when transcriber='local'
        api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
    """
    cache = _cache_path(video_path)

    if not no_cache and _is_cache_valid(video_path, cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)

    if transcriber == "local":
        payload = _transcribe_local(audio_path, whisper_model)
    elif transcriber in OPENAI_API_MODELS:
        payload = _transcribe_openai_api(audio_path, transcriber, api_key=api_key)
    else:
        raise ValueError(
            f"Unknown transcriber '{transcriber}'. "
            f"Choose from: local, {', '.join(sorted(OPENAI_API_MODELS))}"
        )

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload

