import os
import json
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Load credentials from .env
load_dotenv()
TOKEN_PATH = "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.send"]

def authenticate_gmail():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("No valid Gmail token found. Please run the Gmail OAuth flow first.")
    return build("gmail", "v1", credentials=creds)

def parse_email_metadata(message):
    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
    return {
        "date": headers.get("Date", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "snippet": message.get("snippet", "")
    }

def collect_thread_summaries(service, max_threads=500):
    results = service.users().threads().list(userId="me", maxResults=max_threads).execute()
    threads = results.get("threads", [])
    summaries = []

    for thread in threads:
        thread_id = thread["id"]
        full_thread = service.users().threads().get(userId="me", id=thread_id).execute()
        messages = full_thread.get("messages", [])
        convo = [parse_email_metadata(m) for m in messages]
        summaries.append({
            "threadId": thread_id,
            "historyId": full_thread.get("historyId"),
            "messageCount": len(convo),
            "messages": convo
        })

    return summaries

def save_to_file(data, filename="email_thread_history.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    print("🔐 Authenticating with Gmail...")
    service = authenticate_gmail()
    print("📥 Fetching last 500 threads...")
    thread_data = collect_thread_summaries(service, max_threads=500)
    save_to_file(thread_data)
    print("✅ Saved to email_thread_history.json")
