"""CLI entrypoint."""

import sys
import tempfile
from pathlib import Path

import click

from .audio import extract_audio
from .transcribe import transcribe
from .summarize import summarize
from .writer import write_markdown


@click.command()
@click.argument("video", type=click.Path(exists=True, path_type=Path))
@click.option("--model", default="gpt-4o", show_default=True,
              help="LiteLLM-compatible model string for summarization.")
@click.option("--output", "output_dir", default=None, type=click.Path(path_type=Path),
              help="Output directory for the .md file. Defaults to the video's directory.")
@click.option("--transcriber", default="local", show_default=True,
              type=click.Choice(["local", "whisper-1", "gpt-realtime-whisper"], case_sensitive=False),
              help="Transcription backend to use.")
@click.option("--whisper-model", default="base", show_default=True,
              help="Local Whisper model size: tiny, base, small, medium, large. Ignored for cloud transcribers.")
@click.option("--no-cache", is_flag=True, default=False,
              help="Force re-transcription even if a cached transcript exists.")
def main(video: Path, model: str, output_dir: Path, transcriber: str, whisper_model: str, no_cache: bool) -> None:
    """Transcribe a local VIDEO file and write a Markdown summary."""
    output_dir = output_dir or video.parent

    click.echo(f"📹  Video:       {video}")
    click.echo(f"🎙️  Transcriber: {transcriber}" + (f" ({whisper_model})" if transcriber == "local" else ""))
    click.echo(f"🤖  Model:       {model}")
    click.echo(f"📂  Output:      {output_dir}")
    click.echo("")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            click.echo("🔊  Extracting audio…")
            audio = extract_audio(video, tmp)

            click.echo("📝  Transcribing…")
            result = transcribe(
                audio, video,
                whisper_model=whisper_model,
                transcriber=transcriber,
                no_cache=no_cache,
            )

            click.echo(f"🌐  Language detected: {result['language']}")
            click.echo("💬  Summarizing…")
            summary_md = summarize(result["text"], model=model)

            click.echo("📄  Writing Markdown…")
            md_file = write_markdown(
                video_path=video,
                output_path=output_dir,
                summary_md=summary_md,
                transcript=result["text"],
                language=result["language"],
                model=model,
            )

        click.echo(f"\n✅  Done! → {md_file}")

    except (ValueError, RuntimeError) as exc:
        click.echo(f"\n❌  Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"\n❌  Unexpected error: {exc}", err=True)
        sys.exit(1)
