# Video Summarizer — Product Requirements Document

## Overview

A Python CLI tool that takes a local video file, transcribes it using local OpenAI Whisper, and generates a human-readable Markdown summary using a configurable LLM. The output is a single `.md` file containing a structured summary and the full transcript — ready to be used as context for further Q&A with an AI assistant.

---

## Goals

- Turn any local video into a readable, referenceable Markdown document
- Work fully offline for transcription (no API cost for audio-to-text)
- Support multiple LLMs for summarization via a single `--model` flag
- Be fast on repeat runs by caching transcripts

---

## Non-Goals

- No YouTube or URL download support
- No web UI
- No real-time / streaming transcription
- No speaker diarization (who said what)

---

## CLI Interface

```bash
# Basic usage
summarize <video_file> [OPTIONS]

# Examples
summarize meeting.mp4
summarize lecture.mkv --model gpt-4o --output ./notes/
summarize interview.mov --model claude-3-5-sonnet --whisper-model medium
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--model` | `gpt-4o` | LLM used for summarization (any LiteLLM-compatible model string) |
| `--output` | Same dir as input | Directory or full path for the output `.md` file |
| `--whisper-model` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `--no-cache` | `false` | Force re-transcription even if cache exists |

---

## Output Format

Output file is named `<video_filename>.md` (e.g. `meeting.mp4.md`).

```markdown
# Summary: <video filename>

**Date processed:** YYYY-MM-DD  
**Duration:** HH:MM:SS  
**Language detected:** English  
**Model used:** gpt-4o  

---

## TL;DR

<2–4 sentence high-level summary>

## Key Points

- ...
- ...
- ...

## Topics Covered

- Topic A
- Topic B

---

## Full Transcript

<complete transcript text>
```

---

## Architecture

```
video file
    │
    ▼
[ffmpeg]  ──► extract audio (wav/mp3)
    │
    ▼
[Whisper (local)]  ──► raw transcript text  ──► cache (.txt)
    │
    ▼
[LiteLLM]  ──► summarization prompt  ──► structured summary
    │
    ▼
[Markdown writer]  ──► <filename>.md
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `openai-whisper` | Local speech-to-text |
| `ffmpeg` (system) | Audio extraction from video |
| `litellm` | Unified interface to GPT-4o, Claude, Ollama, etc. |
| `click` | CLI argument parsing |

---

## Caching

- Transcript cache stored alongside the video as `.<filename>.transcript.txt`
- Cache is skipped if `--no-cache` flag is passed
- Cache is invalidated if the source file's modification time changes

---

## Language Handling

- Whisper auto-detects the spoken language
- The summarization prompt always instructs the LLM to respond in English
- The detected language is noted in the output markdown header

---

## Error Handling

- Missing `ffmpeg` → clear error message with install instructions
- Unsupported video format → list supported formats
- LLM API key missing → prompt user to set the relevant env var
- Whisper model not downloaded → auto-download on first use (Whisper default behavior)
