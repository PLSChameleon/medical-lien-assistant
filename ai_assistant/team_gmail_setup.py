#!/usr/bin/env python3
"""
Simplified Gmail Setup for Team Members
Uses shared OAuth app - no Google Cloud Console needed!
"""

import os
import json
import shutil
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

class TeamGmailSetup:
    """Simplified setup for team members - uses shared OAuth app"""
    
    def __init__(self):
        self.creds = None
        self.user_email = None
        self.user_name = None
        
    def run(self):
        """Run the simplified setup for team members"""
        print("\n" + "="*60)
        print("🚀 GMAIL SETUP FOR TEAM MEMBERS")
        print("="*60)
        print("\nWelcome! This will connect your Gmail account in just a few steps.")
        print("No Google Cloud Console needed - we'll use the company OAuth app.\n")
        
        # Step 1: Check if credentials.json exists
        if not os.path.exists('credentials.json'):
            print("⚠️  OAuth app credentials not found.")
            print("\nPlease contact Dean to get the credentials.json file.")
            print("Once you have it, place it in this folder and run again.\n")
            return False
        
        # Step 2: Check for existing token
        if os.path.exists('token.json'):
            print("📋 Existing Gmail connection found.")
            replace = input("Do you want to set up a different Gmail account? (y/n): ").strip().lower()
            if replace != 'y':
                print("✅ Keeping existing Gmail connection.")
                return True
            else:
                # Remove old token
                os.remove('token.json')
                print("🔄 Setting up new Gmail account...")
        
        # Step 3: Run OAuth flow
        if not self._authenticate():
            return False
        
        # Step 4: Get user info and configure
        self._get_user_info()
        self._save_user_config()
        
        # Step 5: Test connection
        if self._test_connection():
            print("\n" + "="*60)
            print("✅ SUCCESS! Your Gmail is now connected!")
            print("="*60)
            print("\nYou can now:")
            print("• Run 'bootstrap emails' to download your email history")
            print("• Use all email features with your Gmail account")
            print("\nYour Gmail signature will be automatically added to all emails.")
            return True
        else:
            print("\n❌ Setup failed. Please try again or contact Dean for help.")
            return False
    
    def _authenticate(self):
        """Run simplified OAuth flow"""
        try:
            print("\n🔐 CONNECTING TO GMAIL")
            print("-" * 40)
            print("A browser window will open in a moment.")
            print("Please:")
            print("1. Log in with your work Gmail account")
            print("2. Click 'Continue' when you see the app name")
            print("3. Grant the requested permissions")
            print("\nPress Enter to open the authorization page...")
            input()
            
            # Run OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            
            # Use run_local_server for better user experience
            self.creds = flow.run_local_server(
                port=0,
                success_message='Authorization successful! You can close this window and return to the application.'
            )
            
            # Save the token
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
            
            print("\n✅ Gmail authorization successful!")
            return True
            
        except Exception as e:
            print(f"\n❌ Authorization failed: {e}")
            print("\nTroubleshooting:")
            print("• Make sure you're using your work Gmail account")
            print("• Try using a different browser if it doesn't open")
            print("• Contact Dean if you continue to have issues")
            return False
    
    def _get_user_info(self):
        """Get user's email and name"""
        try:
            print("\n📧 Getting your account information...")
            
            service = build('gmail', 'v1', credentials=self.creds)
            profile = service.users().getProfile(userId='me').execute()
            
            self.user_email = profile.get('emailAddress', '')
            print(f"✅ Connected to: {self.user_email}")
            
            # Get user's name for tracking
            self.user_name = input("\nEnter your full name: ").strip()
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            self.user_email = input("\nEnter your Gmail address: ").strip()
            self.user_name = input("Enter your full name: ").strip()
    
    def _save_user_config(self):
        """Save user configuration"""
        print("\n⚙️  Saving your settings...")
        
        # Detect company name from email domain
        company_name = "ProHealth Advanced Imaging"  # Default
        if '@' in self.user_email:
            domain = self.user_email.split('@')[1]
            if 'prohealth' in domain.lower():
                company_name = "ProHealth Advanced Imaging"
        
        config = {
            "user_email": self.user_email,
            "user_name": self.user_name,
            "company_name": company_name,
            "sent_email_indicators": []
        }
        
        # Set up email detection (for identifying sent vs received)
        config["sent_email_indicators"] = [
            self.user_email.lower(),
            self.user_name.lower().split()[0] if self.user_name else "",
            "prohealth"
        ]
        
        # Remove empty indicators
        config["sent_email_indicators"] = [i for i in config["sent_email_indicators"] if i]
        
        # Save configuration
        os.makedirs("data", exist_ok=True)
        
        config_path = "data/user_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Save email indicators for the cache service
        indicator_path = "data/email_indicators.json"
        with open(indicator_path, 'w') as f:
            json.dump({
                "sent_indicators": config["sent_email_indicators"]
            }, f, indent=2)
        
        print("✅ Settings saved successfully")
    
    def _test_connection(self):
        """Quick test of Gmail access"""
        print("\n🧪 Testing Gmail connection...")
        
        try:
            service = build('gmail', 'v1', credentials=self.creds)
            
            # Just check if we can access the API
            result = service.users().getProfile(userId='me').execute()
            
            if result:
                print("✅ Gmail connection verified!")
                return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            print(f"❌ Connection test failed: {e}")
            return False
        
        return False


def main():
    """Run the team setup"""
    print("\n🏢 ProHealth Email Assistant - Team Setup")
    print("-" * 50)
    
    setup = TeamGmailSetup()
    
    # Check for reset flag
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("🔄 Resetting Gmail connection...")
        if os.path.exists('token.json'):
            os.remove('token.json')
            print("✅ Reset complete. Run setup again to connect a new account.")
        else:
            print("ℹ️  No existing connection to reset.")
    else:
        setup.run()


if __name__ == "__main__":
    main()