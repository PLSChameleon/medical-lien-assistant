import base64
from datetime import datetime
from email.mime.text import MIMEText

from file_lookup import get_file_info
from email_search import search_gmail
from summarizer import summarize_snippets
from gmail_auth import get_gmail_service
from openai import OpenAI
from dotenv import load_dotenv
import os
from email.utils import getaddresses

load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

def normalize_dt(dt):
    if dt is None:
        return datetime.min
    if dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt

def to_proper_case(text):
    return ' '.join(word.capitalize() for word in text.split())

def generate_followup_email_with_gpt(name, pv, doi):
    proper_name = to_proper_case(name)
    prompt = f"""
You are Dean Hyland from Transcon Financial, following up on a medical lien case for {proper_name} (PV #: {pv}) with a date of injury on {doi}.
Draft a short, professional follow-up email to the attorney asking for a case status update. Be cooperative, courteous, and helpful.
Only return the email body, not the subject or signature.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ GPT failed to generate the email:\n{e}"

def send_followup_email(subject, body, recipient):
    service = get_gmail_service()

    message = MIMEText(body)
    message['to'] = recipient
    message['from'] = "me"
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        sent = service.users().messages().send(userId='me', body={'raw': raw}).execute()
        print(f"\n✅ Follow-up email sent. Gmail ID: {sent['id']}")
    except Exception as e:
        print(f"\n❌ Failed to send email: {e}")

def confirm_and_send_email(subject, body, recipient_email):
    confirm_send = input(f"\n📤 Would you like to send this email now to {recipient_email}? (Y/n): ").strip().lower()
    if confirm_send == 'y':
        send_followup_email(subject, body, recipient_email)
    elif confirm_send == 'n':
        manual_email = input("📧 Enter a different email address to send this follow-up: ").strip()
        if manual_email:
            send_followup_email(subject, body, manual_email)
        else:
            print("❌ No email entered. Email not sent.")
    else:
        print("❌ Email not sent.")

# --- Begin Script ---
pv_input = input("Enter PV #: ").strip()
info = get_file_info(pv=pv_input)

if info:
    print("\n✅ File Found:")
    print(f"Name: {info.get('Name')}")
    print(f"PV #: {info.get('PV #')}")
    print(f"CMS: {info.get('CMS')}")
    print(f"Date of Injury: {info.get('Date of Injury')}")

    name = info.get("Name", "").strip()
    pv = str(info.get("PV #"))
    cms = str(info.get("CMS"))
    doi = str(info.get("Date of Injury")).split(" ")[0]
    proper_name = to_proper_case(name)

    search_terms = [f'"{name}"', pv, cms]
    search_query = " OR ".join(filter(None, search_terms))

    print("\n🔍 Searching Gmail for:", search_query)
    email_data = search_gmail(search_query)

    if email_data:
        print("\n📬 Email Snippets Found:")
        prev_date = None
        last_email_date = None
        for email in sorted(email_data, key=lambda x: normalize_dt(x["date"])):
            date = normalize_dt(email["date"])
            date_str = date.strftime("%Y-%m-%d %H:%M") if email["date"] else "Unknown Date"

            if email["date"]:
                last_email_date = email["date"]

            if prev_date and email["date"]:
                gap_days = (normalize_dt(email["date"]) - prev_date).days
                if gap_days >= 14:
                    print(f"⚠️  {gap_days} days passed with no response.")
            prev_date = normalize_dt(email["date"])

            from_label = "YOU" if "deanh.transcon" in email["sender"].lower() else email['sender']
            print(f"FROM: {from_label}")
            print(f"DATE: {date_str}")
            print(f"ATTACHMENT: {email['has_attachment']}")
            print(f"MESSAGE: {email['snippet']}\n")

        print("\n🧠 Generating Summary with GPT...")
        summary = summarize_snippets(email_data, name)
        print("\n📄 Summary:\n")
        print(summary)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = f"summary_{pv_input}_{timestamp}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"\n💾 Summary saved to {out_path}")

        # Determine most recent non-you recipient
        user_email = "deanh.transcon"
        last_sent = None
        recipient_email = None
        for email in reversed(email_data):
            if user_email in email["sender"].lower() and email.get("headers"):
                # Look for 'To' field in headers
                to_header = next((h['value'] for h in email['headers'] if h['name'].lower() == 'to'), None)
                if to_header:
                    addresses = getaddresses([to_header])
                    if addresses:
                        recipient_email = addresses[0][1]  # ('Name', 'email@example.com')
                        break

        # Offer follow-up if no email sent in 30+ days
        if last_sent:
            days_since_sent = (datetime.now() - normalize_dt(last_sent)).days
            if days_since_sent >= 30 and recipient_email:
                print(f"\n📭 It has been {days_since_sent} days since your last email on this case.")
                draft_choice = input(f"📝 Would you like to GPT-generate a follow-up to {recipient_email}? (Y/n): ").strip().lower()
                if draft_choice == 'y':
                    subject = f"{name.upper()} DOI {doi} // Prohealth"
                    body = generate_followup_email_with_gpt(name, pv, doi) + "\n\nBest regards,\nDean Hyland\nTranscon Financial, Inc.\n(909) 219-6008"
                    print("\n✉️ Draft Follow-Up Email:\n")
                    print(body)
                    confirm_and_send_email(subject, body, recipient_email)

        # Offer if 30+ days since any message
        if last_email_date:
            days_gap = (datetime.now() - normalize_dt(last_email_date)).days
            if days_gap >= 30:
                choice = input(f"\n📭 It has been {days_gap} days since any communication. Generate a follow-up? (Y/n): ").strip().lower()
                if choice == 'y':
                    subject = f"{name.upper()} DOI {doi} // Prohealth"
                    body = generate_followup_email_with_gpt(name, pv, doi) + "\n\nBest regards,\nDean Hyland\nTranscon Financial, Inc.\n(909) 219-6008"
                    print("\n✉️ GPT-Generated Follow-Up Email:\n")
                    print(body)
                    if recipient_email:
                        confirm_and_send_email(subject, body, recipient_email)
                    else:
                        print("❌ Could not determine recipient email.")

    else:
        print("📭 No prior emails found. Would you like to start a new email?")
        new = input("➕ Start a fresh email thread? (Y/n): ").strip().lower()
        if new == 'y':
            recipient_email = input("📧 Enter recipient email: ").strip()
            subject = f"{name.upper()} DOI {doi} // Prohealth"
            body = generate_followup_email_with_gpt(name, pv, doi) + "\n\nBest regards,\nDean Hyland\nTranscon Financial, Inc.\n(909) 219-6008"
            print("\n✉️ New Email Draft:\n")
            print(f"TO: {recipient_email}")
            print(f"SUBJECT: {subject}")
            print(f"\n{body}")
            confirm = input(f"\n📤 Send this new email? (Y/n): ").strip().lower()
            if confirm == 'y':
                send_followup_email(subject, body, recipient_email)
            else:
                print("❌ Email not sent.")
else:
    print("❌ No file found with that PV #.")
