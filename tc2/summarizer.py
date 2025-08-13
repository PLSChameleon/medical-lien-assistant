import os
from openai import OpenAI
from dotenv import load_dotenv

# Load your OpenAI API key from the .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

def summarize_snippets(snippets, contact_name=None):
    if not snippets:
        return "No snippets provided."

    combined = "\n".join(f"• {s}" for s in snippets)

    prompt = f"""
You are reviewing email communication related to a medical lien and billing case involving Prohealth Advanced Imaging.

Emails may include requests for lien signatures, discussions about case status, settlements, litigation updates, or reports/charges being sent.

Your job is to summarize the case activity based on the ENTIRE thread. Use emails sent by the user (Dean H) for context and timeline only — do not write a separate summary for Dean.

Summarize the file in the following format:

📄 Summary for {contact_name or 'Attorney/Contact'}

- Attainment: Who is working on it, or if no response has occurred.
- Lien Status: Is it signed, pending, or not discussed?
- Case Status: Settlement, pending, litigation, denied, or unknown.
- Payments: Any mention of payments issued or expected?
- Firm Communication: How responsive has the firm been?

➡️ Next Steps:
1. Based on context, what should Dean H do next?
2. List the most urgent thing to resolve.

📝 Notes:
Mention anything notable, such as:
- The case is in litigation
- Attorney says no representation
- Reports were sent
- Signed lien was returned
- They’re refusing to cooperate
- Repeated attempts to follow up

Now summarize based on this email thread:

{combined}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"❌ Error generating summary:\n\n{str(e)}"
