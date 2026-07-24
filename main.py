import os
from dotenv import load_dotenv
from groq import Groq

# Load the .env file so we can read the API key
load_dotenv()

# Create the client, authenticated with your key
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Send one message and get a response back
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "Say hello and confirm you're working."}
    ]
)

# Print just the text of the reply
print(response.choices[0].message.content)