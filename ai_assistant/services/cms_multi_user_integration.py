"""
Multi-User CMS Integration Service
Extends the CMS integration to support multiple users with different credentials
"""

import logging
import os
from .cms_integration import CMSIntegration
from .user_credential_manager import UserCredentialManager

logger = logging.getLogger(__name__)

class MultiUserCMSIntegration(CMSIntegration):
    """CMS Integration with multi-user support"""
    
    def __init__(self, user_email: str = None, use_persistent_session=True):
        """
        Initialize CMS integration for a specific user
        
        Args:
            user_email: Email address of the user
            use_persistent_session: Whether to use persistent browser session
        """
        self.credential_manager = UserCredentialManager()
        self.user_email = user_email
        
        # Get CMS credentials for this user
        if user_email:
            cms_creds = self.credential_manager.get_cms_credentials(user_email)
            if cms_creds and cms_creds.get('username') and cms_creds.get('password'):
                # Use user-specific credentials
                self.username = cms_creds['username']
                self.password = cms_creds['password']
            else:
                # Fall back to environment variables or defaults
                self.username = os.getenv("CMS_USERNAME", "")
                self.password = os.getenv("CMS_PASSWORD", "")
                
                if not self.username or not self.password:
                    logger.warning(f"No CMS credentials found for {user_email}")
        else:
            # No user specified, use environment variables
            self.username = os.getenv("CMS_USERNAME", "")
            self.password = os.getenv("CMS_PASSWORD", "")
        
        # Set login URL
        self.login_url = "https://cms.transconfinancialinc.com/CMS"
        
        # Initialize other properties
        self.use_persistent = use_persistent_session
        self.browser = None
        self.context = None
        self.page = None
    
    def set_cms_credentials(self, username: str, password: str):
        """
        Set CMS credentials for the current user
        
        Args:
            username: CMS username
            password: CMS password
        """
        if self.user_email:
            # Save credentials for this user
            self.credential_manager.save_cms_credentials(
                self.user_email, username, password
            )
            self.username = username
            self.password = password
            logger.info(f"CMS credentials updated for {self.user_email}")
        else:
            logger.error("No user email set - cannot save credentials")
    
    def has_cms_credentials(self) -> bool:
        """Check if current user has CMS credentials"""
        if self.user_email:
            return self.credential_manager.has_cms_credentials(self.user_email)
        return bool(self.username and self.password)
    
    async def login(self):
        """Override login to use user-specific credentials"""
        if not self.username or not self.password:
            raise ValueError(f"No CMS credentials available for {self.user_email or 'current user'}")
        
        # Call parent login method
        await super().login()
    
    @classmethod
    async def get_persistent_session_for_user(cls, user_email: str):
        """
        Get or create a persistent browser session for a specific user
        
        Args:
            user_email: Email address of the user
            
        Returns:
            Page object for the persistent session
        """
        # Create instance with user credentials
        instance = cls(user_email=user_email, use_persistent_session=True)
        
        # Check if user has credentials
        if not instance.has_cms_credentials():
            raise ValueError(f"No CMS credentials found for {user_email}. Please configure credentials first.")
        
        # Get or create persistent session
        return await cls.get_persistent_session()
    
    def switch_user(self, user_email: str):
        """
        Switch to a different user's CMS credentials
        
        Args:
            user_email: Email address of the user to switch to
        """
        self.user_email = user_email
        
        # Get CMS credentials for new user
        cms_creds = self.credential_manager.get_cms_credentials(user_email)
        if cms_creds and cms_creds.get('username') and cms_creds.get('password'):
            self.username = cms_creds['username']
            self.password = cms_creds['password']
            logger.info(f"Switched to CMS credentials for {user_email}")
        else:
            logger.warning(f"No CMS credentials found for {user_email}")
            self.username = ""
            self.password = ""