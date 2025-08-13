from gmail_auth import get_gmail_service

def search_gmail(query_string):
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', q=query_string).execute()
    messages = results.get('messages', [])
    email_data = []

    for msg in messages[:10]:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = {h['name']: h['value'] for h in msg_data['payload'].get('headers', [])}
        sender = headers.get('From', 'Unknown Sender')
        snippet = msg_data.get('snippet', '').strip()

        # Check for attachment
        has_attachment = False
        parts = msg_data['payload'].get('parts', [])
        for part in parts:
            if part.get('filename') and part.get('body', {}).get('attachmentId'):
                has_attachment = True
                break

        email_data.append({
            "sender": sender,
            "snippet": snippet,
            "has_attachment": has_attachment
        })

    # Join all snippets with metadata for summarizer
    enriched_text = "\n\n".join(
        f"FROM: {email['sender']}\nATTACHMENT: {email['has_attachment']}\nMESSAGE: {email['snippet']}"
        for email in email_data
    )

    return enriched_text
