#!/usr/bin/env python3
"""
Gmail Setup Wizard for New Users
Handles OAuth authentication and initial configuration
"""

import os
import json
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# Gmail API scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

class GmailSetupWizard:
    """Interactive setup wizard for new Gmail users"""
    
    def __init__(self):
        self.creds = None
        self.user_email = None
        self.user_name = None
        
    def run(self):
        """Run the complete setup wizard"""
        print("\n" + "="*60)
        print("🎯 GMAIL SETUP WIZARD")
        print("="*60)
        print("\nThis wizard will help you connect your Gmail account")
        print("and configure the email assistant for your use.\n")
        
        # Step 1: Check for existing setup
        if self._check_existing_setup():
            print("\n✅ Existing Gmail setup detected!")
            use_existing = input("Do you want to use the existing setup? (y/n): ").strip().lower()
            if use_existing == 'y':
                print("✅ Using existing Gmail configuration")
                return True
            else:
                print("🔄 Setting up new Gmail account...")
        
        # Step 2: OAuth Setup
        if not self._setup_oauth():
            print("❌ Gmail authentication failed. Please try again.")
            return False
        
        # Step 3: Get user info
        self._get_user_info()
        
        # Step 4: Configure settings
        self._configure_settings()
        
        # Step 5: Test connection
        if self._test_connection():
            print("\n✅ Setup complete! You can now use all email features.")
            return True
        else:
            print("\n❌ Setup failed. Please check your settings and try again.")
            return False
    
    def _check_existing_setup(self):
        """Check if Gmail is already configured"""
        return os.path.exists('token.json')
    
    def _setup_oauth(self):
        """Handle OAuth authentication flow"""
        print("\n📋 OAUTH AUTHENTICATION")
        print("-" * 40)
        
        # Check for credentials.json
        if not os.path.exists('credentials.json'):
            print("\n⚠️  credentials.json not found!")
            print("\nTo get credentials.json:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a new project or select existing")
            print("3. Enable Gmail API")
            print("4. Create OAuth 2.0 credentials")
            print("5. Download as credentials.json")
            print("6. Place in this directory: " + os.getcwd())
            
            input("\nPress Enter when credentials.json is ready...")
            
            if not os.path.exists('credentials.json'):
                print("❌ credentials.json still not found")
                return False
        
        try:
            # Run OAuth flow
            print("\n🔐 Starting authentication...")
            print("A browser window will open for Gmail authorization.")
            print("Please log in and grant permissions.\n")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            self.creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
            
            print("✅ Authentication successful!")
            return True
            
        except Exception as e:
            logger.error(f"OAuth setup failed: {e}")
            print(f"❌ Authentication failed: {e}")
            return False
    
    def _get_user_info(self):
        """Get user's email address and name from Gmail"""
        try:
            print("\n📧 Getting account information...")
            
            service = build('gmail', 'v1', credentials=self.creds)
            profile = service.users().getProfile(userId='me').execute()
            
            self.user_email = profile.get('emailAddress', '')
            print(f"✅ Connected to: {self.user_email}")
            
            # Try to get user name from email
            self.user_name = input("\nEnter your name: ").strip()
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            self.user_email = input("\nEnter your Gmail address: ").strip()
            self.user_name = input("Enter your name: ").strip()
    
    def _configure_settings(self):
        """Configure user-specific settings"""
        print("\n⚙️  CONFIGURATION")
        print("-" * 40)
        
        config = {
            "user_email": self.user_email,
            "user_name": self.user_name,
            "company_name": input("Enter your company/practice name: ").strip(),
            "sent_email_indicators": []
        }
        
        # Note: No signature needed - Gmail adds it automatically
        print("\nℹ️  Note: Gmail will automatically add your signature to all emails.")
        
        # Set up sent email indicators (for identifying sent vs received)
        config["sent_email_indicators"] = [
            self.user_email.lower(),
            config["user_name"].lower().split()[0] if config["user_name"] else "",
            config["company_name"].lower().split()[0] if config["company_name"] else ""
        ]
        
        # Remove empty indicators
        config["sent_email_indicators"] = [i for i in config["sent_email_indicators"] if i]
        
        # Save configuration
        config_path = "data/user_config.json"
        os.makedirs("data", exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration saved to {config_path}")
        
        # Update email cache service config
        self._update_email_cache_config(config)
        
        return config
    
    def _update_email_cache_config(self, config):
        """Update email cache service with user-specific settings"""
        try:
            # Read the email_cache_service.py file
            service_file = "services/email_cache_service.py"
            if not os.path.exists(service_file):
                return
            
            with open(service_file, 'r') as f:
                content = f.read()
            
            # Find the _is_sent_email method and update indicators
            indicators_str = str(config["sent_email_indicators"])
            
            # Create a marker file instead of modifying code
            marker_file = "data/email_indicators.json"
            with open(marker_file, 'w') as f:
                json.dump({
                    "sent_indicators": config["sent_email_indicators"]
                }, f, indent=2)
            
            print("✅ Email detection configured")
            
        except Exception as e:
            logger.warning(f"Could not update email cache config: {e}")
    
    def _test_connection(self):
        """Test Gmail connection"""
        print("\n🧪 TESTING CONNECTION")
        print("-" * 40)
        
        try:
            service = build('gmail', 'v1', credentials=self.creds)
            
            # Test: Get message count
            result = service.users().messages().list(
                userId='me', maxResults=1
            ).execute()
            
            print("✅ Gmail API connection successful!")
            
            # Test: Check for messages
            if result.get('messages'):
                print("✅ Can read emails")
            else:
                print("⚠️  No emails found (inbox might be empty)")
            
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            print(f"❌ Connection test failed: {e}")
            return False
    
    def reset_setup(self):
        """Reset Gmail configuration"""
        print("\n🔄 Resetting Gmail configuration...")
        
        files_to_remove = [
            'token.json',
            'data/user_config.json',
            'data/email_indicators.json'
        ]
        
        for file in files_to_remove:
            if os.path.exists(file):
                os.remove(file)
                print(f"   Removed {file}")
        
        print("✅ Reset complete. Run setup wizard to reconfigure.")


def main():
    """Run the setup wizard"""
    wizard = GmailSetupWizard()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        wizard.reset_setup()
    else:
        wizard.run()


if __name__ == "__main__":
    main()