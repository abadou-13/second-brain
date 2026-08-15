import chromadb
from pathlib import Path
from datetime import datetime

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "notes"


def _client():
    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_collection():
    return _client().get_or_create_collection(name=COLLECTION_NAME)


def add_note(filename: str, title: str, date: str, tags: list, summary: str):
    if not summary.strip():
        return
    get_collection().upsert(
        ids=[filename],
        documents=[summary],
        metadatas=[{
            "filename": filename,
            "title": title,
            "date": date,
            "tags": ",".join(tags),
            "access_count": 0,
            "last_accessed": "",
        }],
    )


def search(query: str, top_k: int = 3, max_distance: float = 1.2) -> list:
    col = get_collection()
    count = col.count()
    if count == 0:
        return []
    results = col.query(
        query_texts=[query],
        n_results=min(top_k, count),
        include=["metadatas", "distances"],
    )
    hits = []
    for i, filename in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        if distance > max_distance:
            continue
        meta = results["metadatas"][0][i]
        hits.append({
            "filename": filename,
            "title": meta.get("title", filename),
            "date": meta.get("date", ""),
            "distance": distance,
        })
    return hits


def update_access(filename: str):
    col = get_collection()
    result = col.get(ids=[filename], include=["metadatas", "documents"])
    if not result["ids"]:
        return
    meta = dict(result["metadatas"][0])
    meta["access_count"] = int(meta.get("access_count", 0)) + 1
    meta["last_accessed"] = datetime.now().isoformat()
    col.update(ids=[filename], metadatas=[meta])


def get_all_metadata() -> list:
    col = get_collection()
    if col.count() == 0:
        return []
    return col.get(include=["metadatas"])["metadatas"]


def rebuild(notes_dir: Path, parse_frontmatter_fn) -> int:
    col = get_collection()

    # Preserve existing access stats before wiping
    existing = col.get(include=["metadatas"])
    stats = {
        m["filename"]: m
        for m in existing["metadatas"]
    } if existing["ids"] else {}

    if existing["ids"]:
        col.delete(ids=existing["ids"])

    md_files = sorted(notes_dir.glob("*.md"))
    added = 0
    for path in md_files:
        content = path.read_text(encoding="utf-8")
        fm = parse_frontmatter_fn(content)
        summary = fm.get("summary", "")
        if not summary.strip():
            continue
        prev = stats.get(path.name, {})
        col.add(
            ids=[path.name],
            documents=[summary],
            metadatas=[{
                "filename": path.name,
                "title": fm.get("title", path.stem),
                "date": fm.get("date", ""),
                "tags": ",".join(fm.get("tags", [])),
                "access_count": int(prev.get("access_count", 0)),
                "last_accessed": prev.get("last_accessed", ""),
            }],
        )
        added += 1
    return added
