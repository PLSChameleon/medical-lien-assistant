import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
api_key = os.getenv("OPEN_AI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

def summarize_snippets(snippets):
    if not snippets:
        return "No email content to summarize."

    combined_text = "\n\n".join(snippets)

    prompt = f"""
You are an assistant helping summarize email conversations about a client file. Write a concise and professional summary of the email thread below. Include who is involved, what was discussed, agreements or offers made, and any next steps if applicable.

Emails:
{combined_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error generating summary: {e}"
