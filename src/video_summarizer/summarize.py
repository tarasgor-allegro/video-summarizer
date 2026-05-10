"""LLM summarization via LiteLLM."""

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


def summarize(transcript: str, model: str = "gpt-4o") -> str:
    """Send transcript to LLM and return the markdown summary block."""
    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(transcript=transcript)},
        ],
    )
    return response.choices[0].message.content.strip()
