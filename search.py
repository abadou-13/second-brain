import vector_store
from notes_manager import read_note


def search_notes(query: str, top_k: int = 3) -> list:
    hits = vector_store.search(query, top_k=top_k)
    results = []
    for hit in hits:
        content = read_note(hit["filename"])
        if not content:
            continue
        results.append({
            "filename": hit["filename"],
            "title": hit["title"],
            "date": hit["date"],
            "content": content,
        })
        vector_store.update_access(hit["filename"])
    return results


def get_activity_summary(top_n: int = 5) -> str:
    all_meta = vector_store.get_all_metadata()
    if not all_meta:
        return "No notes yet."

    all_notes = sorted(all_meta, key=lambda e: e.get("date", ""), reverse=True)[:top_n]

    recent = sorted(
        [m for m in all_meta if m.get("last_accessed")],
        key=lambda m: m["last_accessed"],
        reverse=True,
    )[:top_n]

    frequent = sorted(
        [m for m in all_meta if int(m.get("access_count", 0)) > 0],
        key=lambda m: int(m.get("access_count", 0)),
        reverse=True,
    )[:top_n]

    lines = [f"You have {len(all_meta)} note(s).\n"]

    lines.append("Recent notes:")
    for e in all_notes:
        lines.append(f"  {e.get('date', '')}  {e.get('title', '')}")

    if recent:
        lines.append("\nMost recently looked up:")
        for e in recent:
            lines.append(f"  {e['last_accessed'][:10]}  {e.get('title', '')}")

    if frequent:
        lines.append("\nMost revisited:")
        for e in frequent:
            lines.append(f"  {int(e.get('access_count', 0))}x  {e.get('title', '')}")

    return "\n".join(lines)
