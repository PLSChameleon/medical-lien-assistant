"""
Multi-User Application Launcher
Main entry point that handles user setup and launches the application
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
from services.user_credential_manager import UserCredentialManager
from services.gmail_multi_user_service import MultiUserGmailService
from services.cms_multi_user_integration import MultiUserCMSIntegration
from user_setup_wizard import UserSetupWizard, should_show_setup_wizard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UserSelectionDialog(QDialog):
    """Dialog for selecting which user to login as"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Medical Lien Assistant - User Selection")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.credential_manager = UserCredentialManager()
        self.selected_user = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Select User Account")
        title.setAlignment(Qt.AlignCenter)
        font = title.font()
        font.setPointSize(12)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # User selection
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("User:"))
        
        self.user_combo = QComboBox()
        users = self.credential_manager.list_users()
        self.user_combo.addItems(users)
        self.user_combo.setMinimumWidth(250)
        user_layout.addWidget(self.user_combo)
        
        layout.addLayout(user_layout)
        
        # Add new user button
        layout.addSpacing(10)
        self.new_user_button = QPushButton("Add New User")
        self.new_user_button.clicked.connect(self.add_new_user)
        layout.addWidget(self.new_user_button)
        
        # Buttons
        layout.addSpacing(20)
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)
        self.login_button.setDefault(True)
        button_layout.addWidget(self.login_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_new_user(self):
        """Launch setup wizard for new user"""
        wizard = UserSetupWizard(self)
        if wizard.exec_():
            # Refresh user list
            users = self.credential_manager.list_users()
            self.user_combo.clear()
            self.user_combo.addItems(users)
            
            # Select the newly added user
            if wizard.user_email:
                index = self.user_combo.findText(wizard.user_email)
                if index >= 0:
                    self.user_combo.setCurrentIndex(index)
    
    def login(self):
        """Login as selected user"""
        self.selected_user = self.user_combo.currentText()
        if self.selected_user:
            # Verify user has all required credentials
            if not self.verify_credentials():
                return
            
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Please select a user")
    
    def verify_credentials(self):
        """Verify selected user has all required credentials"""
        # Check Gmail token
        gmail_service = MultiUserGmailService()
        try:
            if not gmail_service.switch_user(self.selected_user):
                response = QMessageBox.question(
                    self, "Gmail Not Configured",
                    f"Gmail is not configured for {self.selected_user}.\n"
                    "Would you like to set it up now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if response == QMessageBox.Yes:
                    self.add_new_user()
                return False
        except:
            pass
        
        # Check CMS credentials
        if not self.credential_manager.has_cms_credentials(self.selected_user):
            response = QMessageBox.question(
                self, "CMS Not Configured",
                f"CMS credentials are not configured for {self.selected_user}.\n"
                "Would you like to set them up now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if response == QMessageBox.Yes:
                self.add_new_user()
            return False
        
        return True

def launch_main_application(user_email):
    """Launch the main application with the selected user"""
    # Set the current user in credential manager
    credential_manager = UserCredentialManager()
    credential_manager.set_current_user(user_email)
    
    # Import and modify the main application to use multi-user services
    import enhanced_gui_app
    from services.cms_integration import CMSIntegrationService
    
    # Monkey-patch the services to use multi-user versions
    original_gmail_init = enhanced_gui_app.GmailService.__init__
    original_cms_init = CMSIntegrationService.__init__
    
    def gmail_init_wrapper(self):
        # Initialize with current user
        multi_service = MultiUserGmailService(user_email)
        self.service = multi_service.service
        self._authenticate = lambda: None  # Skip re-authentication
    
    def cms_init_wrapper(self, use_persistent_session=True):
        # Initialize with current user
        multi_cms = MultiUserCMSIntegration(user_email, use_persistent_session)
        self.username = multi_cms.username
        self.password = multi_cms.password
        self.login_url = multi_cms.login_url
        self.use_persistent_session = use_persistent_session
        self.use_persistent = use_persistent_session  # Some code might use this
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False
        self.note_type_value = "COR"
        self.next_contact_date = (datetime.today() + timedelta(days=30)).strftime("%m/%d/%Y")
    
    # Apply patches
    enhanced_gui_app.GmailService.__init__ = gmail_init_wrapper
    CMSIntegrationService.__init__ = cms_init_wrapper
    
    # Also patch it in the enhanced_gui_app module namespace if it exists
    if hasattr(enhanced_gui_app, 'CMSIntegration'):
        enhanced_gui_app.CMSIntegration.__init__ = cms_init_wrapper
    
    # Create and show main window
    try:
        window = enhanced_gui_app.EnhancedMainWindow()
        window.setWindowTitle(f"Medical Lien Assistant - {user_email}")
        window.show()
        return window
    except Exception as e:
        logger.error(f"Failed to launch application: {e}")
        QMessageBox.critical(None, "Launch Error", 
            f"Failed to launch application:\n{str(e)}")
        return None

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Medical Lien Assistant")
    
    # Check if first run
    if should_show_setup_wizard():
        # First run - show setup wizard
        wizard = UserSetupWizard()
        if wizard.exec_():
            user_email = wizard.user_email
            if user_email:
                # Launch main app with configured user
                window = launch_main_application(user_email)
                if window:
                    sys.exit(app.exec_())
        sys.exit(0)
    else:
        # Show user selection dialog
        dialog = UserSelectionDialog()
        if dialog.exec_():
            user_email = dialog.selected_user
            if user_email:
                # Launch main app with selected user
                window = launch_main_application(user_email)
                if window:
                    sys.exit(app.exec_())
        sys.exit(0)

if __name__ == "__main__":
    main()