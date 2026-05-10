"""LLM summarization via LiteLLM."""

import os

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


def summarize(transcript: str, model: str = "gpt-4o", api_key: str | None = None) -> tuple[str, dict]:
    """Send transcript to LLM and return (markdown_summary, usage_dict).

    usage_dict keys: prompt_tokens, completion_tokens, total_tokens, cost_usd
    """
    import litellm

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

    usage = response.usage or {}
    try:
        cost_usd = litellm.completion_cost(completion_response=response)
    except Exception:
        cost_usd = 0.0

    usage_dict = {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
        "completion_tokens": getattr(usage, "completion_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
        "cost_usd": cost_usd,
    }
    return response.choices[0].message.content.strip(), usage_dict
