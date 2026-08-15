# Design

## Architecture

Four modules, one flat file store, one vector database.

```
main.py           — chat loop, commands, message assembly
notes_manager.py  — note generation (LLM), saving, frontmatter parsing
search.py         — retrieval, activity tracking
vector_store.py   — ChromaDB wrapper (embeddings, similarity search, metadata)

notes/
  *.md            — Markdown notes, one per session (source of truth)

chroma_db/        — ChromaDB persistent store (regenerable from notes/)
  chroma.sqlite3  — metadata: title, date, tags, access stats
  <uuid>/         — HNSW vector index (binary, not human-readable)
```

The chat loop is stateless between sessions — only `notes/` and `chroma_db/` persist. A new session starts with no conversation history.

If `chroma_db/` is ever deleted, running `reindex` rebuilds it from the Markdown files. The Markdown files are the source of truth; ChromaDB is the search index built on top of them.

---

## Storage: what gets saved and why

Each saved note has two representations:

**The Markdown file** (`notes/*.md`) — the full thinking, structured into Key Ideas and Open Questions with YAML frontmatter (title, date, tags, summary). Human-readable, portable, permanent.

**A ChromaDB entry** — the summary text is embedded into a vector using `all-MiniLM-L6-v2` (local ONNX model, no API call). The vector is stored in the HNSW index for fast similarity search. Metadata (title, date, tags, access counts) goes into `chroma.sqlite3`.

The summary is the critical seam: it's what gets embedded and searched against. If the summary misses a key concept from the session, that note becomes harder to find. The LLM generates it at save time from the full conversation.

---

## Retrieval: how it works

Every user message triggers a two-step pipeline:

**Step 1 — Vector search**: The query is embedded locally (same `all-MiniLM-L6-v2` model). ChromaDB computes cosine distance against all stored note vectors using HNSW and returns the top-k matches. Results above distance 1.2 are filtered out — anything that far from the query is not a real match.

**Step 2 — Answer**: The matched notes (full Markdown content, read from `notes/`) are injected into the system prompt. The assistant is instructed to surface connections proactively — if the user is mid-thought on something new and a past note echoes it, it says so without being asked.

When Step 1 returns nothing, Step 2 proceeds with no injected notes and the assistant responds as a normal thinking partner.

### Why ChromaDB over an LLM router

The first version used an LLM call to route: send all summaries, ask which ones are relevant, parse the returned filenames. It worked for 3 notes. At 1000 notes it would send ~60,000 words to the API — past most context windows, expensive, slow, and increasingly inaccurate as the list grows.

ChromaDB with local embeddings scales differently:
- Search time at 1000 notes: ~700ms (same as at 10 notes)
- No API call for search — fully local
- No context window ceiling
- Distance threshold means "no match" is an honest answer, not a hallucination

The 700ms is the ONNX embedding inference time for the query. It's constant regardless of note count.

---

## Scale test results

Tested with 1000 notes (3 real + 997 synthetic):

| Query | Result | Time |
|---|---|---|
| "AI customer support startup in France" | Conversational AI note (distance 0.69) | 775ms |
| "how to join a football club" | Football Club note (distance 0.64) | 685ms |
| "import export company Africa" | SARL Company note (distance 0.94) | 700ms |
| "best pizza recipe" | No match (0 results) | 648ms |

Accuracy: correct note returned in every case, unrelated notes filtered out by the distance threshold.

---

## The proactive surfacing foothold

The spec's stretch goal: a system that surfaces past thinking mid-thought, before you think to look. We get a real foothold:

- Search runs on **every message**, not just explicit questions.
- The system prompt explicitly instructs the model to proactively mention when the user's current thinking echoes a past note — not just when asked.

This means if you start talking about an idea you explored before, the relevant note gets injected and the model surfaces the connection naturally.

---

## How I know it works

- Distance threshold 1.2 was calibrated on real data: relevant notes score 0.64–0.94, clearly unrelated notes score 1.69+. The gap is large enough for a stable cut.
- "No match" queries correctly return empty rather than a closest-match guess.
- Access counts and `last_accessed` update on every retrieval and persist across sessions.
- `reindex` rebuilds ChromaDB from scratch from the Markdown files, preserving access stats.

---

## Decisions and trade-offs

**Always search vs. search on questions only**

An earlier version only searched when the message contained `?` or started with a question word. This missed the case where a user states something ("I want to build an AI startup about customer support") without phrasing it as a question. Switching to always-search fixed this at the cost of one embedding call per message (~700ms locally, no API cost).

**Local embeddings vs. API embeddings**

ChromaDB's default embedding uses `all-MiniLM-L6-v2` via ONNX — runs locally, no API key, ~90MB one-time download. The alternative was calling an embedding API (OpenAI, Cohere) which would add latency, cost per search, and a second dependency on an external service. Local wins for a personal tool.

**LLM-generated summary vs. user-written**

The summary is generated at save time from the full conversation. Quality of retrieval depends on summary quality. A user who writes a long, meandering session may get a summary that doesn't capture every thread. User-written summaries would be more precise but break the seamless UX. A middle ground — showing the generated summary and letting the user edit before saving — would be the next improvement.

**Flat files for notes**

Notes are plain Markdown. No database for the note content itself. This keeps notes human-readable, portable (copy them anywhere), and recoverable (ChromaDB can always be rebuilt from them). The trade-off is that concurrent writes would corrupt things — acceptable for a single-user local tool.

---

## Where it breaks first

**Long sessions**: The full conversation history is sent on every turn. A very long session will eventually exceed the model's context window. Fix: sliding window or periodic conversation summarization.

**Summary quality**: Retrieval is only as good as the summary. No current mechanism to detect or fix a bad summary after it's saved.

**Distance threshold**: 1.2 was calibrated on a small set of notes. As the note collection grows and topics diversify, some edge cases may need threshold tuning. A note that's somewhat related might land just above 1.2 and get filtered.

**Single-user**: No auth, no isolation. Files are shared on the local machine.

## What I wouldn't trust it with

- High-stakes recall (legal, medical, financial) — it might miss a note if the summary doesn't capture the right concept
- Exact verbatim retrieval — summaries lose detail by design
- Multi-user deployments without adding auth and per-user storage isolation
