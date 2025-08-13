import base64
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import getaddresses

from file_lookup import get_file_info
from email_search import search_gmail
from summarizer import summarize_snippets
from gmail_auth import get_gmail_service
from choose_thread import choose_thread
from openai import OpenAI
from dotenv import load_dotenv

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

def log_sent_email(cms, pv, name, doi, recipient_email):
    log_line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CMS: {cms} | PV: {pv} | Name: {name} | DOI: {doi} | STATUS REQUEST EMAIL SENT TO: {recipient_email}\n"
    with open("sent_emails.log", "a", encoding="utf-8") as log_file:
        log_file.write(log_line)

def generate_followup_email_with_gpt(name, pv, doi, last_message=None):
    proper_name = to_proper_case(name)

    if last_message:
        context = f"""
This is the previous message in the thread:

"{last_message}"

There has been no reply to this message.
"""
    else:
        context = ""

    prompt = f"""
You are Dean Hyland, the personal lien collector for Prohealth Advanced Imaging.

The patient’s name is {proper_name}, PV #: {pv}, date of injury: {doi}.
{context}

Draft a short and professional follow-up email requesting a case status update. Do not ask about payment. Explain that if there is a signed lien on file from the firm we can release any documents such as medical reports or charges.

Request that the recipient please store your contact information for when the case resolves and payment is due as you will be in charge of handling payment negotiations and possible lien reductions. Keep it short and to the point, as this is a follow-up email.

Do NOT include a subject line or signature — only the body of the email.
""".strip()



    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ GPT failed to generate the email:\n{e}"


def send_followup_email(subject, body, recipient, thread_id=None):
    service = get_gmail_service()
    message = MIMEText(body)
    message['to'] = recipient
    message['from'] = "me"
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    payload = {'raw': raw}
    if thread_id:
        payload['threadId'] = thread_id

    try:
        sent = service.users().messages().send(userId='me', body=payload).execute()
        print(f"\n✅ Email sent. Gmail ID: {sent['id']}")
    except Exception as e:
        print(f"\n❌ Failed to send email: {e}")

def confirm_and_send_email(subject, body, recipient_email, cms, pv, name, doi, thread_id=None):
    confirm_send = input(f"\n📤 Would you like to send this email now to {recipient_email}? (Y/n): ").strip().lower()

    if confirm_send == 'y':
        send_followup_email(subject, body, recipient_email, thread_id)
        log_sent_email(cms, pv, name, doi, recipient_email)

    elif confirm_send == 'n':
        use_alternate = input("🔄 Would you like to enter a different email address instead? (Y/n): ").strip().lower()
        if use_alternate == 'y':
            manual_email = input("📧 Enter a different email address to send this follow-up: ").strip()
            if manual_email:
                send_followup_email(subject, body, manual_email)
                log_sent_email(cms, pv, name, doi, manual_email)
            else:
                print("❌ No email entered. Email not sent.")
        else:
            print("❌ Email cancelled.")

    else:
        print("❌ Email not sent.")


# --- Start ---
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
        os.makedirs("summaries", exist_ok=True)
        out_path = os.path.join("summaries", f"summary_{pv_input}_{timestamp}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"\n💾 Summary saved to {out_path}")


        # 30-day communication gap check
        if last_email_date:
            days_gap = (datetime.now() - normalize_dt(last_email_date)).days
        if days_gap >= 30:
            choice = input(f"\n📭 It has been {days_gap} days since any communication on this case. Generate follow-up email? (Y/n): ").strip().lower()
            if choice == 'y':
                subject = f"{name.upper()} DOI {doi} // Prohealth"
                selected = choose_thread(email_data)
                if selected.get("CANCEL"):
                    print("❌ Email process cancelled by user.")
                else:
                    thread_id = selected.get("threadId")
                    context_snippet = selected.get("snippet", "")
                    body = generate_followup_email_with_gpt(name, pv, doi, last_message=context_snippet)
                    body += "\n\nBest regards,\nDean Hyland\nProhealth Advanced Imaging\n(909) 219-6008"

                    # ✅ Get recipient from selected thread
                    recipient_email = None
                    if selected.get("headers"):
                        headers_dict = {h["name"].lower(): h["value"] for h in selected["headers"]}
                        to_header = headers_dict.get("to")
                        if to_header:
                            addresses = getaddresses([to_header])
                            if addresses:
                                recipient_email = addresses[0][1]

                    print(f"\n📧 Email will be sent to: {recipient_email}")
                    confirm = input("✅ Is this the correct recipient? (Y/n): ").strip().lower()
                    if confirm != 'y':
                        print("❌ Email cancelled.")
                    else:
                        print("\n✉️ GPT-Generated Follow-Up Email:\n")
                        print(body)
                        confirm_and_send_email(subject, body, recipient_email, cms, pv, name, doi, thread_id)


    else:
        print("No emails found.")

        # Column S is the 18th column (index 17)
        fallback_email = info.get(info.keys()[17]) if len(info) >= 18 else None

        if fallback_email and "@" in fallback_email:
            choice = input(f"\n📭 No emails found. Would you like to send a follow-up to the attorney on file ({fallback_email})? (Y/n): ").strip().lower()
            if choice == 'y':
                subject = f"{name.upper()} DOI {doi} // Prohealth"
                selected = choose_thread([])
                if selected.get("CANCEL"):
                    print("❌ Email process cancelled by user.")
                else:
                    thread_id = selected.get("threadId")
                    context_snippet = selected.get("snippet", "")
                    body = generate_followup_email_with_gpt(name, pv, doi, last_message=context_snippet)
                    body += "\n\nBest regards,\nDean Hyland\nProhealth Advanced Imaging\n(909) 219-6008"

                    print(f"\n📧 Email will be sent to: {fallback_email}")
                    confirm = input("✅ Is this the correct recipient? (Y/n): ").strip().lower()
                    if confirm != 'y':
                        print("❌ Email cancelled.")
                    else:
                        print("\n✉️ GPT-Generated Follow-Up Email:\n")
                        print(body)
                        confirm_and_send_email(subject, body, fallback_email, cms, pv, name, doi, thread_id)

            

        else:
            print("⚠️ No valid attorney email found in the spreadsheet.")

else:
    print("❌ No file found with that PV #.")
