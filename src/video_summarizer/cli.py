"""CLI entrypoint."""

import sys
import tempfile
from pathlib import Path

import click

from .audio import extract_audio
from .transcribe import transcribe
from .summarize import summarize
from .writer import write_markdown
from .config import resolve as resolve_config
from .costs import (
    transcription_estimate, llm_estimate, format_cost, get_audio_duration,
    TRANSCRIPTION_COST_PER_MIN,
)
from .screenshots import extract_screenshots


@click.command()
@click.argument("video", type=click.Path(exists=True, path_type=Path))
@click.option("--model", default=None,
              help="LiteLLM model string (skips interactive provider setup).")
@click.option("--output", "output_dir", default=None, type=click.Path(path_type=Path),
              help="Output directory for the .md file. Defaults to the video's directory.")
@click.option("--transcriber", default="local", show_default=True,
              type=click.Choice(["local", "whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"], case_sensitive=False),
              help="Transcription backend to use.")
@click.option("--whisper-model", default="base", show_default=True,
              help="Local Whisper model size: tiny, base, small, medium, large. Ignored for cloud transcribers.")
@click.option("--no-cache", is_flag=True, default=False,
              help="Force re-transcription even if a cached transcript exists.")
@click.option("--screenshots", is_flag=True, default=False,
              help="Extract screenshots from the video and embed them in the summary.")
def main(video: Path, model: str | None, output_dir: Path, transcriber: str, whisper_model: str, no_cache: bool, screenshots: bool) -> None:
    """Transcribe a local VIDEO file and write a Markdown summary."""
    output_dir = output_dir or video.parent

    # Interactive provider/key setup (skipped if --model is passed explicitly)
    cfg = resolve_config(model)
    model = cfg["model"]
    api_key = cfg.get("api_key")

    click.echo(f"\n📹  Video:       {video}")
    click.echo(f"🎙️  Transcriber: {transcriber}" + (f" ({whisper_model})" if transcriber == "local" else ""))
    click.echo(f"🤖  Model:       {model}")
    click.echo(f"📂  Output:      {output_dir}")
    click.echo("")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            click.echo("🔊  Extracting audio…")
            audio = extract_audio(video, tmp)

            # --- Transcription cost estimate ---
            if transcriber != "local":
                duration_s = get_audio_duration(audio)
                duration_min, est_cost = transcription_estimate(duration_s, transcriber)
                click.echo(
                    f"\n💰  Transcription estimate: {duration_min:.1f} min audio "
                    f"→ {format_cost(est_cost)} ({transcriber})"
                )
                if not click.confirm("    Proceed?", default=True):
                    click.echo("Aborted.")
                    sys.exit(0)
                click.echo("")

            click.echo("📝  Transcribing…")
            result = transcribe(
                audio, video,
                whisper_model=whisper_model,
                transcriber=transcriber,
                no_cache=no_cache,
                api_key=api_key,
            )
            click.echo(f"🌐  Language detected: {result['language']}")

            # --- Summarization cost estimate ---
            est_tokens, est_llm_cost = llm_estimate(result["text"], model)
            click.echo(
                f"\n💰  Summarization estimate: ~{est_tokens:,} input tokens "
                f"→ {format_cost(est_llm_cost)} ({model})"
            )
            if not click.confirm("    Proceed?", default=True):
                click.echo("Aborted.")
                sys.exit(0)
            click.echo("")

            click.echo("💬  Summarizing…")
            summary_md, usage = summarize(result["text"], model=model, api_key=api_key)
            click.echo(
                f"📊  Tokens used: {usage['prompt_tokens']:,} in / "
                f"{usage['completion_tokens']:,} out  "
                f"({format_cost(usage['cost_usd'])})"
            )

            click.echo("📄  Writing Markdown…")
            screenshot_paths = None
            if screenshots:
                click.echo("📸  Extracting screenshots…")
                screenshot_paths = extract_screenshots(video, output_dir)
                click.echo(f"    {len(screenshot_paths)} screenshots saved → {output_dir / (video.stem + '_screenshots')}/")

            md_file = write_markdown(
                video_path=video,
                output_path=output_dir,
                summary_md=summary_md,
                transcript=result["text"],
                language=result["language"],
                model=model,
                screenshot_paths=screenshot_paths,
            )

        click.echo(f"\n✅  Done! → {md_file}")

    except (ValueError, RuntimeError) as exc:
        click.echo(f"\n❌  Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        # Surface 401 / auth errors clearly
        msg = str(exc)
        if "401" in msg or "invalid_api_key" in msg or "Incorrect API key" in msg:
            click.echo(
                "\n❌  Invalid API key. Run the command again and answer 'n' "
                "to re-enter your key.\n"
                "    Get a valid key at: https://platform.openai.com/api-keys",
                err=True,
            )
        else:
            click.echo(f"\n❌  Unexpected error: {exc}", err=True)
        sys.exit(1)
