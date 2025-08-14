#!/usr/bin/env python3
"""
Prohealth Medical Lien Automation Assistant - GUI Application
Modern PyQt5-based graphical interface
"""

import sys
import os
import logging
import json
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTabWidget, QPushButton, QTextEdit, 
                            QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
                            QMessageBox, QFileDialog, QProgressBar, QSplitter,
                            QGroupBox, QComboBox, QSpinBox, QCheckBox,
                            QHeaderView, QTextBrowser, QListWidget, QDockWidget,
                            QToolBar, QStatusBar, QMenu, QAction, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QPalette, QColor

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import your existing modules
from config import Config
from utils.logging_config import setup_logging
from services.gmail_service import GmailService
from services.ai_service import AIService
from services.email_cache_service import EmailCacheService
from services.collections_tracker import CollectionsTracker
from services.bulk_email_service import BulkEmailService
from case_manager import CaseManager


class WorkerThread(QThread):
    """Worker thread for background operations"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.function(*self.args, **self.kwargs)
            self.result.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CaseSearchWidget(QWidget):
    """Widget for searching and displaying cases"""
    
    def __init__(self, case_manager):
        super().__init__()
        self.case_manager = case_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by PV#, Name, or CMS#...")
        self.search_button = QPushButton("Search")
        self.refresh_button = QPushButton("Refresh Cases")
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.refresh_button)
        
        # Case table
        self.case_table = QTableWidget()
        self.case_table.setColumnCount(7)
        self.case_table.setHorizontalHeaderLabels([
            "PV #", "Name", "CMS #", "Date of Injury", 
            "Attorney Email", "Law Firm", "Status"
        ])
        self.case_table.horizontalHeader().setStretchLastSection(True)
        self.case_table.setAlternatingRowColors(True)
        self.case_table.setSortingEnabled(True)
        
        layout.addLayout(search_layout)
        layout.addWidget(self.case_table)
        
        self.setLayout(layout)
        
        # Connect signals
        self.search_button.clicked.connect(self.search_cases)
        self.search_input.returnPressed.connect(self.search_cases)
        self.refresh_button.clicked.connect(self.load_all_cases)
        
        # Load cases on startup
        self.load_all_cases()
    
    def load_all_cases(self):
        """Load all cases into the table"""
        try:
            # Format each row using the case_manager's format_case method
            cases = []
            for _, row in self.case_manager.df.iterrows():
                case = self.case_manager.format_case(row)
                cases.append(case)
            self.populate_table(cases)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load cases: {str(e)}")
    
    def search_cases(self):
        """Search for cases based on input"""
        search_term = self.search_input.text().strip()
        if not search_term:
            self.load_all_cases()
            return
        
        try:
            # Search in multiple fields
            results = self.case_manager.search_case(search_term)
            if results:
                self.populate_table([results] if isinstance(results, dict) else results)
            else:
                QMessageBox.information(self, "No Results", "No cases found matching your search.")
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"Error searching cases: {str(e)}")
    
    def populate_table(self, cases):
        """Populate the table with case data"""
        self.case_table.setRowCount(len(cases))
        
        for row, case in enumerate(cases):
            self.case_table.setItem(row, 0, QTableWidgetItem(str(case.get('PV', ''))))
            self.case_table.setItem(row, 1, QTableWidgetItem(str(case.get('Name', ''))))
            self.case_table.setItem(row, 2, QTableWidgetItem(str(case.get('CMS', ''))))
            self.case_table.setItem(row, 3, QTableWidgetItem(str(case.get('DOI', ''))))
            self.case_table.setItem(row, 4, QTableWidgetItem(str(case.get('Attorney Email', ''))))
            self.case_table.setItem(row, 5, QTableWidgetItem(str(case.get('Law Firm', ''))))
            self.case_table.setItem(row, 6, QTableWidgetItem("Active"))
        
        self.case_table.resizeColumnsToContents()
    
    def get_selected_case(self):
        """Get the currently selected case"""
        current_row = self.case_table.currentRow()
        if current_row >= 0:
            case_data = {}
            headers = ["PV", "Name", "CMS", "DOI", "Attorney Email", "Law Firm", "Status"]
            for col, header in enumerate(headers):
                item = self.case_table.item(current_row, col)
                if item:
                    case_data[header] = item.text()
            return case_data
        return None


class EmailAnalysisWidget(QWidget):
    """Widget for email search and analysis"""
    
    def __init__(self, gmail_service, ai_service):
        super().__init__()
        self.gmail_service = gmail_service
        self.ai_service = ai_service
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Email search section
        search_group = QGroupBox("Email Search")
        search_layout = QVBoxLayout()
        
        # Search input
        search_input_layout = QHBoxLayout()
        self.email_search_input = QLineEdit()
        self.email_search_input.setPlaceholderText("Enter search query...")
        self.search_emails_button = QPushButton("Search Emails")
        
        search_input_layout.addWidget(self.email_search_input)
        search_input_layout.addWidget(self.search_emails_button)
        
        # Results display
        self.email_results = QTextBrowser()
        self.email_results.setMinimumHeight(200)
        
        search_layout.addLayout(search_input_layout)
        search_layout.addWidget(QLabel("Results:"))
        search_layout.addWidget(self.email_results)
        
        search_group.setLayout(search_layout)
        
        # AI Summary section
        summary_group = QGroupBox("AI Analysis")
        summary_layout = QVBoxLayout()
        
        self.generate_summary_button = QPushButton("Generate Summary")
        self.summary_display = QTextBrowser()
        self.summary_display.setMinimumHeight(300)
        
        summary_layout.addWidget(self.generate_summary_button)
        summary_layout.addWidget(self.summary_display)
        
        summary_group.setLayout(summary_layout)
        
        # Add to main layout
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(search_group)
        splitter.addWidget(summary_group)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # Connect signals
        self.search_emails_button.clicked.connect(self.search_emails)
        self.generate_summary_button.clicked.connect(self.generate_summary)
    
    def search_emails(self):
        """Search for emails based on query"""
        query = self.email_search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search query.")
            return
        
        try:
            self.email_results.append(f"Searching for: {query}\\n")
            # Implement email search logic here
            messages = self.gmail_service.search_messages(query, max_results=10)
            
            if messages:
                self.email_results.append(f"Found {len(messages)} emails:\\n")
                for msg in messages:
                    self.email_results.append(f"- {msg.get('subject', 'No subject')}\\n")
            else:
                self.email_results.append("No emails found.\\n")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Email search failed: {str(e)}")
    
    def generate_summary(self):
        """Generate AI summary of emails"""
        try:
            self.summary_display.append("Generating AI summary...\\n")
            # Implement AI summary generation here
            # This would use the AI service to analyze emails
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Summary generation failed: {str(e)}")


class EmailComposerWidget(QWidget):
    """Widget for composing and sending emails"""
    
    def __init__(self, gmail_service, ai_service):
        super().__init__()
        self.gmail_service = gmail_service
        self.ai_service = ai_service
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Email composition form
        form_layout = QVBoxLayout()
        
        # To field
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_input = QLineEdit()
        to_layout.addWidget(self.to_input)
        
        # Subject field
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        subject_layout.addWidget(self.subject_input)
        
        # Email type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Email Type:"))
        self.email_type = QComboBox()
        self.email_type.addItems(["Follow-up", "Status Request", "Initial Contact", "Custom"])
        type_layout.addWidget(self.email_type)
        
        # AI assistance button
        self.ai_draft_button = QPushButton("Generate AI Draft")
        
        # Email body
        self.email_body = QTextEdit()
        self.email_body.setMinimumHeight(300)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.send_button = QPushButton("Send Email")
        self.save_draft_button = QPushButton("Save Draft")
        self.clear_button = QPushButton("Clear")
        
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.save_draft_button)
        button_layout.addWidget(self.clear_button)
        
        # Add all to layout
        form_layout.addLayout(to_layout)
        form_layout.addLayout(subject_layout)
        form_layout.addLayout(type_layout)
        form_layout.addWidget(self.ai_draft_button)
        form_layout.addWidget(QLabel("Message:"))
        form_layout.addWidget(self.email_body)
        form_layout.addLayout(button_layout)
        
        layout.addLayout(form_layout)
        self.setLayout(layout)
        
        # Connect signals
        self.ai_draft_button.clicked.connect(self.generate_ai_draft)
        self.send_button.clicked.connect(self.send_email)
        self.save_draft_button.clicked.connect(self.save_draft)
        self.clear_button.clicked.connect(self.clear_form)
    
    def generate_ai_draft(self):
        """Generate email draft using AI"""
        email_type = self.email_type.currentText()
        try:
            # Implement AI draft generation based on email type
            draft = f"AI-generated {email_type} email draft will appear here..."
            self.email_body.setText(draft)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate draft: {str(e)}")
    
    def send_email(self):
        """Send the composed email"""
        to = self.to_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.email_body.toPlainText()
        
        if not all([to, subject, body]):
            QMessageBox.warning(self, "Warning", "Please fill in all fields.")
            return
        
        try:
            # Implement email sending logic
            QMessageBox.information(self, "Success", "Email sent successfully!")
            self.clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")
    
    def save_draft(self):
        """Save email as draft"""
        QMessageBox.information(self, "Draft Saved", "Email saved as draft.")
    
    def clear_form(self):
        """Clear all form fields"""
        self.to_input.clear()
        self.subject_input.clear()
        self.email_body.clear()
        self.email_type.setCurrentIndex(0)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Prohealth", "AIAssistant")
        self.init_services()
        self.init_ui()
        self.load_settings()
    
    def init_services(self):
        """Initialize backend services"""
        try:
            setup_logging()
            
            # Initialize AI service first (needed by other services)
            self.ai_service = AIService()
            
            # Try to initialize Gmail service, but allow GUI to run without it
            try:
                self.gmail_service = GmailService()
            except Exception as gmail_error:
                self.gmail_service = None
                QMessageBox.warning(None, "Gmail Service", 
                                  f"Gmail service not available: {str(gmail_error)}\\n\\n"
                                  "Run 'python ai_assistant\\\\gmail_auth_refresh.py' to authenticate.\\n"
                                  "Email features will be disabled.")
            
            # Initialize other services
            self.case_manager = CaseManager()
            self.email_cache_service = EmailCacheService()
            self.collections_tracker = CollectionsTracker()
            
            # Initialize bulk email service only if Gmail is available
            if self.gmail_service:
                self.bulk_email_service = BulkEmailService(
                    self.gmail_service, 
                    self.case_manager, 
                    self.ai_service, 
                    self.collections_tracker
                )
            else:
                self.bulk_email_service = None
            
        except Exception as e:
            QMessageBox.critical(None, "Initialization Error", 
                               f"Failed to initialize core services: {str(e)}\\n\\n"
                               "Please check your configuration and try again.")
            sys.exit(1)
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Prohealth AI Assistant - Medical Lien Case Management")
        self.setGeometry(100, 100, 1400, 900)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #4CAF50;
            }
            QPushButton {
                padding: 6px 12px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Add tabs
        self.case_search_tab = CaseSearchWidget(self.case_manager)
        self.email_analysis_tab = EmailAnalysisWidget(self.gmail_service, self.ai_service)
        self.email_composer_tab = EmailComposerWidget(self.gmail_service, self.ai_service)
        
        self.tabs.addTab(self.case_search_tab, "Case Search")
        self.tabs.addTab(self.email_analysis_tab, "Email Analysis")
        self.tabs.addTab(self.email_composer_tab, "Compose Email")
        
        # Add collections tracker tab
        self.collections_tab = self.create_collections_tab()
        self.tabs.addTab(self.collections_tab, "Collections Tracker")
        
        # Add bulk operations tab
        self.bulk_ops_tab = self.create_bulk_operations_tab()
        self.tabs.addTab(self.bulk_ops_tab, "Bulk Operations")
        
        # Add settings tab
        self.settings_tab = self.create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Settings")
        
        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        
        # Create dock widgets
        self.create_dock_widgets()
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Cases File", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_cases_file)
        
        export_action = QAction("Export Results", self)
        export_action.setShortcut("Ctrl+E")
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(open_action)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        preferences_action = QAction("Preferences", self)
        preferences_action.triggered.connect(self.show_preferences)
        
        edit_menu.addAction(preferences_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        sync_action = QAction("Sync with Gmail", self)
        cache_action = QAction("Clear Cache", self)
        
        tools_menu.addAction(sync_action)
        tools_menu.addAction(cache_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add toolbar actions
        refresh_action = QAction("Refresh", self)
        search_action = QAction("Search", self)
        compose_action = QAction("Compose", self)
        
        toolbar.addAction(refresh_action)
        toolbar.addAction(search_action)
        toolbar.addAction(compose_action)
        toolbar.addSeparator()
    
    def create_dock_widgets(self):
        """Create dockable widgets"""
        # Activity log dock
        log_dock = QDockWidget("Activity Log", self)
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(150)
        log_dock.setWidget(self.log_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)
        
        # Quick actions dock
        actions_dock = QDockWidget("Quick Actions", self)
        actions_widget = QWidget()
        actions_layout = QVBoxLayout()
        
        quick_search_btn = QPushButton("Quick Search")
        quick_draft_btn = QPushButton("Quick Draft")
        quick_summary_btn = QPushButton("Generate Summary")
        
        actions_layout.addWidget(quick_search_btn)
        actions_layout.addWidget(quick_draft_btn)
        actions_layout.addWidget(quick_summary_btn)
        actions_layout.addStretch()
        
        actions_widget.setLayout(actions_layout)
        actions_dock.setWidget(actions_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, actions_dock)
    
    def create_collections_tab(self):
        """Create collections tracker tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Collections overview
        overview_group = QGroupBox("Collections Overview")
        overview_layout = QVBoxLayout()
        
        stats_layout = QHBoxLayout()
        self.total_cases_label = QLabel("Total Cases: 0")
        self.contacted_label = QLabel("Contacted: 0")
        self.pending_label = QLabel("Pending: 0")
        
        stats_layout.addWidget(self.total_cases_label)
        stats_layout.addWidget(self.contacted_label)
        stats_layout.addWidget(self.pending_label)
        
        overview_layout.addLayout(stats_layout)
        
        # Collections table
        self.collections_table = QTableWidget()
        self.collections_table.setColumnCount(6)
        self.collections_table.setHorizontalHeaderLabels([
            "PV #", "Name", "Last Contact", "Status", "Days Since Contact", "Action"
        ])
        
        overview_layout.addWidget(self.collections_table)
        overview_group.setLayout(overview_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.track_collections_btn = QPushButton("Track Collections")
        self.export_collections_btn = QPushButton("Export Report")
        
        button_layout.addWidget(self.track_collections_btn)
        button_layout.addWidget(self.export_collections_btn)
        
        layout.addWidget(overview_group)
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        return widget
    
    def create_bulk_operations_tab(self):
        """Create bulk operations tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Bulk email section
        bulk_email_group = QGroupBox("Bulk Email Operations")
        bulk_layout = QVBoxLayout()
        
        # Template selection
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(["Follow-up", "Status Request", "Initial Contact"])
        template_layout.addWidget(self.template_combo)
        
        # Recipients selection
        self.recipients_list = QListWidget()
        self.recipients_list.setSelectionMode(QListWidget.MultiSelection)
        
        # Send button
        self.send_bulk_btn = QPushButton("Send Bulk Emails")
        
        bulk_layout.addLayout(template_layout)
        bulk_layout.addWidget(QLabel("Select Recipients:"))
        bulk_layout.addWidget(self.recipients_list)
        bulk_layout.addWidget(self.send_bulk_btn)
        
        bulk_email_group.setLayout(bulk_layout)
        
        layout.addWidget(bulk_email_group)
        widget.setLayout(layout)
        return widget
    
    def create_settings_tab(self):
        """Create settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # API Settings
        api_group = QGroupBox("API Configuration")
        api_layout = QVBoxLayout()
        
        # OpenAI API Key
        openai_layout = QHBoxLayout()
        openai_layout.addWidget(QLabel("OpenAI API Key:"))
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.Password)
        openai_layout.addWidget(self.openai_key_input)
        
        # Gmail settings
        gmail_layout = QHBoxLayout()
        gmail_layout.addWidget(QLabel("Gmail Credentials:"))
        self.gmail_creds_path = QLineEdit()
        self.browse_creds_btn = QPushButton("Browse...")
        gmail_layout.addWidget(self.gmail_creds_path)
        gmail_layout.addWidget(self.browse_creds_btn)
        
        api_layout.addLayout(openai_layout)
        api_layout.addLayout(gmail_layout)
        api_group.setLayout(api_layout)
        
        # General Settings
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout()
        
        # Auto-refresh
        self.auto_refresh_check = QCheckBox("Enable Auto-refresh")
        refresh_interval_layout = QHBoxLayout()
        refresh_interval_layout.addWidget(QLabel("Refresh Interval (minutes):"))
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setMinimum(1)
        self.refresh_interval_spin.setMaximum(60)
        self.refresh_interval_spin.setValue(5)
        refresh_interval_layout.addWidget(self.refresh_interval_spin)
        
        general_layout.addWidget(self.auto_refresh_check)
        general_layout.addLayout(refresh_interval_layout)
        general_group.setLayout(general_layout)
        
        # Save button
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_settings)
        
        layout.addWidget(api_group)
        layout.addWidget(general_group)
        layout.addWidget(self.save_settings_btn)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def open_cases_file(self):
        """Open a cases Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Cases File", "", "Excel Files (*.xlsx *.xls)")
        
        if file_path:
            try:
                # Load the new cases file
                self.case_manager = CaseManager(file_path)
                self.case_search_tab.case_manager = self.case_manager
                self.case_search_tab.load_all_cases()
                self.status_bar.showMessage(f"Loaded cases from {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load cases: {str(e)}")
    
    def show_preferences(self):
        """Show preferences dialog"""
        self.tabs.setCurrentWidget(self.settings_tab)
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", 
                         "Prohealth AI Assistant\\n\\n"
                         "Medical Lien Case Management System\\n"
                         "Version 1.0.0\\n\\n"
                         "Powered by OpenAI GPT-4 and Gmail API")
    
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("openai_key", self.openai_key_input.text())
        self.settings.setValue("gmail_creds", self.gmail_creds_path.text())
        self.settings.setValue("auto_refresh", self.auto_refresh_check.isChecked())
        self.settings.setValue("refresh_interval", self.refresh_interval_spin.value())
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
    
    def load_settings(self):
        """Load application settings"""
        self.openai_key_input.setText(self.settings.value("openai_key", ""))
        self.gmail_creds_path.setText(self.settings.value("gmail_creds", ""))
        self.auto_refresh_check.setChecked(self.settings.value("auto_refresh", False, type=bool))
        self.refresh_interval_spin.setValue(self.settings.value("refresh_interval", 5, type=int))
    
    def log_activity(self, message):
        """Log activity to the activity log widget"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_widget.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        cursor = self.log_widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_widget.setTextCursor(cursor)


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Prohealth AI Assistant")
    app.setOrganizationName("Prohealth")
    
    # Set application icon if available
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()