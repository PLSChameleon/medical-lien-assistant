"""
Easy Gmail Authentication Handler
Automatically captures OAuth tokens without manual copy/paste
"""

import os
import json
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import logging

logger = logging.getLogger(__name__)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback"""
    
    def do_GET(self):
        """Handle GET request with authorization code"""
        # Parse the URL
        query_components = parse_qs(urlparse(self.path).query)
        
        # Check if we got an authorization code
        if 'code' in query_components:
            # Store the code
            self.server.auth_code = query_components['code'][0]
            
            # Send success response to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .container {
                        background: white;
                        padding: 50px;
                        border-radius: 10px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 500px;
                    }
                    h1 { color: #4CAF50; }
                    p { color: #666; margin: 20px 0; }
                    .checkmark {
                        font-size: 60px;
                        color: #4CAF50;
                        animation: scale 0.5s ease-in-out;
                    }
                    @keyframes scale {
                        0% { transform: scale(0); }
                        50% { transform: scale(1.2); }
                        100% { transform: scale(1); }
                    }
                    .close-message {
                        margin-top: 30px;
                        padding: 15px;
                        background: #f0f0f0;
                        border-radius: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="checkmark">✓</div>
                    <h1>Authentication Successful!</h1>
                    <p>Your Gmail account has been connected successfully.</p>
                    <div class="close-message">
                        <strong>You can close this window</strong><br>
                        The Medical Lien Assistant will continue setup automatically.
                    </div>
                </div>
                <script>
                    // Auto-close after 5 seconds
                    setTimeout(function() {
                        window.close();
                    }, 5000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        else:
            # No code - show error
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Failed</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #f44336;
                    }
                    .container {
                        background: white;
                        padding: 50px;
                        border-radius: 10px;
                        text-align: center;
                    }
                    h1 { color: #f44336; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Authentication Failed</h1>
                    <p>Please close this window and try again.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
    
    def log_message(self, format, *args):
        """Suppress console output"""
        pass


class EasyGmailAuth:
    """Simplified Gmail authentication handler"""
    
    def __init__(self):
        self.creds = None
        self.port = 8080  # Default port
        
    def authenticate(self, force_new=False):
        """
        Perform Gmail authentication with automatic token capture
        
        Args:
            force_new: Force new authentication even if token exists
            
        Returns:
            Credentials object or None if failed
        """
        # Check for existing valid token
        if not force_new and os.path.exists('token.json'):
            try:
                self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                if self.creds and self.creds.valid:
                    return self.creds
                elif self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                    with open('token.json', 'w') as token:
                        token.write(self.creds.to_json())
                    return self.creds
            except Exception as e:
                logger.warning(f"Could not use existing token: {e}")
        
        # Check for credentials.json
        if not os.path.exists('credentials.json'):
            print("\n⚠️  MISSING CREDENTIALS FILE")
            print("="*50)
            print("\nThe file 'credentials.json' is required but not found.")
            print("\nThis file is provided by your administrator.")
            print("Please contact your IT department or supervisor")
            print("to get the credentials.json file.")
            print("\nOnce you have it, place it in:")
            print(f"  {os.getcwd()}")
            print("\nThen run this setup again.")
            return None
        
        # Try automatic authentication with local server
        print("\n🔐 GMAIL AUTHENTICATION")
        print("="*50)
        print("\nA browser window will open for Gmail sign-in.")
        print("Please sign in and allow access when prompted.")
        print("\n⏳ Waiting for authentication...")
        
        try:
            # Use InstalledAppFlow with automatic port selection
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            # Run the local server to capture the authorization
            # Port 0 means select any available port
            self.creds = flow.run_local_server(
                port=0,
                authorization_prompt_message='Please visit this URL to authorize: {url}',
                success_message='Authentication successful! You can close this window.',
                open_browser=True
            )
            
            # Save the credentials
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
            
            print("\n✅ Authentication successful!")
            print("   Your Gmail account is now connected.")
            
            return self.creds
            
        except Exception as e:
            print(f"\n❌ Authentication failed: {e}")
            print("\nTROUBLESHOOTING:")
            print("1. Make sure you have internet connection")
            print("2. Try using a different browser as default")
            print("3. Check if antivirus is blocking the connection")
            print("4. Try running as Administrator")
            
            # Fallback to manual mode
            print("\n" + "="*50)
            print("MANUAL AUTHENTICATION MODE")
            print("="*50)
            return self._manual_auth_fallback()
    
    def _manual_auth_fallback(self):
        """Fallback to manual authentication if automatic fails"""
        print("\nIf the automatic method didn't work, try this:")
        print("\n1. Open your browser")
        print("2. Go to the URL shown below")
        print("3. Sign in to Gmail and approve access")
        print("4. Copy the authorization code from the page")
        print("5. Paste it here when prompted")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            # Get the authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            
            print(f"\n🌐 AUTHORIZATION URL:")
            print("="*50)
            print(auth_url)
            print("="*50)
            
            # Try to open browser
            webbrowser.open(auth_url)
            
            # Get the authorization code from user
            print("\nAfter approving access, you'll see an authorization code.")
            code = input("Enter the authorization code here: ").strip()
            
            if not code:
                print("❌ No code entered")
                return None
            
            # Exchange code for token
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            
            # Save the credentials
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
            
            print("\n✅ Authentication successful!")
            return self.creds
            
        except Exception as e:
            print(f"\n❌ Manual authentication failed: {e}")
            return None
    
    def test_connection(self):
        """Test the Gmail connection"""
        if not self.creds:
            return False
            
        try:
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=self.creds)
            profile = service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'Unknown')
            print(f"\n✅ Connected to Gmail account: {email}")
            return True
        except Exception as e:
            print(f"\n❌ Connection test failed: {e}")
            return False


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]


def setup_gmail_easy():
    """Main function to run easy Gmail setup"""
    auth = EasyGmailAuth()
    
    if auth.authenticate():
        if auth.test_connection():
            return True
    
    return False


if __name__ == "__main__":
    # Run setup if called directly
    success = setup_gmail_easy()
    if success:
        print("\n🎉 Gmail setup complete!")
        print("You can now use the Medical Lien Assistant.")
    else:
        print("\n😞 Setup failed. Please try again or contact support.")
        
    input("\nPress Enter to exit...")