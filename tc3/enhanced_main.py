import argparse
import base64
from datetime import datetime
from email.mime.text import MIMEText

from file_lookup import get_file_info
from email_search import search_gmail
from summarizer import summarize_snippets
from gmail_auth import get_gmail_service

def normalize_dt(dt):
    if dt is None:
        return datetime.min
    if dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt

def generate_followup_email(info):
    name = info.get("Name", "your client")
    pv = info.get("PV #", "[PV #]")
    doi = info.get("Date of Injury", "[Date of Injury]").split(" ")[0].replace("/", "-")
    subject = f"{name.upper()} DOI {doi} // Prohealth"

    body = f"""
Subject: {subject}

Hello,

I hope you're doing well. I'm following up regarding the case for {name}, PV #: {pv}, with a date of injury on {doi}.

We have the signed lien on file, and I wanted to check in to see if there have been any recent updates on the case status. Specifically, can you please advise whether the case has progressed toward settlement or if any payments are expected in the near future?

We’d appreciate any updates you can provide at your earliest convenience.

Thank you for your time and continued cooperation.

Best regards,  
Dean Hyland  
Transcon Financial, Inc.  
(909) 219-6008
""".strip()

    return body

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

def confirm_and_send_email(followup, recipient_email):
    confirm_send = input(f"\n📤 Would you like to send this email now to {recipient_email}? (Y/n): ").strip().lower()
    if confirm_send == 'y':
        subject_line = followup.splitlines()[0].replace("Subject: ", "").strip()
        body = "\n".join(followup.splitlines()[2:]).strip()
        send_followup_email(subject_line, body, recipient_email)
    elif confirm_send == 'n':
        manual_email = input("📧 Enter a different email address to send this follow-up: ").strip()
        if manual_email:
            subject_line = followup.splitlines()[0].replace("Subject: ", "").strip()
            body = "\n".join(followup.splitlines()[2:]).strip()
            send_followup_email(subject_line, body, manual_email)
        else:
            print("❌ No email entered. Email not sent.")
    else:
        print("❌ Email not sent.")

# --- CLI ---
parser = argparse.ArgumentParser(description="Search and summarize case-related emails")
parser.add_argument('--pv', required=True, help='PV number to search for')
parser.add_argument('--output', default=None, help='Optional: Path to save summary file')
args = parser.parse_args()

pv_input = args.pv
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
        summary = summarize_snippets(email_data, info["Name"])
        print("\n📄 Summary:\n")
        print(summary)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = args.output or f"summary_{pv_input}_{timestamp}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"\n💾 Summary saved to {out_path}")

        # Detect last sent & recipient
        user_email = "deanh.transcon"
        last_sent = None
        recipient_email = None
        for email in reversed(email_data):
            if not recipient_email and user_email not in email["sender"].lower():
                raw_sender = email["sender"]
                if "<" in raw_sender and ">" in raw_sender:
                    recipient_email = raw_sender.split("<")[-1].split(">")[0].strip()
                else:
                    recipient_email = raw_sender.strip()
            if user_email in email["sender"].lower() and email["date"]:
                last_sent = email["date"]
                break

        if last_sent:
            days_since_sent = (datetime.now() - normalize_dt(last_sent)).days
            if days_since_sent >= 30 and recipient_email:
                print(f"\n📭 It has been {days_since_sent} days since your last email on this case.")
                draft_choice = input(f"📝 Would you like to draft a follow-up status request email to {recipient_email}? (Y/n): ").strip().lower()
                if draft_choice == 'y':
                    followup = generate_followup_email(info)
                    print("\n✉️ Draft Follow-Up Email:\n")
                    print(followup)
                    confirm_and_send_email(followup, recipient_email)

        if last_email_date:
            days_gap = (datetime.now() - normalize_dt(last_email_date)).days
            if days_gap >= 30:
                choice = input(f"\n📭 It has been {days_gap} days since any communication on this case. Generate follow-up email? (Y/n): ").strip().lower()
                if choice == 'y':
                    followup = generate_followup_email(info)
                    print("\n✉️ Follow-Up Email Draft:\n")
                    print(followup)

                    # Detect recipient again if needed
                    recipient_email = None
                    for email in reversed(email_data):
                        if "deanh.transcon" not in email["sender"].lower():
                            raw_sender = email["sender"]
                            if "<" in raw_sender and ">" in raw_sender:
                                recipient_email = raw_sender.split("<")[-1].split(">")[0].strip()
                            else:
                                recipient_email = raw_sender.strip()
                            break

                    if recipient_email:
                        confirm_and_send_email(followup, recipient_email)
                    else:
                        print("❌ Could not determine recipient email automatically.")
    else:
        print("No emails found.")
else:
    print("❌ No file found with that PV #.")
