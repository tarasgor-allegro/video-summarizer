"""Cost estimation and usage reporting."""

# Transcription pricing: USD per minute of audio
TRANSCRIPTION_COST_PER_MIN: dict[str, float] = {
    "whisper-1": 0.006,
    "gpt-4o-transcribe": 0.006,
    "gpt-4o-mini-transcribe": 0.003,
    "local": 0.0,
}

# LLM pricing: USD per 1M tokens (input, output)
# Used only for estimates; actual cost comes from litellm.completion_cost()
LLM_COST_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o":                  (2.50,  10.00),
    "gpt-4o-mini":             (0.15,   0.60),
    "gpt-4-turbo":             (10.00,  30.00),
    "claude-3-5-sonnet":       (3.00,  15.00),
    "claude-3-opus":           (15.00, 75.00),
    "claude-3-haiku":          (0.25,   1.25),
    "ollama":                  (0.0,    0.0),
}

CHARS_PER_TOKEN = 4  # rough approximation


def transcription_estimate(duration_seconds: float, transcriber: str) -> tuple[float, float]:
    """Return (duration_minutes, estimated_usd) for a cloud transcription."""
    minutes = duration_seconds / 60
    rate = TRANSCRIPTION_COST_PER_MIN.get(transcriber, 0.006)
    return minutes, minutes * rate


def llm_estimate(transcript: str, model: str) -> tuple[int, float]:
    """Return (estimated_input_tokens, estimated_usd) for an LLM summarization call."""
    # Find the closest pricing key (model strings may have version suffixes)
    rate_in, rate_out = 0.0, 0.0
    for key, rates in LLM_COST_PER_1M.items():
        if model.startswith(key) or key in model:
            rate_in, rate_out = rates
            break

    # Estimate: input = transcript + ~500 token system prompt; output ~ 400 tokens
    input_tokens = len(transcript) // CHARS_PER_TOKEN + 500
    output_tokens = 400
    cost = (input_tokens * rate_in + output_tokens * rate_out) / 1_000_000
    return input_tokens, cost


def format_cost(usd: float) -> str:
    if usd == 0:
        return "free"
    if usd < 0.001:
        return f"< $0.001"
    return f"~${usd:.3f}"


def get_audio_duration(audio_path) -> float:
    """Return audio duration in seconds using ffprobe."""
    import subprocess, json
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0
