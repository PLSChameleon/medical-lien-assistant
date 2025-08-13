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

# Memory store for recent user interactions
conversation_history = {}

# Template for Magic rules questions
def generate_judge_prompt(user_question):
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

# Template for Magic general help questions
def generate_help_prompt(user_question):
    return f"""
You are a professional Magic: The Gathering expert and deckbuilding assistant. A player has asked the following question:

\"{user_question}\"

Provide a helpful and strategic answer based on current Magic meta knowledge and gameplay principles. Use competitive terminology, mention strong cards or synergies when relevant, and keep it beginner-friendly if needed.
"""

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    user_id = str(message.author.id)

    # Recognize follow-up based on recent history
    is_followup = user_id in conversation_history and not content.startswith("!")

    if content.startswith("!judge") or (is_followup and conversation_history[user_id]['type'] == 'judge'):
        question = content[len("!judge"):].strip() if content.startswith("!judge") else content
        if not question:
            await message.channel.send("Please provide a rules question after the command.")
            return

        messages = conversation_history.get(user_id, {}).get('messages', [
            {"role": "system", "content": "You are an expert MTG rules judge."}
        ])
        messages.append({"role": "user", "content": question})

        try:
            response = client_ai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.5
            )
            answer = response.choices[0].message.content
            await message.channel.send(answer)

            # Save to conversation history
            messages.append({"role": "assistant", "content": answer})
            conversation_history[user_id] = {"type": "judge", "messages": messages[-10:]}

        except Exception as e:
            await message.channel.send(f"❌ Error getting ruling: {e}")
            print(f"Error: {e}")

    elif content.startswith("!help") or (is_followup and conversation_history[user_id]['type'] == 'help'):
        question = content[len("!help"):].strip() if content.startswith("!help") else content
        if not question:
            await message.channel.send("Please ask a Magic: The Gathering-related question after the !help command.")
            return

        messages = conversation_history.get(user_id, {}).get('messages', [
            {"role": "system", "content": "You are a helpful MTG expert and deckbuilding advisor."}
        ])
        messages.append({"role": "user", "content": question})

        try:
            response = client_ai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7
            )
            answer = response.choices[0].message.content
            await message.channel.send(answer)

            # Save to conversation history
            messages.append({"role": "assistant", "content": answer})
            conversation_history[user_id] = {"type": "help", "messages": messages[-10:]}

        except Exception as e:
            await message.channel.send(f"❌ Error getting help: {e}")
            print(f"Error: {e}")

client.run(DISCORD_TOKEN)
