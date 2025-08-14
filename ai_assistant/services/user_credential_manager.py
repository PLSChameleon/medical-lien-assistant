"""
User Credential Management System
Handles multiple users' Gmail and CMS credentials securely
"""

import os
import json
import hashlib
import platform
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import base64
import getpass
import logging

logger = logging.getLogger(__name__)

class UserCredentialManager:
    """Manages credentials for multiple users securely"""
    
    def __init__(self):
        # Get user-specific data directory
        self.data_dir = self._get_user_data_directory()
        self.credentials_file = self.data_dir / "user_credentials.json"
        self.encryption_key_file = self.data_dir / ".encryption_key"
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        self.cipher = self._get_or_create_cipher()
        
        # Load existing credentials
        self.credentials = self._load_credentials()
        
        # Current user identifier
        self.current_user = None
    
    def _get_user_data_directory(self) -> Path:
        """Get platform-specific user data directory"""
        system = platform.system()
        
        if system == "Windows":
            # Windows: %APPDATA%\MedicalLienAssistant
            base_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
            return Path(base_dir) / "MedicalLienAssistant"
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/MedicalLienAssistant
            return Path.home() / "Library" / "Application Support" / "MedicalLienAssistant"
        else:
            # Linux: ~/.config/MedicalLienAssistant
            return Path.home() / ".config" / "MedicalLienAssistant"
    
    def _get_or_create_cipher(self) -> Fernet:
        """Get or create encryption cipher for secure credential storage"""
        if self.encryption_key_file.exists():
            # Load existing encryption key
            with open(self.encryption_key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new encryption key
            key = Fernet.generate_key()
            # Save key securely (restricted permissions)
            with open(self.encryption_key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions on key file
            if platform.system() != "Windows":
                import stat
                os.chmod(self.encryption_key_file, stat.S_IRUSR | stat.S_IWUSR)
        
        return Fernet(key)
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def _load_credentials(self) -> Dict[str, Any]:
        """Load encrypted credentials from file"""
        if not self.credentials_file.exists():
            return {}
        
        try:
            with open(self.credentials_file, 'r') as f:
                encrypted_creds = json.load(f)
            
            # Decrypt credentials
            decrypted_creds = {}
            for user_id, user_data in encrypted_creds.items():
                decrypted_creds[user_id] = {
                    'email': user_data['email'],  # Email is not encrypted
                    'gmail_token_path': user_data.get('gmail_token_path'),
                    'cms_credentials': {
                        'username': self._decrypt_data(user_data['cms_credentials']['username']) if 'cms_credentials' in user_data else None,
                        'password': self._decrypt_data(user_data['cms_credentials']['password']) if 'cms_credentials' in user_data else None
                    } if 'cms_credentials' in user_data else {},
                    'preferences': user_data.get('preferences', {})
                }
            
            return decrypted_creds
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return {}
    
    def _save_credentials(self):
        """Save encrypted credentials to file"""
        try:
            # Encrypt sensitive data before saving
            encrypted_creds = {}
            for user_id, user_data in self.credentials.items():
                encrypted_creds[user_id] = {
                    'email': user_data['email'],
                    'gmail_token_path': user_data.get('gmail_token_path'),
                    'cms_credentials': {
                        'username': self._encrypt_data(user_data['cms_credentials']['username']) if user_data.get('cms_credentials', {}).get('username') else None,
                        'password': self._encrypt_data(user_data['cms_credentials']['password']) if user_data.get('cms_credentials', {}).get('password') else None
                    } if user_data.get('cms_credentials') else {},
                    'preferences': user_data.get('preferences', {})
                }
            
            # Save to file
            with open(self.credentials_file, 'w') as f:
                json.dump(encrypted_creds, f, indent=2)
            
            # Set restrictive permissions on credentials file
            if platform.system() != "Windows":
                import stat
                os.chmod(self.credentials_file, stat.S_IRUSR | stat.S_IWUSR)
            
            logger.info(f"Credentials saved for {len(self.credentials)} users")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
    
    def get_user_id_from_email(self, email: str) -> str:
        """Generate a unique user ID from email"""
        return hashlib.md5(email.lower().encode()).hexdigest()[:8]
    
    def get_current_user(self) -> Optional[str]:
        """Get current authenticated user's email"""
        return self.current_user
    
    def set_current_user(self, email: str):
        """Set the current authenticated user"""
        self.current_user = email
        user_id = self.get_user_id_from_email(email)
        
        # Initialize user data if new user
        if user_id not in self.credentials:
            self.credentials[user_id] = {
                'email': email,
                'gmail_token_path': None,
                'cms_credentials': {},
                'preferences': {}
            }
            self._save_credentials()
    
    def get_user_gmail_token_path(self, email: str) -> str:
        """Get user-specific Gmail token path"""
        user_id = self.get_user_id_from_email(email)
        token_filename = f"token_{user_id}.json"
        return str(self.data_dir / token_filename)
    
    def save_user_gmail_token(self, email: str, token_path: str):
        """Save Gmail token path for user"""
        user_id = self.get_user_id_from_email(email)
        
        if user_id in self.credentials:
            self.credentials[user_id]['gmail_token_path'] = token_path
            self._save_credentials()
    
    def get_cms_credentials(self, email: str) -> Dict[str, str]:
        """Get CMS credentials for user"""
        user_id = self.get_user_id_from_email(email)
        
        if user_id in self.credentials:
            return self.credentials[user_id].get('cms_credentials', {})
        return {}
    
    def save_cms_credentials(self, email: str, username: str, password: str):
        """Save CMS credentials for user"""
        user_id = self.get_user_id_from_email(email)
        
        if user_id not in self.credentials:
            self.credentials[user_id] = {
                'email': email,
                'gmail_token_path': None,
                'cms_credentials': {},
                'preferences': {}
            }
        
        self.credentials[user_id]['cms_credentials'] = {
            'username': username,
            'password': password
        }
        self._save_credentials()
        logger.info(f"CMS credentials saved for user: {email}")
    
    def has_cms_credentials(self, email: str) -> bool:
        """Check if user has saved CMS credentials"""
        cms_creds = self.get_cms_credentials(email)
        return bool(cms_creds.get('username') and cms_creds.get('password'))
    
    def get_user_preferences(self, email: str) -> Dict[str, Any]:
        """Get user preferences"""
        user_id = self.get_user_id_from_email(email)
        
        if user_id in self.credentials:
            return self.credentials[user_id].get('preferences', {})
        return {}
    
    def save_user_preference(self, email: str, key: str, value: Any):
        """Save a user preference"""
        user_id = self.get_user_id_from_email(email)
        
        if user_id in self.credentials:
            if 'preferences' not in self.credentials[user_id]:
                self.credentials[user_id]['preferences'] = {}
            
            self.credentials[user_id]['preferences'][key] = value
            self._save_credentials()
    
    def list_users(self) -> list:
        """List all users who have authenticated"""
        return [user_data['email'] for user_data in self.credentials.values()]
    
    def remove_user(self, email: str):
        """Remove a user's credentials"""
        user_id = self.get_user_id_from_email(email)
        
        if user_id in self.credentials:
            # Remove Gmail token file if it exists
            token_path = self.credentials[user_id].get('gmail_token_path')
            if token_path and os.path.exists(token_path):
                try:
                    os.remove(token_path)
                except:
                    pass
            
            # Remove from credentials
            del self.credentials[user_id]
            self._save_credentials()
            logger.info(f"Removed credentials for user: {email}")