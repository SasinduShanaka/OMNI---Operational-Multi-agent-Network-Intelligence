import os
from dotenv import load_dotenv
from groq import Groq


# Load backend/.env
load_dotenv()


# Create Groq client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# Send a simple test request
response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Say hello and explain in one sentence what an Operations Agent does."
        }
    ],
)


print("\nGroq response:")
print(response.choices[0].message.content)