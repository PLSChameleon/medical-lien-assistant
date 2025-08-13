from datetime import datetime
from email.utils import getaddresses

def choose_thread(email_data):
    print("\n📩 Choose an email thread to reply to:")
    threads = []

    for i, email in enumerate(sorted(email_data, key=lambda x: x["date"] or 0), start=1):
        sender = email.get("sender", "Unknown Sender")
        headers = {h["name"].lower(): h["value"] for h in email.get("headers", [])}
        to_field = headers.get("to", "Unknown Recipient")
        recipients = getaddresses([to_field])
        to_display = recipients[0][1] if recipients else to_field

        date = email["date"]
        snippet = email["snippet"][:80].replace("\n", " ").strip()
        date_str = date.strftime("%Y-%m-%d %H:%M") if date else "Unknown Date"

        print(f"[{i}] FROM: {sender} → TO: {to_display} | DATE: {date_str} | \"{snippet}\"")
        email["to"] = to_display
        threads.append(email)

    print(f"[{len(threads)+1}] Start a new email thread")
    print("Or type 'n' to cancel and send no email.")

    while True:
        choice = input("\nEnter your choice: ").strip().lower()

        if choice == 'n':
            return {"CANCEL": True}
        if choice.isdigit():
            choice = int(choice)
            if 1 <= choice <= len(threads):
                return threads[choice - 1]
            elif choice == len(threads) + 1:
                return {"threadId": None}  # new thread

        print("❌ Invalid choice. Try again.")
