import re
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv
import os
from gmail_auth import get_gmail_service

load_dotenv()
client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

def extract_email_address(header):
    # Get just the email address (e.g., From: "Jane Smith <jane@law.com>" → jane@law.com)
    match = re.search(r'<([^>]+)>', header)
    return match.group(1) if match else header

def fetch_threads_matching_query(query):
    service = get_gmail_service()
    messages = []
    response = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
    messages.extend(response.get('messages', []))

    # Group messages by threadId
    thread_map = defaultdict(list)

    for msg in messages:
        full = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
        thread_id = full['threadId']
        headers = {h['name']: h['value'] for h in full.get('payload', {}).get('headers', [])}
        sender = extract_email_address(headers.get('From', 'Unknown Sender'))
        subject = headers.get('Subject', '[No Subject]')
        snippet = full.get('snippet', '').strip()
        date = headers.get('Date', '')

        thread_map[thread_id].append({
            'sender': sender,
            'subject': subject,
            'snippet': snippet,
            'date': date
        })

    return thread_map

def summarize_threads(thread_map, contact_name):
    summaries = []

    for i, (thread_id, messages) in enumerate(thread_map.items(), start=1):
        sorted_msgs = sorted(messages, key=lambda x: x.get('date', ''))
        participants = sorted(set(m['sender'] for m in sorted_msgs))
        last_msg = sorted_msgs[-1]['snippet'] if sorted_msgs else "No content"

        text_for_gpt = f"""
Thread {i} – Email Thread Summary

Participants: {', '.join(participants)}
Last Message Snippet: {last_msg}

Give a 1-sentence summary of what this thread is about and whether it’s worth replying to in the context of {contact_name}'s lien or billing.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": text_for_gpt}],
                temperature=0.3
            )
            gpt_summary = response.choices[0].message.content.strip()
        except Exception as e:
            gpt_summary = f"[Error summarizing thread: {e}]"

        summaries.append({
            'thread_id': thread_id,
            'participants': participants,
            'summary': gpt_summary,
            'last_message': last_msg,
            'index': i
        })

    return summaries
