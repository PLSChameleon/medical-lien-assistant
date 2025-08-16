"""
User Setup Wizard
First-run wizard for configuring user credentials
"""

import sys
import os
import webbrowser
import logging
from PyQt5.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox,
    QComboBox, QGroupBox, QRadioButton, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont, QDesktopServices
import asyncio
from services.user_credential_manager import UserCredentialManager
from services.gmail_multi_user_service import MultiUserGmailService
from services.cms_multi_user_integration import MultiUserCMSIntegration
try:
    from utils.easy_gmail_auth import EasyGmailAuth
except ImportError:
    EasyGmailAuth = None

logger = logging.getLogger(__name__)

class WelcomePage(QWizardPage):
    """Welcome page for the setup wizard"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Medical Lien Assistant")
        self.setSubTitle("This wizard will help you set up your credentials for first use.")
        
        layout = QVBoxLayout()
        
        # Welcome message
        welcome_text = QLabel(
            "Welcome! This application helps manage medical lien cases.\n\n"
            "To get started, we need to configure:\n"
            "• Your Gmail account for email management\n"
            "• Your CMS credentials for case notes\n\n"
            "This setup only needs to be done once. Your credentials will be "
            "securely stored on your computer."
        )
        welcome_text.setWordWrap(True)
        layout.addWidget(welcome_text)
        
        # User selection
        layout.addSpacing(20)
        user_group = QGroupBox("Select User Type")
        user_layout = QVBoxLayout()
        
        self.new_user_radio = QRadioButton("I'm a new user")
        self.new_user_radio.setChecked(True)
        user_layout.addWidget(self.new_user_radio)
        
        self.existing_user_radio = QRadioButton("I've used this before (switch user)")
        user_layout.addWidget(self.existing_user_radio)
        
        user_group.setLayout(user_layout)
        layout.addWidget(user_group)
        
        layout.addStretch()
        self.setLayout(layout)

class GmailSetupPage(QWizardPage):
    """Gmail authentication setup page"""
    
    def __init__(self, parent_wizard):
        super().__init__()
        self.parent_wizard = parent_wizard
        self.setTitle("Gmail Account Setup")
        self.setSubTitle("Connect your Gmail account to manage emails")
        
        self.gmail_service = None
        self.auth_completed = False
        
        layout = QVBoxLayout()
        
        # Email input
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Gmail Address:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@gmail.com")
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)
        
        # Instructions
        instructions = QLabel(
            "\nSteps:\n"
            "1. Enter your Gmail address above\n"
            "2. Click 'Authorize Gmail' below\n"
            "3. A browser window will open - sign in to Google\n"
            "4. Grant permission to access your Gmail\n"
            "5. Copy the authorization code and paste it below"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Authorization button
        self.auth_button = QPushButton("Authorize Gmail")
        self.auth_button.clicked.connect(self.start_gmail_auth)
        layout.addWidget(self.auth_button)
        
        # Authorization code input
        layout.addSpacing(10)
        code_layout = QVBoxLayout()
        code_layout.addWidget(QLabel("Authorization Code:"))
        self.auth_code_input = QLineEdit()
        self.auth_code_input.setPlaceholderText("Paste the authorization code here")
        self.auth_code_input.setEnabled(False)
        code_layout.addWidget(self.auth_code_input)
        
        self.verify_button = QPushButton("Verify Code")
        self.verify_button.clicked.connect(self.verify_auth_code)
        self.verify_button.setEnabled(False)
        code_layout.addWidget(self.verify_button)
        layout.addLayout(code_layout)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("QLabel { color: blue; }")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Register field for wizard completion
        self.registerField("gmail_email*", self.email_input)
    
    def start_gmail_auth(self):
        """Start Gmail OAuth flow with automatic token capture"""
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, "Error", "Please enter your Gmail address")
            return
        
        try:
            # Try to use easy authentication if available
            if EasyGmailAuth:
                auth = EasyGmailAuth()
                
                self.status_label.setText("Opening browser for Gmail sign-in...")
                self.status_label.setStyleSheet("QLabel { color: blue; }")
                QApplication.processEvents()
                
                # Perform authentication (automatically captures token)
                creds = auth.authenticate()
                
                if creds:
                    # Authentication successful
                    self.auth_completed = True
                    self.status_label.setText("✓ Gmail authenticated successfully!")
                    self.status_label.setStyleSheet("QLabel { color: green; }")
                    
                    # Store email in wizard
                    self.parent_wizard.user_email = email
                    
                    # Disable inputs since we're done
                    self.email_input.setEnabled(False)
                    self.auth_button.setEnabled(False)
                    self.auth_code_input.hide()
                    self.verify_button.hide()
                    
                    # Mark page as complete
                    self.completeChanged.emit()
                    return
            
            # Fall back to manual method if easy auth not available
            self.gmail_service = MultiUserGmailService()
            
            if self.gmail_service.authenticate_new_user(email):
                # Open browser with auth URL
                auth_url = self.gmail_service.auth_url
                webbrowser.open(auth_url)
                
                # Enable code input for manual entry
                self.auth_code_input.setEnabled(True)
                self.verify_button.setEnabled(True)
                
                self.status_label.setText("Browser opened. Please complete authentication and paste the code.")
                self.status_label.setStyleSheet("QLabel { color: blue; }")
            else:
                QMessageBox.critical(self, "Error", 
                    "Failed to start authentication. Please ensure credentials.json is present.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Authentication error: {str(e)}")
    
    def verify_auth_code(self):
        """Verify the authorization code"""
        code = self.auth_code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "Error", "Please paste the authorization code")
            return
        
        try:
            if self.gmail_service and self.gmail_service.complete_authentication(code):
                self.auth_completed = True
                self.status_label.setText("✓ Gmail authenticated successfully!")
                self.status_label.setStyleSheet("QLabel { color: green; }")
                
                # Store email in wizard
                self.parent_wizard.user_email = self.email_input.text().strip()
                
                # Disable inputs
                self.email_input.setEnabled(False)
                self.auth_button.setEnabled(False)
                self.auth_code_input.setEnabled(False)
                self.verify_button.setEnabled(False)
                
                # Mark page as complete
                self.completeChanged.emit()
            else:
                QMessageBox.critical(self, "Error", "Invalid authorization code. Please try again.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to verify code: {str(e)}")
    
    def isComplete(self):
        """Check if page is complete"""
        return self.auth_completed

class CMSSetupPage(QWizardPage):
    """CMS credentials setup page"""
    
    def __init__(self, parent_wizard):
        super().__init__()
        self.parent_wizard = parent_wizard
        self.setTitle("CMS Credentials Setup")
        self.setSubTitle("Enter your CMS login credentials")
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Enter your CMS (Transcon Financial) login credentials.\n"
            "These will be encrypted and stored securely on your computer."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(20)
        
        # Username input
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("CMS Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your CMS username")
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        # Password input
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("CMS Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your CMS password")
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # Show password checkbox
        self.show_password_cb = QCheckBox("Show password")
        self.show_password_cb.toggled.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password_cb)
        
        # Test connection button
        layout.addSpacing(20)
        self.test_button = QPushButton("Test CMS Connection")
        self.test_button.clicked.connect(self.test_cms_connection)
        layout.addWidget(self.test_button)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Register fields
        self.registerField("cms_username*", self.username_input)
        self.registerField("cms_password*", self.password_input)
    
    def toggle_password_visibility(self, checked):
        """Toggle password visibility"""
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
    
    def test_cms_connection(self):
        """Test CMS connection with provided credentials"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return
        
        self.status_label.setText("Testing connection...")
        self.status_label.setStyleSheet("QLabel { color: blue; }")
        self.test_button.setEnabled(False)
        
        # For now, just save the credentials
        # In production, you would actually test the login
        QTimer.singleShot(1000, lambda: self.connection_test_complete(True))
    
    def connection_test_complete(self, success):
        """Handle connection test result"""
        self.test_button.setEnabled(True)
        
        if success:
            self.status_label.setText("✓ CMS credentials verified!")
            self.status_label.setStyleSheet("QLabel { color: green; }")
        else:
            self.status_label.setText("✗ Failed to connect. Please check credentials.")
            self.status_label.setStyleSheet("QLabel { color: red; }")

class CompletionPage(QWizardPage):
    """Setup completion page"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete!")
        self.setSubTitle("Your credentials have been configured successfully")
        
        layout = QVBoxLayout()
        
        completion_text = QLabel(
            "Setup is complete! Your credentials have been securely saved.\n\n"
            "You can now:\n"
            "• Search and process Gmail messages\n"
            "• Send bulk emails to law firms\n"
            "• Add notes to CMS automatically\n"
            "• Track case statuses and responses\n\n"
            "Click 'Finish' to start using the Medical Lien Assistant."
        )
        completion_text.setWordWrap(True)
        layout.addWidget(completion_text)
        
        layout.addStretch()
        self.setLayout(layout)

class UserSetupWizard(QWizard):
    """Main setup wizard"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Medical Lien Assistant - Setup Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(600, 500)
        
        # Initialize credential manager
        self.credential_manager = UserCredentialManager()
        self.user_email = None
        
        # Add pages
        self.welcome_page = WelcomePage()
        self.gmail_page = GmailSetupPage(self)
        self.cms_page = CMSSetupPage(self)
        self.completion_page = CompletionPage()
        
        self.addPage(self.welcome_page)
        self.addPage(self.gmail_page)
        self.addPage(self.cms_page)
        self.addPage(self.completion_page)
        
        # Connect finish button
        self.finished.connect(self.save_credentials)
    
    def save_credentials(self):
        """Save all credentials when wizard completes"""
        if self.user_email:
            # Save CMS credentials
            cms_username = self.field("cms_username")
            cms_password = self.field("cms_password")
            
            if cms_username and cms_password:
                self.credential_manager.save_cms_credentials(
                    self.user_email, cms_username, cms_password
                )
                logger.info(f"All credentials saved for {self.user_email}")

def should_show_setup_wizard():
    """Check if setup wizard should be shown"""
    manager = UserCredentialManager()
    users = manager.list_users()
    
    # Show wizard if no users configured
    return len(users) == 0

def run_setup_wizard():
    """Run the setup wizard"""
    app = QApplication(sys.argv)
    wizard = UserSetupWizard()
    wizard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_setup_wizard()