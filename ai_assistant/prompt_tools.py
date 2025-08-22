import re
import json
from datetime import datetime
#from gmail_auth import get_gmail_service


def build_subject_line(case):
    # Convert name to title case (e.g., "John Smith" not "JOHN SMITH")
    name = ' '.join(word.capitalize() for word in str(case['Name']).split())
    doi = case['DOI'].strftime('%Y-%m-%d')
    return f"{name} DOI {doi} // Prohealth"


def generate_followup_prompt(case):
    # Convert name to title case
    name = ' '.join(word.capitalize() for word in str(case['Name']).split())
    doi = case['DOI'].strftime('%B %d, %Y')
    return f"""
Hello,

In regards to Prohealth Advanced Imaging billing and liens for {name} (DOI: {doi}), I am following up on my previous emails requesting the status of the case at this time.

Please get back to me when you have a moment.

Thank you for your time
""".strip()


def generate_status_request_prompt(case):
    # Convert name to title case
    name = ' '.join(word.capitalize() for word in str(case['Name']).split())
    doi = case['DOI'].strftime('%B %d, %Y')
    return f"""
Hello,

In regards to Prohealth Advanced Imaging billing and liens for {name} (DOI: {doi}), I am reaching out to request the current status of the case.

Please let me know when you have an update.

Thank you for your time
""".strip()


def extract_thread_candidates(all_threads, case):
    candidates = []
    for t in all_threads:
        for m in t["messages"]:
            snippet = m.get("snippet", "").lower()
            if case['Name'].lower() in snippet and str(case['DOI'].date()) in snippet:
                candidates.append({"threadId": m['threadId'], "to": m.get("to", ""), "from": m.get("from", "")})
    return candidates


def choose_recipient_email(case, thread_messages):
    print("\n📬 Available email threads for this case:")

    preview_options = []
    seen_emails = set()

    for i, thread in enumerate(thread_messages):
        thread_id = thread.get("id")
        messages = thread.get("messages", [])
        snippet = messages[-1].get("snippet", "")[:150] if messages else ""

        # Gather headers from the latest message
        headers = messages[-1].get("payload", {}).get("headers", []) if messages else []
        header_dict = {h['name']: h['value'] for h in headers if 'name' in h and 'value' in h}

        # Extract participants from headers
        to_field = header_dict.get("To", "")
        from_field = header_dict.get("From", "")

        participants = set([to_field, from_field])

        # Filter out your own email
        recipient = next((p for p in participants if p and "deanh.transcon@gmail.com" not in p.lower()), None)
        if not recipient or recipient.lower() in seen_emails:
            continue

        seen_emails.add(recipient.lower())
        preview_options.append((i, recipient, thread_id, snippet.strip()))

    if not preview_options:
        print("❌ No valid reply threads found. You may want to use a status request instead.")
        return None, None

    for idx, (i, recipient, thread_id, snippet) in enumerate(preview_options):
        print(f"{idx+1}. To: {recipient}\n   Snippet: {snippet}\n")

    try:
        choice = int(input("Select a thread to reply to (1-N): ").strip())
        recipient, thread_id = preview_options[choice - 1][1:3]
        return recipient, thread_id
    except Exception:
        print("❌ Invalid selection.")
        return None, None




def pick_status_recipient(case):
    known = [case.get("Attorney Email"), case.get("Alt Email 1"), case.get("Alt Email 2")]
    known = [e for e in known if e and "@" in e]
    print("\n📨 Possible recipient addresses:")
    for idx, email in enumerate(known, 1):
        print(f"{idx}. {email}")
    print(f"{len(known)+1}. Enter custom email")
    choice = input("Select recipient (default 1): ").strip()
    if choice == "" or not choice.isdigit():
        return known[0]
    idx = int(choice)
    if 1 <= idx <= len(known):
        return known[idx - 1]
    return input("Enter email: ").strip()