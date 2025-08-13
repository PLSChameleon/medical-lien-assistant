from datetime import datetime
from gmail_auth import get_gmail_service

def search_gmail(query_string):
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', q=query_string, maxResults=50).execute()
    messages = results.get('messages', [])
    email_data = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = msg_data.get('payload', {})
        headers_list = payload.get('headers', [])
        headers = {h['name']: h['value'] for h in headers_list}

        sender = headers.get('From', 'Unknown Sender')
        date_raw = headers.get('Date')
        snippet = msg_data.get('snippet', '').strip()

        # Parse date safely
        try:
            email_date = datetime.strptime(date_raw, '%a, %d %b %Y %H:%M:%S %z')
        except Exception:
            email_date = None

        # Check for attachment
        has_attachment = False
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('filename') and part.get('body', {}).get('attachmentId'):
                has_attachment = True
                break

        email_data.append({
            "sender": sender,
            "snippet": snippet,
            "has_attachment": has_attachment,
            "date": email_date,
            "headers": headers_list,
            "threadId": msg_data.get("threadId")
        })


    return email_data
