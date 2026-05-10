# Video Summarizer

A Python CLI tool that transcribes a local video file using [OpenAI Whisper](https://github.com/openai/whisper) (runs fully offline) and generates a human-readable Markdown summary using any LLM supported by [LiteLLM](https://github.com/BerriAI/litellm).

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) installed on your system

Install ffmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

## Installation

```bash
git clone <repo-url>
cd video-summarizer

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -e .
```

## Usage

```bash
summarize <video_file> [OPTIONS]
```

### Examples

```bash
# Basic — uses gpt-4o, saves .md next to the video
summarize meeting.mp4

# Specify model and output directory
summarize lecture.mkv --model gpt-4o --output ./notes/

# Use Claude and a larger Whisper model for better accuracy
summarize interview.mov --model claude-3-5-sonnet --whisper-model medium

# Use OpenAI cloud transcription (faster startup, no local GPU needed)
summarize meeting.mp4 --transcriber whisper-1
summarize meeting.mp4 --transcriber gpt-realtime-whisper

# Force re-transcription (ignore cached transcript)
summarize meeting.mp4 --no-cache
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--model` | `gpt-4o` | LiteLLM-compatible model string (see below) |
| `--output` | Same dir as video | Directory where the `.md` file is saved |
| `--transcriber` | `local` | Transcription backend: `local`, `whisper-1`, `gpt-realtime-whisper` |
| `--whisper-model` | `base` | Local Whisper model size (ignored for cloud transcribers) |
| `--no-cache` | off | Force re-transcription even if a cache exists |

## Transcription Backends

| `--transcriber` | Runs | Cost | Best for |
|---|---|---|---|
| `local` (default) | On your machine | Free | Privacy, no internet, large files |
| `whisper-1` | OpenAI API | $0.006/min | Fast startup, low-spec machines |
| `gpt-realtime-whisper` | OpenAI API | $0.017/min | Highest cloud accuracy |

Cloud transcribers require `OPENAI_API_KEY`. The `--whisper-model` flag is ignored when using a cloud transcriber.

## LLM Models

Set the relevant API key as an environment variable, then pass the model name via `--model`.

| Provider | Env var | Example `--model` value |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4-turbo` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet`, `claude-3-opus` |
| Ollama (local) | _(none)_ | `ollama/llama3` |

```bash
export OPENAI_API_KEY=sk-...
summarize video.mp4 --model gpt-4o
```

## Output

The tool writes a single Markdown file named `<video_filename>.md`:

```markdown
# Summary: meeting.mp4

**Date processed:** 2026-05-10
**Duration:** 00:45:12
**Language detected:** en
**Model used:** gpt-4o

---

## TL;DR
...

## Key Points
- ...

## Topics Covered
- ...

---

## Full Transcript
...
```

## Caching

Transcripts are cached alongside the video as `.<filename>.transcript.json`. On subsequent runs the transcription step is skipped, making re-summarization with a different model fast. Use `--no-cache` to force a fresh transcription.

## Whisper Model Sizes

| Model | Speed | Accuracy | VRAM |
|---|---|---|---|
| `tiny` | fastest | lowest | ~1 GB |
| `base` | fast | good | ~1 GB |
| `small` | moderate | better | ~2 GB |
| `medium` | slow | great | ~5 GB |
| `large` | slowest | best | ~10 GB |

`base` is the default and works well for most content.
