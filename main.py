import os
from dotenv import load_dotenv
from groq import Groq
from notes_manager import generate_note, save_note, rebuild_index
from search import search_notes, get_activity_summary

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """\
You are a second brain assistant — a thinking partner that remembers what the user has worked through.

If relevant notes from past sessions are included below:
- Weave them into your response naturally, referring to them by title only \
(e.g. "You actually explored this when thinking about X..." or "In your note on Y, you touched on something similar").
- If the user is developing a new idea and it echoes something from a past note, say so proactively — \
don't wait to be asked. Surface the connection as if you simply remember it.
- Never mention filenames, file extensions, or dates.

If no notes are included:
- Just be a helpful thinking partner. Do not reference notes, memory, or past sessions at all.\
"""

COMMANDS = """\
Commands:
  exit    — end session (offers to save as note)
  recap   — show your note activity
  reindex — rebuild note index from files\
"""


def build_messages(history: list, relevant_notes: list = None) -> list:
    system = SYSTEM_PROMPT
    if relevant_notes:
        notes_block = "\n\n---\n\n".join(
            f"[Note title: {n['title']}]\n{n['content']}" for n in relevant_notes
        )
        system += f"\n\nRelevant notes from your knowledge base:\n\n{notes_block}"
    return [{"role": "system", "content": system}] + history


def chat():
    messages = []
    print("Second Brain\n")
    print(COMMANDS)
    print()

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd == "exit":
            if messages:
                answer = input("\nSave this session as a note? (y/n): ").strip().lower()
                if answer == "y":
                    print("Generating note…")
                    note = generate_note(messages, client)
                    path = save_note(note)
                    print(f"Saved → {path}\n")
            break

        if cmd == "recap":
            print("\n" + get_activity_summary() + "\n")
            continue

        if cmd == "reindex":
            n = rebuild_index()
            print(f"Index rebuilt — {n} note(s) indexed.\n")
            continue

        messages.append({"role": "user", "content": user_input})

        relevant = search_notes(user_input)

        response = client.chat.completions.create(
            model=MODEL,
            messages=build_messages(messages, relevant),
        )

        reply = response.choices[0].message.content
        print(f"\nAssistant: {reply}\n")

        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    chat()
