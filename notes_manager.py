import re
import json
from datetime import datetime
from pathlib import Path

NOTES_DIR = Path("notes")
INDEX_FILE = NOTES_DIR / "index.json"
MODEL = "llama-3.3-70b-versatile"

NOTES_DIR.mkdir(exist_ok=True)

NOTE_PROMPT = """\
You are a note-taking assistant. Given a conversation, extract and structure the key ideas into a Markdown note.

Respond with YAML frontmatter followed by Markdown content, exactly in this format:

---
title: "A concise title"
date: {date}
tags: [tag1, tag2, tag3]
summary: "2-3 sentences capturing what was discussed. Must be one line."
---

## Key Ideas
- Key point 1
- Key point 2

## Open Questions
- Any unresolved threads worth returning to

Only include sections that have content. Be precise and concise. Do not invent anything not in the conversation.\
"""


def load_index() -> list:
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return []


def save_index(index: list):
    INDEX_FILE.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")[:50]


def parse_frontmatter(content: str) -> dict:
    """Extract fields from YAML frontmatter. Falls back to body sections."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    fm = {}

    if match:
        fm_text = match.group(1)
        for line in fm_text.splitlines():
            if not line.strip() or ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "tags":
                tags_match = re.match(r"\[(.+?)\]", val)
                fm["tags"] = (
                    [t.strip().strip("\"'") for t in tags_match.group(1).split(",")]
                    if tags_match
                    else []
                )
            else:
                fm[key] = val.strip("\"'")

    # Fallback: pull summary from ## Summary section if not in frontmatter
    if "summary" not in fm:
        summary_match = re.search(
            r"## Summary\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL
        )
        if summary_match:
            fm["summary"] = " ".join(summary_match.group(1).strip().split())[:300]

    return fm


def generate_note(messages: list, client) -> str:
    conversation = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in messages
    )
    today = datetime.now().strftime("%Y-%m-%d")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": NOTE_PROMPT.format(date=today)},
            {
                "role": "user",
                "content": f"Create a note from this conversation:\n\n{conversation}",
            },
        ],
    )
    return response.choices[0].message.content.strip()


def save_note(content: str) -> Path:
    fm = parse_frontmatter(content)
    title = fm.get("title", "untitled")
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    path = NOTES_DIR / f"{timestamp}-{slugify(title)}.md"
    path.write_text(content, encoding="utf-8")

    index = load_index()
    index.append(
        {
            "filename": path.name,
            "title": title,
            "date": fm.get("date", timestamp[:10]),
            "tags": fm.get("tags", []),
            "summary": fm.get("summary", ""),
            "access_count": 0,
            "last_accessed": None,
            "created_at": datetime.now().isoformat(),
        }
    )
    save_index(index)
    return path


def read_note(filename: str) -> str:
    path = NOTES_DIR / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rebuild_index():
    """Scan all .md files in notes/ and rebuild index.json, preserving access stats."""
    existing = {e["filename"]: e for e in load_index()}
    md_files = sorted(NOTES_DIR.glob("*.md"))
    index = []
    for path in md_files:
        content = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        prev = existing.get(path.name, {})
        index.append(
            {
                "filename": path.name,
                "title": fm.get("title", path.stem),
                "date": fm.get("date", ""),
                "tags": fm.get("tags", []),
                "summary": fm.get("summary", ""),
                "access_count": prev.get("access_count", 0),
                "last_accessed": prev.get("last_accessed", None),
                "created_at": prev.get(
                    "created_at",
                    datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
                ),
            }
        )
    save_index(index)
    return len(index)
