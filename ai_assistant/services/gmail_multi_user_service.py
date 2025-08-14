"""
Multi-User Gmail Service
Extends the existing Gmail service to support multiple users
"""

import os
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from config import Config
from .gmail_service import GmailService
from .user_credential_manager import UserCredentialManager

logger = logging.getLogger(__name__)

class MultiUserGmailService(GmailService):
    """Gmail service with multi-user support"""
    
    def __init__(self, user_email: str = None):
        """
        Initialize Gmail service for a specific user
        
        Args:
            user_email: Email address of the user to authenticate as
        """
        self.service = None
        self.credential_manager = UserCredentialManager()
        self.user_email = user_email
        
        if user_email:
            self.credential_manager.set_current_user(user_email)
            self._authenticate_user(user_email)
    
    def _authenticate_user(self, user_email: str):
        """Authenticate with Gmail API for a specific user"""
        creds = None
        
        # Get user-specific token path
        token_path = self.credential_manager.get_user_gmail_token_path(user_email)
        
        # Check if token exists
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, Config.GMAIL_SCOPES)
            except Exception as e:
                logger.error(f"Error loading token for {user_email}: {e}")
        
        # Check if credentials are valid
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    # Refresh the token
                    creds.refresh(Request())
                    logger.info(f"Successfully refreshed Gmail credentials for {user_email}")
                    
                    # Save refreshed token
                    with open(token_path, "w") as token:
                        token.write(creds.to_json())
                    
                    # Save token path in credential manager
                    self.credential_manager.save_user_gmail_token(user_email, token_path)
                except Exception as e:
                    logger.error(f"Failed to refresh credentials for {user_email}: {e}")
                    raise Exception(f"Failed to refresh Gmail token for {user_email}. Please re-authenticate.")
            else:
                # Need to perform new OAuth flow
                raise Exception(
                    f"No valid Gmail token found for {user_email}. Please complete the authentication setup."
                )
        
        # Build the service
        self.service = build("gmail", "v1", credentials=creds)
        logger.info(f"Gmail service authenticated successfully for {user_email}")
    
    def authenticate_new_user(self, user_email: str) -> bool:
        """
        Start OAuth flow for a new user
        
        Args:
            user_email: Email address of the new user
            
        Returns:
            bool: True if authentication successful
        """
        try:
            # Check for credentials.json
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
            if not os.path.exists(credentials_path):
                logger.error("credentials.json not found. Please ensure the Gmail API project credentials are available.")
                return False
            
            # Create OAuth flow
            flow = Flow.from_client_secrets_file(
                credentials_path,
                scopes=Config.GMAIL_SCOPES,
                redirect_uri='http://localhost:8080'
            )
            
            # Get authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                login_hint=user_email
            )
            
            # Return the auth URL - the GUI will handle opening this
            self.auth_url = auth_url
            self.flow = flow
            self.pending_user_email = user_email
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting authentication for {user_email}: {e}")
            return False
    
    def complete_authentication(self, authorization_code: str) -> bool:
        """
        Complete the OAuth flow with the authorization code
        
        Args:
            authorization_code: The authorization code from Google
            
        Returns:
            bool: True if authentication completed successfully
        """
        try:
            if not hasattr(self, 'flow') or not hasattr(self, 'pending_user_email'):
                logger.error("No pending authentication flow")
                return False
            
            # Exchange authorization code for credentials
            self.flow.fetch_token(code=authorization_code)
            creds = self.flow.credentials
            
            # Save the credentials
            token_path = self.credential_manager.get_user_gmail_token_path(self.pending_user_email)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            
            # Save token path in credential manager
            self.credential_manager.save_user_gmail_token(self.pending_user_email, token_path)
            
            # Set current user and authenticate
            self.user_email = self.pending_user_email
            self.credential_manager.set_current_user(self.user_email)
            self._authenticate_user(self.user_email)
            
            # Clean up
            delattr(self, 'flow')
            delattr(self, 'pending_user_email')
            delattr(self, 'auth_url')
            
            logger.info(f"Successfully authenticated new user: {self.user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing authentication: {e}")
            return False
    
    def switch_user(self, user_email: str) -> bool:
        """
        Switch to a different authenticated user
        
        Args:
            user_email: Email address of the user to switch to
            
        Returns:
            bool: True if switch successful
        """
        try:
            # Check if user has authenticated before
            token_path = self.credential_manager.get_user_gmail_token_path(user_email)
            
            if not os.path.exists(token_path):
                logger.error(f"No saved credentials for {user_email}")
                return False
            
            # Switch user
            self.user_email = user_email
            self.credential_manager.set_current_user(user_email)
            self._authenticate_user(user_email)
            
            logger.info(f"Switched to user: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching user: {e}")
            return False
    
    def get_authenticated_users(self) -> list:
        """Get list of all authenticated users"""
        return self.credential_manager.list_users()
    
    def remove_user(self, user_email: str):
        """Remove a user's authentication"""
        self.credential_manager.remove_user(user_email)
        
        # If removed user is current user, clear service
        if self.user_email == user_email:
            self.service = None
            self.user_email = None