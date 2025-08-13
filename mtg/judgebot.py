import discord
import os
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Load environment variables from .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging setup (optional)
logging.basicConfig(level=logging.INFO)

# OpenAI client (new SDK format)
client_ai = OpenAI(api_key=OPENAI_API_KEY)

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Template for Magic rules questions
def generate_prompt(user_question):
    return f"""
You are a professional Magic: The Gathering rules judge AI. A player has asked the following question:

\"{user_question}\"

Answer the question clearly and accurately using the official Magic: The Gathering Comprehensive Rules. Be sure to:
1. Break down the steps involved.
2. Use accurate game terminology.
3. **Cite specific rule numbers** from the Comprehensive Rules to support your ruling.
4. Only include information that is relevant to answering the question.

Respond in a helpful tone suitable for experienced players.
"""

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!judge"):
        question = message.content[len("!judge"):].strip()
        if not question:
            await message.channel.send("Please provide a rules question after the command.")
            return

        prompt = generate_prompt(question)

        try:
            response = client_ai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert MTG rules judge."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            answer = response.choices[0].message.content
            await message.channel.send(answer)

        except Exception as e:
            await message.channel.send(f"❌ Error getting ruling: {e}")
            print(f"Error: {e}")

client.run(DISCORD_TOKEN)
