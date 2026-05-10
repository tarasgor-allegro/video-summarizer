"""Persistent configuration stored in ~/.config/video-summarizer/config.json.

API keys are stored in the system keychain (macOS Keychain, Windows Credential
Manager, Linux Secret Service) via the `keyring` library — never written to disk
as plain text.
"""

import json
from pathlib import Path

import click
import keyring

KEYRING_SERVICE = "video-summarizer"
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


def _load_meta() -> dict:
    """Load non-sensitive config (provider, model) from disk."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_meta(cfg: dict) -> None:
    """Save non-sensitive config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    safe = {k: v for k, v in cfg.items() if k != "api_key"}
    with open(CONFIG_FILE, "w") as f:
        json.dump(safe, f, indent=2)


def _save_key(provider: str, api_key: str) -> None:
    keyring.set_password(KEYRING_SERVICE, provider, api_key)


def _load_key(provider: str) -> str | None:
    return keyring.get_password(KEYRING_SERVICE, provider)


def _delete_key(provider: str) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, provider)
    except keyring.errors.PasswordDeleteError:
        pass


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

    if provider["needs_key"]:
        api_key = click.prompt(
            f"\nEnter your {provider['env_var']}",
            hide_input=True,
            confirmation_prompt=False,
        )
        _save_key(provider_key, api_key)
        click.echo("🔐  API key stored in system keychain.")
    else:
        api_key = None

    cfg = {
        "provider": provider_key,
        "model": provider["model"],
        "env_var": provider["env_var"],
    }
    _save_meta(cfg)
    click.echo(f"✅  Config saved to {CONFIG_FILE}\n")
    return {**cfg, "api_key": api_key}


def resolve(model_override: str | None) -> dict:
    """
    Return a dict with 'model' and 'api_key' (may be None for Ollama).
    Handles first-run setup and re-use prompts.
    If model_override is provided, skip interactive flow.
    """
    if model_override:
        return {"model": model_override, "api_key": None, "env_var": None}

    meta = _load_meta()

    if meta:
        provider_label = PROVIDERS.get(meta.get("provider", ""), {}).get("label", meta.get("model", "?"))
        click.echo(f"\n💾  Saved provider: {provider_label}")
        use_saved = click.confirm("    Use this provider?", default=True)
        if use_saved:
            api_key = _load_key(meta["provider"]) if meta.get("provider") else None
            return {**meta, "api_key": api_key}
        # User wants to switch — clean up old key
        if meta.get("provider"):
            _delete_key(meta["provider"])

    cfg = _prompt_setup()
    return cfg
