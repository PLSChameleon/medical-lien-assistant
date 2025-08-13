from gmail_auth import get_gmail_service

def search_gmail(query_string):
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', q=query_string).execute()
    messages = results.get('messages', [])
    snippets = []

    for msg in messages[:10]:  # Limit to first 10 results
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippets.append(msg_data.get('snippet', ''))

    return snippets or ["No emails found."]
