"""Assemble the final Markdown document."""

from datetime import date
from pathlib import Path


def format_duration(video_path: Path) -> str:
    """Return HH:MM:SS duration using ffprobe."""
    import subprocess, json

    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
        seconds = float(data["format"]["duration"])
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return "unknown"


def write_markdown(
    video_path: Path,
    output_path: Path,
    summary_md: str,
    transcript: str,
    language: str,
    model: str,
    screenshot_paths: list[Path] | None = None,
) -> Path:
    """Write the final .md file and return its path."""
    duration = format_duration(video_path)
    today = date.today().isoformat()

    screenshots_section = ""
    if screenshot_paths:
        lines = ["## Screenshots\n"]
        for p in screenshot_paths:
            # Use path relative to the markdown file so images work portably
            try:
                rel = p.relative_to(output_path)
            except ValueError:
                rel = p
            ts_sec = int(p.stem.split("_")[-1].rstrip("s"))
            h, m, s = ts_sec // 3600, (ts_sec % 3600) // 60, ts_sec % 60
            label = f"{h:02d}:{m:02d}:{s:02d}"
            lines.append(f"![{label}]({rel})\n")
        screenshots_section = "\n" + "\n".join(lines) + "\n---\n"

    content = f"""# Summary: {video_path.name}

**Date processed:** {today}  
**Duration:** {duration}  
**Language detected:** {language}  
**Model used:** {model}  

---

{summary_md}

---
{screenshots_section}
## Full Transcript

{transcript}
"""

    md_file = output_path / f"{video_path.name}.md"
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file
