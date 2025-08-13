from datetime import datetime
from gmail_auth import get_gmail_service

def search_gmail(query_string):
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', q=query_string).execute()
    messages = results.get('messages', [])
    email_data = []

    for msg in messages[:10]:  # or however many you want
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = {h['name']: h['value'] for h in msg_data['payload'].get('headers', [])}
        sender = headers.get('From', 'Unknown Sender')
        date_raw = headers.get('Date')
        snippet = msg_data.get('snippet', '').strip()

        try:
            email_date = datetime.strptime(date_raw, '%a, %d %b %Y %H:%M:%S %z')
        except Exception:
            email_date = None  # fallback if parsing fails

        has_attachment = any(
            part.get('filename') and part.get('body', {}).get('attachmentId')
            for part in msg_data['payload'].get('parts', [])
        )

        email_data.append({
            "sender": sender,
            "snippet": snippet,
            "has_attachment": has_attachment,
            "date": email_date
        })

    return email_data  # now returns list of dicts instead of single string
