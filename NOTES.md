# Notes

## What I didn't get to

**Web or TUI interface**: The interface is a terminal readline loop. A Streamlit app or a TUI (e.g. `textual`) would make the experience significantly better — streaming responses, visible note matches, a sidebar for recent notes. Skipped to keep scope tight; the spec says interface is not evaluated.

**Streaming responses**: The assistant's reply arrives all at once after the full API call completes. Token-by-token streaming would make long responses feel much more responsive.

**Note editing**: No way to update a note after it's saved. You'd edit the Markdown file manually and run `reindex`. A "edit last note" command would cover the common case.

**Summary quality feedback**: Retrieval quality depends entirely on the LLM-generated summary. There's no mechanism to detect a weak summary or let the user improve it before saving. Showing the draft summary and asking for confirmation before saving would help.

**Chunking long notes**: A very long session produces a long note. When that note is matched and injected into context, it can consume a large portion of the answer call's context window. Chunking notes and injecting only the most relevant section would help.

**Conversation summarization for long sessions**: The full message history is sent on every turn. A sliding window or periodic summarization of older turns would keep context bounded for multi-hour sessions.

**Distance threshold tuning**: The 1.2 cosine distance cutoff was calibrated on a small note set. It works well, but as the collection grows and topics diversify, some edge cases near the threshold may need manual tuning or an adaptive approach.

## What I'd improve with more time

- Embed at a chunk level, not just summary level — index individual paragraphs so long notes can be partially matched
- Show which note(s) were retrieved at the end of each response (opt-in, for transparency and debugging)
- Detect activity queries ("what have I been thinking about lately?") inside normal conversation rather than requiring the `recap` command
- Add a `delete` command to remove a note from both the filesystem and the vector index
- Auto-reindex on startup if new `.md` files are detected that aren't in ChromaDB yet
