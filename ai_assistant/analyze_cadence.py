import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

with open("email_thread_history.json", "r", encoding="utf-8") as f:
    threads = json.load(f)

sent_messages = []
for thread in threads:
    for msg in thread.get("messages", []):
        sender = msg.get("from", "").lower()
        if "prohealthlien" in sender or "dean hyland" in sender:
            content = msg.get("snippet", "")
            if len(content.strip()) >= 30:
                sent_messages.append(content.strip())

examples = sent_messages[:10]

email_block = "\n\n".join(f"---\n{e}" for e in examples)
analysis_prompt = f"""
You are analyzing email writing style and tone for a medical lien collector.

Here are 10 sample follow-up emails sent by the user:
{email_block}

Based on these examples, describe the typical writing style used. Break it down into:

1. Tone
2. Typical opening phrases
3. Sentence structure and length
4. Level of formality
5. Phrases or patterns that repeat
6. What to avoid
7. Preferred length
8. Style summary in one paragraph

Then write two prompt templates the assistant can reuse:

A. Follow-Up Email Prompt (for when an attorney previously responded)
B. Status Request Prompt (for a first-time email asking for a case update)

Only output JSON with keys: "style_summary", "followup_prompt", "status_request_prompt"
"""

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": analysis_prompt}],
    temperature=0.4
)

output = response.choices[0].message.content

with open("prompt_template.json", "w", encoding="utf-8") as f:
    f.write(output)

print("✅ prompt_template.json generated.")
