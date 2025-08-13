import os.path
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ✅ Scopes: read email, send email, access thread metadata
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.metadata'
]

def get_gmail_service():
    creds = None

    # Load token if it exists
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)

    # If no valid token, run the auth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the token for next time
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)

    # Build and return the Gmail service object
    return build('gmail', 'v1', credentials=creds)

# Optional test run
if __name__ == '__main__':
    service = get_gmail_service()
    profile = service.users().getProfile(userId='me').execute()
    print(f"✅ Authenticated as: {profile['emailAddress']}")
