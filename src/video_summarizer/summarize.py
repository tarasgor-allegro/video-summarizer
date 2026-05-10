"""LLM summarization via LiteLLM, with per-model disk cache."""

import json
import os
import re
from pathlib import Path

from litellm import completion


SYSTEM_PROMPT = """\
You are an expert at summarizing spoken content from videos.
You will receive a full transcript and must produce a structured summary in English.

Respond ONLY with valid Markdown using exactly this structure (no extra text before or after):

## TL;DR

<2–4 sentences capturing the core message>

## Key Points

- <point>
- <point>
- ...

## Topics Covered

- <topic>
- <topic>
- ...
"""

USER_PROMPT_TEMPLATE = """\
Please summarize the following video transcript:

---
{transcript}
---
"""


def _model_slug(model: str) -> str:
    """Turn a model string into a safe filename component."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _cache_path(video_path: Path, model: str) -> Path:
    return video_path.parent / f".{video_path.name}.summary.{_model_slug(model)}.json"


def _transcript_cache_path(video_path: Path) -> Path:
    return video_path.parent / f".{video_path.name}.transcript.json"


def _is_cache_valid(video_path: Path, model: str) -> bool:
    cache = _cache_path(video_path, model)
    if not cache.exists():
        return False
    transcript_cache = _transcript_cache_path(video_path)
    # Invalidate if transcript was re-generated after summary was cached
    if transcript_cache.exists() and transcript_cache.stat().st_mtime > cache.stat().st_mtime:
        return False
    return True


def _load_cache(video_path: Path, model: str) -> tuple[str, dict] | None:
    cache = _cache_path(video_path, model)
    with open(cache, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["summary"], data.get("usage", {})


def _save_cache(video_path: Path, model: str, summary: str, usage: dict) -> None:
    cache = _cache_path(video_path, model)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "usage": usage}, f, ensure_ascii=False, indent=2)


def summarize(
    transcript: str,
    model: str = "gpt-4o",
    api_key: str | None = None,
    video_path: Path | None = None,
    no_cache: bool = False,
) -> tuple[str, dict]:
    """Send transcript to LLM and return (markdown_summary, usage_dict).

    usage_dict keys: prompt_tokens, completion_tokens, total_tokens, cost_usd, cached
    """
    import litellm

    if video_path and not no_cache and _is_cache_valid(video_path, model):
        summary, usage = _load_cache(video_path, model)
        return summary, {**usage, "cached": True}

    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(transcript=transcript)},
        ],
    )
    if api_key:
        kwargs["api_key"] = api_key
    response = completion(**kwargs)

    raw_usage = response.usage or {}
    try:
        cost_usd = litellm.completion_cost(completion_response=response)
    except Exception:
        cost_usd = 0.0

    usage_dict = {
        "prompt_tokens": getattr(raw_usage, "prompt_tokens", 0),
        "completion_tokens": getattr(raw_usage, "completion_tokens", 0),
        "total_tokens": getattr(raw_usage, "total_tokens", 0),
        "cost_usd": cost_usd,
        "cached": False,
    }
    summary = response.choices[0].message.content.strip()

    if video_path:
        _save_cache(video_path, model, summary, usage_dict)

    return summary, usage_dict

