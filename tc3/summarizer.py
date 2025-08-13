import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load your OpenAI API key from the .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

def normalize_dt(dt):
    """Convert all datetime objects to naive format for consistent comparison."""
    if dt is None:
        return datetime.min
    if dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt

def summarize_snippets(email_data, contact_name=None):
    if not email_data:
        return "No email data provided."

    # Sort emails by date (oldest to newest)
    sorted_emails = sorted(email_data, key=lambda x: normalize_dt(x["date"]))

    # Build message log and detect last email date
    combined = ""
    last_email_date = None

    for email in sorted_emails:
        date = email["date"]
        if date:
            last_email_date = date
        date_str = normalize_dt(date).strftime("%Y-%m-%d") if date else "Unknown Date"
        combined += f"\n• {date_str} FROM: {email['sender']} - {email['snippet']}"

    # Determine time since last email
    days_since_last = None
    delay_note = ""
    if last_email_date:
        now = datetime.now()
        last_email_naive = normalize_dt(last_email_date)
        days_since_last = (now - last_email_naive).days
        if days_since_last >= 30:
            delay_note = f"\n🚨 It has been {days_since_last} days since the last message. Recommend sending a follow-up email."

    # Build GPT prompt
    prompt = f"""
You are reviewing email communication related to a medical lien and billing case involving Prohealth Advanced Imaging.

The emails may contain discussions about case status, signed liens, settlements, litigation, or other communications with a law firm.

Use this format to summarize the case:

📄 Summary for {contact_name or 'Attorney/Contact'}

- Attainment: Who is working on it, or if no response has occurred.
- Lien Status: Is it signed, pending, or not discussed?
- Case Status: Settlement, pending, litigation, denied, or unknown.
- Payments: Any mention of payments issued or expected?
- Firm Communication: How responsive has the firm been?

➡️ Next Steps:
1. Based on context and time delays, what should Dean H do?
2. What is the most urgent follow-up action?

📝 Notes:
Mention anything notable:
- The case is in litigation
- Attorney says no representation
- Reports were sent
- Signed lien was returned
- Repeated attempts to follow up
- They are refusing to cooperate

{delay_note}

Emails for context:
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
