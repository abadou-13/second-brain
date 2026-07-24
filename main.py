import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def chat():
    messages = []  # this will hold the whole conversation history

    print("Second Brain — type 'exit' to quit\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            break

        # add the user's message to the conversation history
        messages.append({"role": "user", "content": user_input})

        # send the whole history so far to the model
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )

        reply = response.choices[0].message.content
        print(f"\nAssistant: {reply}\n")

        # add the assistant's reply to the history too, so it remembers
        messages.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    chat()