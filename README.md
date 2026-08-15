# Second Brain

A local AI assistant that thinks with you, saves what you work through, and hands it back when it matters — across separate sessions with no shared history.

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

## Usage

Just talk. There's no mode to switch into — you can develop an idea, ask about something you explored before, or ask about your history, all in the same session.

```
You: I want to build an AI agent that helps with customer support
Assistant: [thinks with you, and surfaces any relevant past notes]

You: recap
[shows your note history — recent, most revisited]

You: exit
Save this session as a note? (y/n): y
Generating note…
Saved → notes/2026-08-15-1430-customer-support-agent.md
```

**Commands:**

| Command | What it does |
|---------|-------------|
| `exit` | End session. Offers to save as a Markdown note. |
| `recap` | Show recent notes, most revisited, last looked up. |
| `reindex` | Rebuild the note index from the `notes/` folder (useful after manual edits). |

## How notes are stored

Each note is a Markdown file in `notes/` with YAML frontmatter:

```markdown
---
title: "Customer Support AI"
date: 2026-08-15
tags: [AI, startup, customer support]
summary: "One or two sentences used for retrieval."
---

## Key Ideas
...

## Open Questions
...
```

A lightweight `notes/index.json` keeps titles, tags, and summaries so retrieval never reads all notes at once.
