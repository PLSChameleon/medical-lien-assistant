import os.path
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# This scope allows read-only access to Gmail messages
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None

    # Load token if it exists
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)

    # If no token, go through OAuth flow
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES
        )
        creds = flow.run_local_server(port=0)

        # Save token for next time
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)

    # Return the Gmail service object
    return build('gmail', 'v1', credentials=creds)

# Test run
if __name__ == '__main__':
    service = get_gmail_service()
    print("✅ Gmail API is authenticated and ready to use!")
