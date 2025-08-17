"""
Seamless Gmail Authentication
No manual code copying required - just click and authorize!
"""

import os
import json
import webbrowser
import socket
import threading
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class AuthCallbackHandler(BaseHTTPRequestHandler):
    """Handles OAuth callback automatically"""
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass
    
    def do_GET(self):
        """Handle the OAuth callback"""
        query_components = parse_qs(urlparse(self.path).query)
        
        if 'code' in query_components:
            # Store the authorization code
            self.server.auth_code = query_components['code'][0]
            
            # Send success page to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Gmail Connected!</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .success-container {
                        background: white;
                        padding: 60px;
                        border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        text-align: center;
                        max-width: 500px;
                        animation: slideIn 0.5s ease-out;
                    }
                    @keyframes slideIn {
                        from { transform: translateY(-50px); opacity: 0; }
                        to { transform: translateY(0); opacity: 1; }
                    }
                    .checkmark {
                        width: 80px;
                        height: 80px;
                        border-radius: 50%;
                        background: #4CAF50;
                        margin: 0 auto 30px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        animation: scaleIn 0.5s ease-out 0.2s both;
                    }
                    @keyframes scaleIn {
                        from { transform: scale(0); }
                        to { transform: scale(1); }
                    }
                    .checkmark::after {
                        content: '✓';
                        color: white;
                        font-size: 50px;
                        font-weight: bold;
                    }
                    h1 {
                        color: #333;
                        margin-bottom: 20px;
                        font-size: 32px;
                    }
                    p {
                        color: #666;
                        font-size: 18px;
                        line-height: 1.6;
                        margin-bottom: 30px;
                    }
                    .auto-close {
                        background: #f5f5f5;
                        padding: 20px;
                        border-radius: 10px;
                        color: #888;
                        font-size: 14px;
                    }
                    .progress-bar {
                        width: 100%;
                        height: 4px;
                        background: #e0e0e0;
                        border-radius: 2px;
                        margin-top: 20px;
                        overflow: hidden;
                    }
                    .progress-fill {
                        height: 100%;
                        background: #4CAF50;
                        animation: progress 5s linear;
                    }
                    @keyframes progress {
                        from { width: 100%; }
                        to { width: 0%; }
                    }
                </style>
            </head>
            <body>
                <div class="success-container">
                    <div class="checkmark"></div>
                    <h1>Successfully Connected!</h1>
                    <p>Your Gmail account has been linked to the Medical Lien Assistant.</p>
                    <div class="auto-close">
                        <strong>You can close this window</strong>
                        <br>or it will close automatically in a few seconds
                        <div class="progress-bar">
                            <div class="progress-fill"></div>
                        </div>
                    </div>
                </div>
                <script>
                    setTimeout(function() {
                        window.close();
                        // If window.close() doesn't work, show a message
                        document.body.innerHTML = '<div style="text-align:center;padding:50px;"><h2>You can now close this window</h2></div>';
                    }, 5000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
            
        elif 'error' in query_components:
            # Handle authorization error
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Cancelled</title>
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
                    .error-container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        text-align: center;
                    }
                    h1 { color: #f44336; }
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>Authorization Cancelled</h1>
                    <p>Please try again and click "Allow" to connect your Gmail account.</p>
                    <p>You can close this window.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())


def find_available_port(start_port=8080, max_attempts=10):
    """Find an available port for the local server"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find available port in range {start_port}-{start_port + max_attempts}")


def authenticate_gmail(credentials_file='credentials.json', token_file='token.json', scopes=None):
    """
    Authenticate Gmail with seamless OAuth flow
    
    Args:
        credentials_file: Path to OAuth credentials JSON
        token_file: Path to save/load token
        scopes: Gmail API scopes needed
    
    Returns:
        Credentials object
    """
    if scopes is None:
        scopes = ['https://www.googleapis.com/auth/gmail.modify']
    
    creds = None
    
    # Check for existing token
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, scopes)
            
            # Check if token is valid
            if creds and creds.valid:
                logger.info("Using existing valid Gmail token")
                return creds
            
            # Try to refresh expired token
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save refreshed token
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Successfully refreshed Gmail token")
                    return creds
                except Exception as e:
                    logger.warning(f"Could not refresh token: {e}")
                    creds = None
        except Exception as e:
            logger.warning(f"Could not load existing token: {e}")
            creds = None
    
    # Need new authentication
    if not creds:
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(
                f"Gmail credentials file not found: {credentials_file}\n"
                "Please download credentials.json from Google Cloud Console:\n"
                "1. Go to https://console.cloud.google.com/\n"
                "2. Create a new project or select existing\n"
                "3. Enable Gmail API\n"
                "4. Create OAuth 2.0 credentials\n"
                "5. Download as credentials.json"
            )
        
        # Find available port
        port = find_available_port()
        redirect_uri = f'http://localhost:{port}'
        
        # Create OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file, 
            scopes,
            redirect_uri=redirect_uri
        )
        
        # Create local server to catch the authorization code
        server = HTTPServer(('localhost', port), AuthCallbackHandler)
        server.auth_code = None
        server.timeout = 120  # 2 minute timeout
        
        # Start server in a separate thread
        server_thread = threading.Thread(target=lambda: server.handle_request())
        server_thread.daemon = True
        server_thread.start()
        
        # Get authorization URL and open browser
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            access_type='offline',
            include_granted_scopes='true'
        )
        
        print("\n" + "="*60)
        print("GMAIL AUTHENTICATION REQUIRED")
        print("="*60)
        print("\nOpening your browser for Gmail authorization...")
        print("\n1. Sign in to your Gmail account")
        print("2. Click 'Allow' to grant access")
        print("3. The browser will show 'Successfully Connected!'")
        print("4. Return to this program\n")
        print("="*60 + "\n")
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Wait for authorization
        print("Waiting for authorization...")
        timeout = time.time() + 120  # 2 minute timeout
        
        while server.auth_code is None and time.time() < timeout:
            time.sleep(0.5)
        
        if server.auth_code is None:
            raise TimeoutError(
                "Authorization timed out. Please try again.\n"
                "Make sure to click 'Allow' in your browser."
            )
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=server.auth_code)
        creds = flow.credentials
        
        # Save the token for future use
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        print("\n✓ Gmail authentication successful!")
        logger.info("Gmail authentication completed successfully")
    
    return creds


def test_gmail_connection(creds):
    """Test if Gmail connection works"""
    try:
        service = build('gmail', 'v1', credentials=creds)
        # Try to get user's email address
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress', 'Unknown')
        
        print(f"\n✓ Successfully connected to Gmail: {email_address}")
        return True, email_address
    except Exception as e:
        print(f"\n✗ Failed to connect to Gmail: {e}")
        return False, None


if __name__ == "__main__":
    # Test the authentication
    try:
        print("Testing seamless Gmail authentication...")
        creds = authenticate_gmail()
        test_gmail_connection(creds)
    except Exception as e:
        print(f"Error: {e}")