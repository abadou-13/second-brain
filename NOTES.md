# Notes

## What I didn't get to

**Embedding-based retrieval**: The LLM router scales to ~300-500 notes before the summary list overflows context. Beyond that, the right fix is a local embedding model (e.g. `all-MiniLM-L6-v2` via `sentence-transformers`) to pre-filter candidates before the LLM router call. Skipped because it adds PyTorch as a dependency (~1GB download) and the LLM router is already semantically strong for the realistic note pile size.

**Conversation summarization**: Long sessions send the full message history on every turn. A sliding window or periodic summarization (compress old turns into a running summary) would keep the context bounded. Not done — sessions are naturally bounded in practice.

**Note editing**: There's no way to update a note after it's saved. You'd have to edit the Markdown file manually and run `reindex`. A simple "edit last note" command would help.

**Chunking long notes**: A very long session produces a very long note. When that note is matched and injected into context, it can consume a large chunk of the answer call's context window. Chunking notes and only injecting the most relevant chunk (e.g. matching section) would help.

**GUI / TUI**: The interface is a terminal readline loop. Works, but a TUI (e.g. `textual`) would make the experience noticeably better — streaming responses, visible note matches, a sidebar for recent notes.

## What I'd improve with more time

- Pre-filter with BM25 before the LLM router to extend the note pile limit
- Stream the assistant's response token-by-token instead of waiting for the full reply
- Show which note(s) were matched at the end of each response (opt-in, for transparency)
- Let the user confirm or edit the generated note before saving
- Detect when the user is asking about their activity inside normal conversation ("what have I been thinking about lately?") rather than requiring the `recap` command
