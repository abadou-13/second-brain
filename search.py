import re
import json
from datetime import datetime
from notes_manager import load_index, save_index, read_note

MODEL = "llama-3.3-70b-versatile"

# Matches questions and lookup-style messages
_QUESTION_WORDS = (
    "what", "when", "where", "who", "why", "how",
    "did i", "do i", "have i", "can you find", "remember",
    "recall", "show me", "tell me about", "what did i",
    "find my", "look up",
)

ROUTER_PROMPT = """\
You are a note retrieval router. Given a user query and a list of note summaries, \
identify which notes are relevant to the query.

Return ONLY a JSON array of relevant filenames. Example: ["note1.md", "note2.md"]
If no notes are relevant, return: []
Do not return anything else — no explanation, no markdown, just the JSON array.\
"""


def is_question(text: str) -> bool:
    t = text.strip().lower()
    return "?" in t or t.startswith(_QUESTION_WORDS)


def search_notes(query: str, client, top_k: int = 3) -> list:
    index = load_index()
    if not index:
        return []

    lines = []
    for entry in index:
        tags = ", ".join(entry.get("tags", []))
        summary = entry.get("summary") or "(no summary)"
        lines.append(
            f"- {entry['filename']} | {entry['title']} | tags: {tags} | {summary}"
        )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": ROUTER_PROMPT},
            {
                "role": "user",
                "content": f"Query: {query}\n\nNotes:\n" + "\n".join(lines),
            },
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    try:
        arr_match = re.search(r"\[.*?\]", raw, re.DOTALL)
        filenames = json.loads(arr_match.group(0)) if arr_match else []
    except Exception:
        return []

    now = datetime.now().isoformat()
    results = []
    updated = load_index()

    for filename in filenames[:top_k]:
        content = read_note(filename)
        if not content:
            continue
        entry = next((e for e in updated if e["filename"] == filename), {})
        results.append({
            "filename": filename,
            "title": entry.get("title", filename),
            "date": entry.get("date", ""),
            "content": content,
        })
        if entry:
            entry["access_count"] = entry.get("access_count", 0) + 1
            entry["last_accessed"] = now

    if results:
        save_index(updated)

    return results


def get_activity_summary(top_n: int = 5) -> str:
    index = load_index()
    if not index:
        return "No notes yet."

    recent = sorted(
        [e for e in index if e.get("last_accessed")],
        key=lambda e: e["last_accessed"],
        reverse=True,
    )[:top_n]

    frequent = sorted(
        [e for e in index if e.get("access_count", 0) > 0],
        key=lambda e: e["access_count"],
        reverse=True,
    )[:top_n]

    all_notes = sorted(index, key=lambda e: e.get("date", ""), reverse=True)[:top_n]

    lines = [f"You have {len(index)} note(s).\n"]

    lines.append("Recent notes:")
    for e in all_notes:
        lines.append(f"  {e['date']}  {e['title']}")

    if recent:
        lines.append("\nMost recently looked up:")
        for e in recent:
            lines.append(f"  {e['last_accessed'][:10]}  {e['title']}")

    if frequent:
        lines.append("\nMost revisited:")
        for e in frequent:
            lines.append(f"  {e['access_count']}x  {e['title']}")

    return "\n".join(lines)
