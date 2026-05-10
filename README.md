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

## First run — interactive setup

The first time you run `summarize`, it walks you through picking an LLM provider and entering your API key:

```
⚙️  Let's set up your LLM provider.

  1) OpenAI (gpt-4o)
  2) Anthropic (claude-3-5-sonnet)
  3) Ollama — local, free, no API key needed (ollama/llama3)

Pick a provider [1]: 1

Enter your OPENAI_API_KEY: ****
🔐  API key stored in system keychain.
✅  Config saved to ~/.config/video-summarizer/config.json
```

Your API key is stored in the **system keychain** (macOS Keychain, Windows Credential Manager, Linux Secret Service) — never written to disk as plain text.

## Subsequent runs

On every run after setup, you're asked whether to reuse your saved provider:

```
💾  Saved provider: OpenAI (gpt-4o)
    Use this provider? [Y/n]:
```

Press **Enter** to continue, or **n** to switch to a different provider.

## Usage

```bash
summarize <video_file> [OPTIONS]
```

### Examples

```bash
# Basic — interactive provider prompt, saves .md next to the video
summarize meeting.mp4

# Save output to a specific directory
summarize meeting.mp4 --output ./notes/

# Use a cloud transcriber for faster startup (no local model download)
summarize meeting.mp4 --transcriber gpt-realtime-whisper

# Use a larger local Whisper model for better accuracy
summarize lecture.mkv --whisper-model medium

# Skip the provider prompt (useful for scripting)
summarize meeting.mp4 --model gpt-4o

# Force re-transcription, ignoring cached transcript
summarize meeting.mp4 --no-cache
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--model` | _(interactive)_ | LiteLLM model string — bypasses provider prompt entirely |
| `--output` | Same dir as video | Directory where the `.md` file is saved |
| `--transcriber` | `local` | Transcription backend: `local`, `whisper-1`, `gpt-realtime-whisper` |
| `--whisper-model` | `base` | Local Whisper model size (ignored for cloud transcribers) |
| `--no-cache` | off | Force re-transcription even if a cached transcript exists |

## Transcription Backends

| `--transcriber` | Runs | Cost | Best for |
|---|---|---|---|
| `local` (default) | On your machine | Free | Privacy, no internet, large files |
| `whisper-1` | OpenAI API | $0.006/min | Fast startup, low-spec machines |
| `gpt-realtime-whisper` | OpenAI API | $0.017/min | Highest cloud accuracy |

Cloud transcribers use your saved `OPENAI_API_KEY`. The `--whisper-model` flag is ignored when using a cloud transcriber.

## LLM Providers

| Provider | API key needed | Models |
|---|---|---|
| OpenAI | Yes | `gpt-4o`, `gpt-4-turbo`, … |
| Anthropic | Yes | `claude-3-5-sonnet`, `claude-3-opus`, … |
| Ollama | No (runs locally) | `ollama/llama3`, `ollama/mistral`, … |

When using `--model` directly (scripting mode), set the API key as an environment variable:

```bash
export OPENAI_API_KEY=sk-...
summarize meeting.mp4 --model gpt-4o
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

