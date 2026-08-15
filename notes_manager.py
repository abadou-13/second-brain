import re
from datetime import datetime
from pathlib import Path
import vector_store

NOTES_DIR = Path("notes")
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


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")[:50]


def parse_frontmatter(content: str) -> dict:
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

    vector_store.add_note(
        filename=path.name,
        title=title,
        date=fm.get("date", timestamp[:10]),
        tags=fm.get("tags", []),
        summary=fm.get("summary", ""),
    )
    return path


def read_note(filename: str) -> str:
    path = NOTES_DIR / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rebuild_index() -> int:
    return vector_store.rebuild(NOTES_DIR, parse_frontmatter)
