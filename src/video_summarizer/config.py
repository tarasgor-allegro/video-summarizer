"""Persistent configuration stored in ~/.config/video-summarizer/config.json."""

import json
import os
from pathlib import Path

import click

CONFIG_DIR = Path.home() / ".config" / "video-summarizer"
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDERS = {
    "openai": {
        "label": "OpenAI (gpt-4o)",
        "model": "gpt-4o",
        "env_var": "OPENAI_API_KEY",
        "needs_key": True,
    },
    "anthropic": {
        "label": "Anthropic (claude-3-5-sonnet)",
        "model": "claude-3-5-sonnet",
        "env_var": "ANTHROPIC_API_KEY",
        "needs_key": True,
    },
    "ollama": {
        "label": "Ollama — local, free, no API key needed (ollama/llama3)",
        "model": "ollama/llama3",
        "env_var": None,
        "needs_key": False,
    },
}


def _load() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def _save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    CONFIG_FILE.chmod(0o600)  # keep API key private


def _prompt_setup() -> dict:
    """Interactive first-time (or change) setup. Returns config dict."""
    click.echo("\n⚙️  Let's set up your LLM provider.\n")

    choices = list(PROVIDERS.keys())
    for i, key in enumerate(choices, 1):
        click.echo(f"  {i}) {PROVIDERS[key]['label']}")

    while True:
        raw = click.prompt("\nPick a provider", default="1")
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                break
        except ValueError:
            pass
        click.echo("  Please enter a number from the list.")

    provider_key = choices[idx]
    provider = PROVIDERS[provider_key]

    api_key = None
    if provider["needs_key"]:
        api_key = click.prompt(
            f"\nEnter your {provider['env_var']}",
            hide_input=True,
            confirmation_prompt=False,
        )

    cfg = {
        "provider": provider_key,
        "model": provider["model"],
        "api_key": api_key,
        "env_var": provider["env_var"],
    }
    _save(cfg)
    click.echo(f"\n✅  Config saved to {CONFIG_FILE}\n")
    return cfg


def resolve(model_override: str | None) -> dict:
    """
    Return a dict with 'model' and 'api_key' (may be None for Ollama).
    Handles first-run setup and re-use prompts.
    If model_override is provided, skip interactive flow.
    """
    if model_override:
        # Explicit --model flag: use env var for key, skip prompts
        return {"model": model_override, "api_key": None, "env_var": None}

    cfg = _load()

    if cfg:
        provider_label = PROVIDERS.get(cfg.get("provider", ""), {}).get("label", cfg.get("model", "?"))
        click.echo(f"\n💾  Saved provider: {provider_label}")
        use_saved = click.confirm("    Use this provider?", default=True)
        if use_saved:
            return cfg
        cfg = _prompt_setup()
    else:
        cfg = _prompt_setup()

    return cfg
