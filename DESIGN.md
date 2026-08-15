# Design

## Architecture

Three modules, one flat file store.

```
main.py          — chat loop, commands, message assembly
notes_manager.py — note generation (LLM), saving, index I/O
search.py        — LLM-router retrieval, activity tracking

notes/
  *.md           — Markdown notes (source of truth)
  index.json     — lightweight index: title, tags, summary, access stats
```

The chat loop is stateless between sessions by design — only `notes/` persists. A new session starts with no conversation history, only the index.

---

## Storage: what gets saved and why

Each saved note has two representations:

1. **The full Markdown file** — the actual thinking, structured into Key Ideas and Open Questions. Human-readable. Never touched during retrieval unless a note is matched.

2. **An index entry** — title, date, tags, and a 2-3 sentence summary in `index.json`. This is what retrieval reads. The summary is LLM-generated at save time from the same conversation.

This split is the core bet: the summary has to be good enough to find the note later. If the summary misses the key concept, the note becomes unreachable. That's a real limitation (see below), but it also means retrieval is fast and context-bounded regardless of how many notes pile up — we never load full notes at search time.

---

## Retrieval: how it works

Every user message triggers a two-call retrieval pipeline:

**Call 1 — Router**: All summaries from `index.json` are sent to a fast LLM call with a strict prompt: return only a JSON array of relevant filenames, nothing else. Temperature is set to 0 for determinism.

**Call 2 — Answer**: The matched notes (full content) are injected into the system prompt for the actual response. The assistant is instructed to surface connections proactively — if you're mid-thought on something new and a past note echoes it, it says so without being asked.

When the router returns `[]`, the second call proceeds with no injected notes and the assistant responds as a normal thinking partner.

### Why LLM router instead of embeddings

Embeddings would be more scalable (see limits below), but they require either a large local model (PyTorch, ~1GB+) or a separate API provider. The LLM router gives semantic matching without any extra dependencies, handles vague "gist" queries well, and is easy to inspect — you can read the prompt and understand exactly what it's doing. The trade-off is an extra API call per message and a ceiling on how many notes can fit in the router's context.

---

## The proactive surfacing foothold

The spec's stretch goal is a system that doesn't wait to be asked — it surfaces past thinking mid-thought on something new. We get a real foothold here:

- Search runs on **every message**, not just explicit questions.
- The system prompt explicitly instructs the model to say so when the user's current thinking echoes a past note, without being prompted.

This means if you start talking about an idea you explored a month ago, the relevant note is injected and the model will surface the connection naturally in its response.

---

## How I know it works

- The router's `temperature=0` makes it deterministic: given the same query and the same index, it returns the same filenames.
- Exact-phrase and title queries reliably return the right note.
- Vague/gist queries work because the router is a full LLM, not a keyword matcher — tested with paraphrases that share no vocabulary with the note title.
- When nothing matches, the router returns `[]` and the assistant responds without inventing past notes.
- Access counts and `last_accessed` update on every retrieval and persist across sessions.

---

## Decisions and trade-offs

**Always search vs. search on questions only**

An earlier version only searched when the message contained a `?` or started with a question word. This missed the case where a user states something ("I want to build an AI startup about customer support") without phrasing it as a question. Switching to always-search fixed this. The cost is one extra API call per message, which is acceptable for a personal tool.

**LLM-generated summary vs. user-written summary**

The summary is generated at save time from the conversation. This means the quality of retrieval depends on the quality of the summary. A user who writes a long, meandering session may get a summary that doesn't capture every thread. The alternative — letting the user write their own summary — would be more precise but breaks the seamless "just talk" UX.

**Flat files vs. a database**

Notes are plain Markdown files. The index is a JSON file. No SQLite, no vector database, no migration scripts. This keeps setup to `pip install -r requirements.txt` and makes the notes human-readable and portable. The trade-off is that concurrent writes would corrupt the index, but this is a single-user local tool.

---

## Where it breaks first

**Note count ~300-500**: The router sends all summaries in one context window. At ~300 notes (roughly 30k tokens of summaries), this approaches the model's limit. Fix: add a BM25 or embedding pre-filter to cut the candidate set before the LLM router call.

**Long sessions**: The full conversation history is sent on every turn. A 2-hour session with hundreds of exchanges will eventually exceed context. Fix: sliding window or periodic conversation summarization.

**Summary quality**: Retrieval is only as good as the summary. A poor summary (too vague, missing key terms) makes a note effectively unreachable. No current mechanism to detect or fix bad summaries after the fact.

**Router hallucination**: Rare, but the LLM could return a filename that doesn't exist. Handled gracefully — `read_note` returns empty string and the result is skipped — but the retrieval silently fails.

## What I wouldn't trust it with

- Note piles above ~300 entries without adding embeddings
- High-stakes recall (legal, medical, financial) — it might miss a note
- Anything requiring exact verbatim retrieval — summaries lose detail by design
