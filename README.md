# Second Brain

A local AI assistant that thinks with you, saves what you work through, and hands it back when it matters — across separate sessions with no shared history.

## How it works

You talk through an idea. At the end, it summarizes the conversation into a structured Markdown note and files it away. In later sessions, with none of the old chat in context, it finds the relevant notes and answers from them — or tells you honestly when it has nothing.

## Setup

**Requirements:** Python 3.9+, a Groq API key.

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd second-brain

# 2. Create and activate a virtual environment
python -m venv brainenv

# Windows:
brainenv\Scripts\activate
# macOS/Linux:
source brainenv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Groq API key
echo GROQ_API_KEY=your_key_here > .env

# 5. Run
python main.py
```

On first run, ChromaDB will download the embedding model (~90MB, one time only).

## Usage

Just talk. No mode to switch into — developing an idea, asking about something you explored before, and checking your history all work in the same session.

```
You: I've been thinking about building an AI tool for customer support
Assistant: [thinks with you — surfaces any relevant past notes automatically]

You: recap
[shows your note history: recent, most revisited, last looked up]

You: exit
Save this session as a note? (y/n): y
Generating note…
Saved → notes/2026-08-15-1430-customer-support-ai.md
```

**Commands:**

| Command | What it does |
|---------|-------------|
| `exit` | End session. Offers to save as a Markdown note. |
| `recap` | Show recent notes, most revisited, last looked up. |
| `reindex` | Rebuild the vector index from the `notes/` folder. |

## What gets stored

```
notes/
  2026-08-15-1430-customer-support-ai.md   ← full note, human-readable
  ...

chroma_db/                                  ← vector index (auto-managed)
  chroma.sqlite3                            ← metadata + access stats
  <uuid>/                                   ← HNSW embedding index
```

Each note is a Markdown file with YAML frontmatter:

```markdown
---
title: "Customer Support AI"
date: 2026-08-15
tags: [AI, startup, customer support]
summary: "One or two sentences used for semantic search."
---

## Key Ideas
...

## Open Questions
...
```

`chroma_db/` is regenerable — if you delete it, run `reindex` and it rebuilds from your Markdown files. The `notes/` folder is the source of truth; never delete it.
