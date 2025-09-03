#!/usr/bin/env python3
"""
Prohealth Medical Lien Automation Assistant - Enhanced GUI Application
Complete PyQt5 interface with all main_new.py functionality and dark mode
"""

import sys
import os
import logging
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import pytz
import shutil
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QDateEdit
from PyQt5.QtCore import *
from PyQt5.QtCore import QTimer, QThread, QDate
from PyQt5.QtGui import *
from PyQt5.QtGui import QColor

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import your existing modules
from config import Config
from utils.logging_config import setup_logging, log_sent_email
try:
    from utils.error_tracker import initialize_error_tracker, get_error_tracker
    from utils.safe_execution import safe_execute, SafeExecutionContext
    ERROR_TRACKING_AVAILABLE = True
except ImportError:
    ERROR_TRACKING_AVAILABLE = False
from services.gmail_service import GmailService
from services.ai_service import AIService
from services.email_cache_service import EmailCacheService
from services.collections_tracker import CollectionsTracker
from services.bulk_email_service import BulkEmailService
from services.case_acknowledgment_service import CaseAcknowledgmentService
from services.template_summary_service import TemplateSummaryService
from utils.progress_manager import ProgressManager, ProgressContext, with_progress
from utils.threaded_operations import EmailCacheWorker, GmailSearchWorker, CategorizeWorker, CollectionsAnalyzerWorker
try:
    from services.cms_integration import add_cms_note_for_email, process_session_cms_notes, get_session_stats
    CMS_AVAILABLE = True
except ImportError:
    CMS_AVAILABLE = False
    add_cms_note_for_email = None
    process_session_cms_notes = None
    get_session_stats = None

# Setup logger
logger = logging.getLogger(__name__)
from case_manager import CaseManager
# EnhancedCollectionsTracker removed - using basic CollectionsTracker
EnhancedCollectionsTracker = None


class WorkerThread(QThread):
    """Worker thread for background operations"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    
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


class CategoriesWidget(QWidget):
    """Widget for displaying cases organized by categories"""
    
    def __init__(self, collections_tracker, case_manager, parent=None):
        super().__init__(parent)
        self.collections_tracker = collections_tracker
        self.case_manager = case_manager
        self.parent_window = parent
        self.ack_service = CaseAcknowledgmentService()
        self.category_data = {}  # Store original data for filtering
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header with refresh button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>📂 Case Categories</h2>"))
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh Categories")
        self.refresh_btn.clicked.connect(self.refresh_analysis)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Balance filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Balance Filter:"))
        
        self.balance_filter_combo = QComboBox()
        self.balance_filter_combo.addItems(["All", "Above", "Below"])
        self.balance_filter_combo.currentTextChanged.connect(self.apply_balance_filter)
        filter_layout.addWidget(self.balance_filter_combo)
        
        self.balance_threshold = QLineEdit()
        self.balance_threshold.setPlaceholderText("Enter amount (e.g., 5000)")
        self.balance_threshold.setMaximumWidth(150)
        self.balance_threshold.textChanged.connect(self.apply_balance_filter)
        filter_layout.addWidget(self.balance_threshold)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Category tabs
        self.category_tabs = QTabWidget()
        
        # Critical cases tab (90+ days no response)
        self.critical_widget = self.create_category_widget("critical", "🚨 Critical (90+ days no response)")
        self.category_tabs.addTab(self.critical_widget, "Critical")
        
        # High priority tab (60+ days no response)
        self.high_priority_widget = self.create_category_widget("high_priority", "🔥 High Priority (60+ days no response)")
        self.category_tabs.addTab(self.high_priority_widget, "High Priority")
        
        # No response tab (30+ days no response)
        self.no_response_widget = self.create_category_widget("no_response", "📋 No Response (30+ days)")
        self.category_tabs.addTab(self.no_response_widget, "No Response")
        
        # Never contacted tab
        self.never_contacted_widget = self.create_category_widget("never_contacted", "📝 Never Contacted")
        self.category_tabs.addTab(self.never_contacted_widget, "Never Contacted")
        
        # Recently Sent tab (sent within last 30 days)
        self.recently_sent_widget = self.create_category_widget("recently_sent", "📧 Recently Sent (<30 days)")
        self.category_tabs.addTab(self.recently_sent_widget, "Recently Sent")
        
        # Missing DOI tab
        self.missing_doi_widget = self.create_category_widget("missing_doi", "❓ Missing DOI")
        self.category_tabs.addTab(self.missing_doi_widget, "Missing DOI")
        
        # CCP 335.1 tab (cases over 2 years old with no litigation status)
        self.ccp_335_1_widget = self.create_category_widget("ccp_335_1", "⚖️ CCP 335.1 (>2yr Statute)")
        self.category_tabs.addTab(self.ccp_335_1_widget, "CCP 335.1")
        
        # Summary statistics
        self.stats_label = QLabel()
        self.update_stats()
        
        layout.addWidget(self.stats_label)
        layout.addWidget(self.category_tabs)
        
        self.setLayout(layout)
    
    def create_category_widget(self, category, title):
        """Create a widget for a specific case category"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Title and count
        title_label = QLabel(f"<h3>{title}</h3>")
        layout.addWidget(title_label)
        
        # Table for cases
        table = QTableWidget()
        table.setObjectName(f"{category}_table")
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "PV #", "Name", "Balance", "Days Since Contact", "Law Firm", 
            "Attorney Email", "Status", "Acknowledged", "Actions"
        ])
        table.horizontalHeader().setStretchLastSection(False)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        process_btn = QPushButton(f"Process {title.split()[0]} Cases")
        process_btn.clicked.connect(lambda: self.process_category(category))
        
        export_btn = QPushButton("Export to Excel")
        export_btn.clicked.connect(lambda: self.export_category(category))
        
        button_layout.addWidget(process_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        
        layout.addWidget(table)
        layout.addLayout(button_layout)
        
        widget.setLayout(layout)
        return widget
    
    def refresh_analysis(self):
        """Refresh the case categories"""
        try:
            # Ensure email cache is set on tracker if available
            if hasattr(self.parent_window, 'email_cache_service'):
                if not hasattr(self.collections_tracker, 'email_cache'):
                    self.collections_tracker.email_cache = self.parent_window.email_cache_service
                    
            # Use enhanced progress with live logs
            with ProgressContext(self.parent_window, "Refreshing Analysis", "Analyzing case categories...", 
                               pulse=False, maximum=100, show_logs=True) as progress:
                
                # Clear cache to force fresh analysis
                progress.set_message("Clearing cache...")
                progress.log("🗑️ Clearing category cache")
                self.collections_tracker.clear_stale_cache()
                progress.process_events()
                
                # Get comprehensive case categories with enhanced progress
                progress.log("🔍 Analyzing case activity patterns")
                
                def update_progress(msg, pct):
                    progress.update(pct if pct > 0 else progress.dialog.progress_bar.value(), msg)
                    if "Found" in msg or "Processing" in msg:
                        progress.log(msg)
                    progress.process_events()
                
                case_categories = self.collections_tracker.get_comprehensive_stale_cases(
                    self.case_manager,
                    exclude_acknowledged=True,
                    progress_callback=update_progress,
                    skip_email_search=True  # Use cached data for fast refresh
                )
                
                # Debug logging to see what categories we got
                logger.info(f"Categories returned: {case_categories.keys()}")
                for cat_name, cat_cases in case_categories.items():
                    logger.info(f"Category '{cat_name}': {len(cat_cases)} cases")
                
                # Store data for filtering
                progress.update(60, "Processing case data...")
                progress.log("📦 Processing case categories")
                self.category_data = case_categories
                progress.process_events()
                
                # Apply current filter and update tables
                progress.update(80, "Applying filters and updating display...")
                progress.log("🎯 Applying balance filters")
                self.apply_balance_filter()
                progress.process_events()
                
                # Update statistics
                progress.update(95, "Updating statistics...")
                progress.log("📊 Calculating statistics")
                self.update_stats()
                
                progress.update(100, "Analysis complete!")
                progress.log("✅ Category analysis complete")
            
            QMessageBox.information(self, "Success", "Categories refreshed!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh analysis: {str(e)}")
    
    def update_category_table(self, category, cases):
        """Update a specific category table with cases"""
        # Find the table widget
        widget = self.findChild(QTableWidget, f"{category}_table")
        if not widget:
            return
        
        # Clear existing rows to ensure clean state
        widget.setRowCount(0)
        
        # DEBUG: Log what we're updating
        print(f"[DEBUG] Updating {category} table with {len(cases)} cases")
        if cases:
            print(f"[DEBUG] First case: PV={cases[0].get('pv')}, Name={cases[0].get('name')}")
            if len(cases) > 1:
                print(f"[DEBUG] Last case: PV={cases[-1].get('pv')}, Name={cases[-1].get('name')}")
        
        widget.setRowCount(len(cases))
        
        for row, case in enumerate(cases):
            # CRITICAL: Capture all case data at the start to ensure consistency
            pv = str(case.get('pv', ''))
            name = str(case.get('name', ''))
            status = str(case.get('status', 'Unknown'))
            
            # PV #
            widget.setItem(row, 0, QTableWidgetItem(pv))
            
            # Name
            widget.setItem(row, 1, QTableWidgetItem(name))
            
            # Balance - format as currency
            balance = case.get('balance', 0.0)
            if isinstance(balance, (int, float)):
                balance_item = QTableWidgetItem(f"${balance:,.2f}")
                # Store raw value for sorting
                balance_item.setData(Qt.UserRole, balance)
            else:
                balance_item = QTableWidgetItem("$0.00")
                balance_item.setData(Qt.UserRole, 0.0)
            widget.setItem(row, 2, balance_item)
            
            # Days since contact
            days = case.get('days_since_contact', 'Never')
            widget.setItem(row, 3, QTableWidgetItem(str(days) if days else 'Never'))
            
            # Law Firm
            widget.setItem(row, 4, QTableWidgetItem(str(case.get('law_firm', ''))))
            
            # Attorney Email
            widget.setItem(row, 5, QTableWidgetItem(str(case.get('attorney_email', ''))))
            
            # Status
            widget.setItem(row, 6, QTableWidgetItem(status))
            
            # Acknowledgment status
            ack_info = self.ack_service.get_acknowledgment_info(pv)
            if ack_info:
                ack_text = f"✅ {ack_info.get('reason', 'Acknowledged')[:20]}..."
                ack_item = QTableWidgetItem(ack_text)
                ack_item.setForeground(QColor(0, 200, 0))
                widget.setItem(row, 7, ack_item)
            else:
                widget.setItem(row, 7, QTableWidgetItem(""))
            
            # Actions button
            action_btn = QPushButton("Actions")
            action_menu = QMenu()
            
            # CRITICAL: Create a helper function to ensure proper value capture
            def create_action_handler(func, *args):
                """Helper to properly capture values for action handlers"""
                return lambda checked=False: func(*args)
            
            # Add actions with properly captured values
            summarize_action = action_menu.addAction("📄 Summarize")
            # DEBUG: Print what PV we're capturing
            print(f"[DEBUG] Creating actions for row {row}: PV={pv}, Name={name}")
            summarize_action.triggered.connect(create_action_handler(self.summarize_case, pv))
            
            followup_action = action_menu.addAction("✉️ Draft Follow-up")
            followup_action.triggered.connect(create_action_handler(self.draft_followup, pv))
            
            status_action = action_menu.addAction("📮 Draft Status Request")
            status_action.triggered.connect(create_action_handler(self.draft_status_request, pv))
            
            # Add CCP 335.1 action if in CCP 335.1 category
            if category == "ccp_335_1":
                ccp_action = action_menu.addAction("⚖️ Send CCP 335.1 Inquiry")
                # Make a copy of case data to avoid reference issues
                case_copy = dict(case)
                ccp_action.triggered.connect(create_action_handler(self.send_ccp_335_1_inquiry, pv, case_copy))
            
            action_menu.addSeparator()
            
            # Acknowledgment actions
            if ack_info:
                unack_action = action_menu.addAction("❌ Remove Acknowledgment")
                unack_action.triggered.connect(create_action_handler(self.unacknowledge_case, pv))
                
                extend_action = action_menu.addAction("⏰ Extend Snooze")
                extend_action.triggered.connect(create_action_handler(self.extend_snooze, pv))
            else:
                ack_action = action_menu.addAction("✅ Acknowledge Case")
                ack_action.triggered.connect(create_action_handler(self.acknowledge_case, pv, name, status))
            
            action_btn.setMenu(action_menu)
            widget.setCellWidget(row, 8, action_btn)
        
        widget.resizeColumnsToContents()
    
    def update_stats(self):
        """Update statistics label"""
        try:
            dashboard = self.collections_tracker.get_collections_dashboard()
            
            # Get CCP 335.1 count from category data if available
            ccp_335_1_count = len(self.category_data.get('ccp_335_1', [])) if hasattr(self, 'category_data') else 0
            
            stats_text = f"""
            <b>📊 Collections Overview:</b><br>
            Total tracked cases: {dashboard['total_cases']}<br>
            Cases 30+ days old: {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['30_days']}<br>
            Cases 60+ days old: {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['60_days']}<br>
            Cases 90+ days old: {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['90_days']}<br>
            CCP 335.1 eligible: {ccp_335_1_count}
            """
            
            self.stats_label.setText(stats_text)
            
        except Exception as e:
            self.stats_label.setText(f"Error loading statistics: {str(e)}")
    
    def apply_balance_filter(self):
        """Apply balance filter to all category tables"""
        try:
            filter_type = self.balance_filter_combo.currentText() if hasattr(self, 'balance_filter_combo') else "All"
            threshold_text = self.balance_threshold.text() if hasattr(self, 'balance_threshold') else ""
            
            threshold = 0.0
            if threshold_text:
                try:
                    threshold = float(threshold_text.replace(',', '').replace('$', ''))
                except ValueError:
                    threshold = 0.0
            
            # Apply filter to each category
            for category in ["critical", "high_priority", "no_response", "recently_sent", "never_contacted", "missing_doi", "ccp_335_1"]:
                cases = self.category_data.get(category, [])
                
                # Add balance information to each case
                filtered_cases = []
                for case in cases:
                    # Get full case data with balance
                    pv = case.get('pv')
                    if pv:
                        full_case = self.case_manager.get_case_by_pv(pv)
                        if full_case:
                            case['balance'] = full_case.get('Balance', 0.0)
                    
                    # Apply filter
                    balance = case.get('balance', 0.0)
                    if filter_type == "All":
                        filtered_cases.append(case)
                    elif filter_type == "Above" and balance >= threshold:
                        filtered_cases.append(case)
                    elif filter_type == "Below" and balance <= threshold:
                        filtered_cases.append(case)
                
                # Update table with filtered cases
                self.update_category_table(category, filtered_cases)
                
        except Exception as e:
            print(f"Error applying balance filter: {e}")
    
    def process_category(self, category):
        """Process all cases in a category"""
        # This would trigger bulk email processing for the category
        if self.parent_window:
            self.parent_window.process_bulk_category(category)
    
    def move_case_from_acknowledged(self, pv):
        """Move a case back from acknowledged to the appropriate category"""
        try:
            # For now, just trigger a refresh since determining the right category is complex
            # In the future, we could analyze the case and add it to the right category
            self.refresh_analysis()
            
            # Log the activity
            if self.parent_window:
                self.parent_window.log_activity(f"Removed acknowledgment for PV {pv}")
                
        except Exception as e:
            print(f"Error moving case from acknowledged: {e}")
    
    def move_case_to_acknowledged(self, pv, acknowledgment_data):
        """Move a case to the acknowledged section without refreshing"""
        try:
            # Remove from all category displays
            self.remove_case_from_display(pv)
            
            # Add to the main acknowledged tab (it's a sibling tab, not a child)
            if self.parent_window and hasattr(self.parent_window, 'acknowledged_cases_tab'):
                acknowledged_widget = self.parent_window.acknowledged_cases_tab
                if hasattr(acknowledged_widget, 'add_acknowledged_case'):
                    # Get case details for the acknowledged display
                    case = self.case_manager.get_case_by_pv(pv)
                    if case:
                        acknowledged_widget.add_acknowledged_case(pv, case, acknowledgment_data)
            
            # Log the activity
            if self.parent_window:
                self.parent_window.log_activity(f"Moved PV {pv} to acknowledged cases")
                
        except Exception as e:
            print(f"Error moving case to acknowledged: {e}")
    
    def remove_case_from_display(self, pv):
        """Remove a case from the current category display after email sent"""
        try:
            print(f"[DEBUG] Removing PV {pv} from category displays")
            
            # Find and remove the case from all category tables
            for category in ["critical", "high_priority", "no_response", "recently_sent", "never_contacted", "missing_doi", "ccp_335_1"]:
                if category in self.category_data:
                    # Remove the case from the category data
                    original_count = len(self.category_data[category])
                    self.category_data[category] = [c for c in self.category_data[category] if str(c.get('pv')) != str(pv)]
                    
                    # If we removed something, update just that row
                    if len(self.category_data[category]) < original_count:
                        print(f"[DEBUG] Removed PV {pv} from {category}")
                        
                        # Find the table widget for this category
                        widget = self.findChild(QTableWidget, f"{category}_table")
                        if widget:
                            # Find and remove only the specific row
                            for row in range(widget.rowCount()):
                                item = widget.item(row, 0)  # PV is in column 0
                                if item and str(item.text()) == str(pv):
                                    widget.removeRow(row)
                                    print(f"[DEBUG] Removed row {row} from {category} table")
                                    break
                        
                        # Update the category tab title with new count
                        for i in range(self.category_tabs.count()):
                            tab_text = self.category_tabs.tabText(i)
                            if category in tab_text.lower().replace(' ', '_'):
                                new_count = len(self.category_data[category])
                                # Extract the category name without the count
                                category_name = tab_text.split('(')[0].strip()
                                self.category_tabs.setTabText(i, f"{category_name} ({new_count})")
                                break
            
            # Update statistics
            self.update_stats()
            
            # Log the removal
            if self.parent_window:
                self.parent_window.log_activity(f"Removed PV {pv} from category display")
                
        except Exception as e:
            print(f"Error removing case from display: {e}")
            import traceback
            traceback.print_exc()
    
    def export_category(self, category):
        """Export category cases to Excel"""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, f"Export {category} Cases", 
                f"category_{category}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel Files (*.xlsx)")
            
            if filepath:
                # Get cases for this category
                result = self.collections_tracker.get_stale_cases_by_category(
                    self.case_manager, category, limit=None
                )
                cases = result["cases"]
                
                # Create DataFrame and export
                import pandas as pd
                df = pd.DataFrame(cases)
                df.to_excel(filepath, index=False)
                
                QMessageBox.information(self, "Success", f"Exported {len(cases)} cases to {filepath}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
    
    def summarize_case(self, pv):
        """Trigger case summarization"""
        print(f"[DEBUG] summarize_case called with PV: {pv}")
        # Get the current case data for this PV to ensure we have the right info
        current_case = None
        for category in self.category_data.values():
            for case in category:
                if str(case.get('pv')) == str(pv):
                    current_case = case
                    break
            if current_case:
                break
        
        if current_case:
            print(f"[DEBUG] Found case for PV {pv}: Name={current_case.get('name')}")
        else:
            print(f"[DEBUG] WARNING: Could not find case data for PV {pv} in category_data")
        
        if self.parent_window:
            # Pass reference to this widget so it can be notified when email is sent from summary
            self.parent_window.summarize_case_by_pv(pv, category_widget=self)
    
    def draft_followup(self, pv):
        """Trigger follow-up email draft"""
        if self.parent_window:
            # Pass reference to this widget so it can be notified when email is sent
            self.parent_window.draft_followup_by_pv(pv, category_widget=self)
    
    def draft_status_request(self, pv):
        """Trigger status request draft"""
        if self.parent_window:
            # Pass reference to this widget so it can be notified when email is sent
            self.parent_window.draft_status_request_by_pv(pv, category_widget=self)
    
    def send_ccp_335_1_inquiry(self, pv, case_data):
        """Send CCP 335.1 statute of limitations inquiry"""
        try:
            # Get full case details from case manager
            case = self.case_manager.get_case_by_pv(pv)
            if not case:
                QMessageBox.warning(self, "Case Not Found", f"Could not find case {pv}")
                return
            
            # Prepare case data
            ccp_case_data = {
                'pv': pv,
                'name': case.get('Name', 'Unknown'),
                'doi': case.get('DOI', 'Unknown'),
                'cms': case.get('CMS', 'Unknown'),
                'amount': case.get('Balance', '[AMOUNT]')
            }
            
            # Generate CCP 335.1 email content
            doi = ccp_case_data.get('doi', '')
            # Convert name to title case for proper capitalization
            name_title_case = ' '.join(word.capitalize() for word in str(ccp_case_data.get('name', 'Patient')).split())
            subject = f"CCP 335.1 Statute of Limitations Inquiry - {name_title_case} (PV: {ccp_case_data.get('pv', '')})"
            
            body = f"""Dear Counsel,

In regards to Prohealth Advanced Imaging billing and liens for the above-referenced case.

Our records indicate that the date of injury for this matter was {doi}, which is now over two years ago. Under California Code of Civil Procedure Section 335.1, the statute of limitations for personal injury claims is generally two years from the date of injury.

Could you please provide an update on:
1. Whether litigation has been filed in this matter
2. The current status of any settlement negotiations
3. Whether there are any tolling agreements or other factors that would extend the statute of limitations

We need this information to properly manage our lien and determine next steps. If the statute of limitations has expired without litigation being filed, please advise how you intend to proceed with this matter.

Please respond at your earliest convenience so we can update our records accordingly.

Thank you for your attention to this matter"""
            
            # Get attorney email
            attorney_email = case.get('Attorney Email', '')
            if not attorney_email:
                QMessageBox.warning(self, "No Email", "No attorney email found for this case")
                return
            
            # Show email preview dialog
            dialog = EmailPreviewDialog(attorney_email, subject, body, pv, self)
            dialog.setWindowTitle(f"CCP 335.1 Inquiry - {pv}")
            
            if dialog.exec_() and dialog.approved:
                # Send the email
                if self.parent_window and hasattr(self.parent_window, 'gmail_service'):
                    try:
                        self.parent_window.gmail_service.send_message(
                            dialog.recipient,
                            dialog.email_subject,
                            dialog.email_body
                        )
                        
                        # Log the activity
                        self.parent_window.log_activity(f"Sent CCP 335.1 inquiry for {pv} to {dialog.recipient}")
                        
                        # Add CMS note if available
                        if CMS_AVAILABLE and add_cms_note_for_email:
                            add_cms_note_for_email(
                                pv_number=pv,
                                note_text=f"CCP 335.1 Inquiry sent to {dialog.recipient}",
                                sent_to=dialog.recipient,
                                email_type="ccp_335_1"
                            )
                        
                        QMessageBox.information(self, "Success", f"CCP 335.1 inquiry sent for {pv}")
                        
                        # Update the case as contacted
                        if hasattr(self.collections_tracker, 'mark_case_contacted'):
                            self.collections_tracker.mark_case_contacted(pv, contact_type="email_sent")
                        
                        # Remove from category display immediately (no need to refresh entire analysis)
                        self.remove_case_from_display(pv)
                        
                    except Exception as e:
                        QMessageBox.critical(self, "Send Failed", f"Failed to send email: {str(e)}")
                else:
                    QMessageBox.warning(self, "Gmail Not Available", "Gmail service is not available")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to prepare CCP 335.1 inquiry: {str(e)}")
    
    def acknowledge_case(self, pv, case_name="", status=""):
        """Acknowledge a case with snooze options"""
        dialog = CaseAcknowledgmentDialog(pv, case_name, status, self)
        if dialog.exec_():
            data = dialog.get_acknowledgment_data()
            
            # Get the full case data to retrieve CMS number
            case = self.case_manager.get_case_by_pv(pv)
            cms_number = case.get('CMS') if case else None
            
            success = self.ack_service.acknowledge_case(
                pv=pv,
                reason=data['reason'],
                snooze_days=data['snooze_days'],
                status=status,
                notes=data['notes'],
                cms_number=cms_number
            )
            
            if success:
                QMessageBox.information(self, "Success", f"Case {pv} acknowledged successfully!")
                # Instead of refreshing, just move the case to acknowledged section
                self.move_case_to_acknowledged(pv, data)
            else:
                QMessageBox.critical(self, "Error", f"Failed to acknowledge case {pv}")
    
    def unacknowledge_case(self, pv):
        """Remove acknowledgment from a case"""
        reply = QMessageBox.question(
            self, "Remove Acknowledgment",
            f"Remove acknowledgment for case {pv}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.ack_service.unacknowledge_case(pv):
                QMessageBox.information(self, "Success", f"Acknowledgment removed for case {pv}")
                # Instead of refreshing, remove from acknowledged and add back to categories
                self.move_case_from_acknowledged(pv)
            else:
                QMessageBox.critical(self, "Error", f"Failed to remove acknowledgment")
    
    def extend_snooze(self, pv):
        """Extend the snooze period for an acknowledged case"""
        days, ok = QInputDialog.getInt(
            self, "Extend Snooze",
            f"Extend snooze for case {pv} by how many days?",
            30, 1, 365
        )
        
        if ok:
            if self.ack_service.extend_snooze(pv, days):
                QMessageBox.information(self, "Success", f"Extended snooze by {days} days")
                # No need to refresh, snooze extension doesn't affect display
                if self.parent_window:
                    self.parent_window.log_activity(f"Extended snooze for PV {pv} by {days} days")
            else:
                QMessageBox.critical(self, "Error", "Failed to extend snooze")


class CaseAcknowledgmentDialog(QDialog):
    """Dialog for acknowledging/snoozing cases"""
    
    def __init__(self, case_pv, case_name="", current_status="", parent=None):
        super().__init__(parent)
        self.case_pv = case_pv
        self.case_name = case_name
        self.current_status = current_status
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"Acknowledge Case {self.case_pv}")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Case info
        info_label = QLabel(f"<b>Case:</b> {self.case_pv} - {self.case_name}")
        layout.addWidget(info_label)
        
        if self.current_status:
            status_label = QLabel(f"<b>Current Status:</b> {self.current_status}")
            layout.addWidget(status_label)
        
        layout.addWidget(QLabel("<hr>"))
        
        # Reason selection
        layout.addWidget(QLabel("Reason for acknowledgment:"))
        self.reason_combo = QComboBox()
        self.reason_combo.addItems([
            "LITIGATION - Awaiting outcome",
            "PENDING SETTLEMENT",
            "LIEN NOT SIGNED",
            "CLIENT UNRESPONSIVE",
            "FIRM UNRESPONSIVE - Will retry later",
            "LOW PRIORITY",
            "REVIEWED - No action needed",
            "OTHER (specify below)"
        ])
        layout.addWidget(self.reason_combo)
        
        # Snooze duration
        layout.addWidget(QLabel("Snooze duration:"))
        self.snooze_combo = QComboBox()
        self.snooze_combo.addItems([
            "30 days",
            "60 days",
            "90 days",
            "6 months",
            "1 year",
            "Indefinite (manual review)"
        ])
        layout.addWidget(self.snooze_combo)
        
        # Notes field
        layout.addWidget(QLabel("Additional notes (optional):"))
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(100)
        self.notes_text.setPlaceholderText("Add any additional context or information...")
        layout.addWidget(self.notes_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.acknowledge_btn = QPushButton("✅ Acknowledge Case")
        self.acknowledge_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.acknowledge_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_acknowledgment_data(self):
        """Get the acknowledgment data from the dialog"""
        snooze_map = {
            "30 days": 30,
            "60 days": 60,
            "90 days": 90,
            "6 months": 180,
            "1 year": 365,
            "Indefinite (manual review)": 0
        }
        
        return {
            'reason': self.reason_combo.currentText(),
            'snooze_days': snooze_map.get(self.snooze_combo.currentText(), 30),
            'notes': self.notes_text.toPlainText(),
            'status': self.current_status
        }


class ThreadSelectorDialog(QDialog):
    """Dialog for selecting which email thread to reply to"""
    
    def __init__(self, threads, case, parent=None):
        super().__init__(parent)
        self.threads = threads
        self.case = case
        self.selected_thread = None
        self.start_new_thread = False
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Select Email Thread")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel(f"<h3>Select Email Thread for {self.case.get('Name', '')}</h3>")
        layout.addWidget(header_label)
        
        # Info label
        info_label = QLabel("Choose which email thread to reply to, or start a new conversation:")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Thread list widget with improved selection visibility
        self.thread_list = QListWidget()
        self.thread_list.setSelectionMode(QListWidget.SingleSelection)
        
        # Apply custom stylesheet for better selection visibility
        self.thread_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                border: 2px solid #1976D2;
            }
            QListWidget::item:hover:!selected {
                background-color: #E3F2FD;
            }
        """)
        
        # Add threads to list
        for thread in self.threads:
            item = QListWidgetItem()
            widget = self.create_thread_widget(thread)
            item.setSizeHint(widget.sizeHint())
            self.thread_list.addItem(item)
            self.thread_list.setItemWidget(item, widget)
            item.setData(Qt.UserRole, thread)
        
        # Select first thread by default
        if self.threads:
            self.thread_list.setCurrentRow(0)
        
        layout.addWidget(self.thread_list)
        
        # New thread option
        new_thread_layout = QHBoxLayout()
        self.new_thread_checkbox = QCheckBox("Start a new email thread instead")
        self.new_thread_checkbox.toggled.connect(self.on_new_thread_toggled)
        new_thread_layout.addWidget(self.new_thread_checkbox)
        new_thread_layout.addStretch()
        layout.addLayout(new_thread_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_btn = QPushButton("✅ Select Thread")
        select_btn.clicked.connect(self.accept_selection)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(select_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_thread_widget(self, thread):
        """Create a widget to display thread information"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Parse thread data
        subject = thread.get('subject', 'No Subject')
        last_date = thread.get('last_date', 'Unknown date')
        message_count = thread.get('message_count', 0)
        last_sender = thread.get('last_sender', 'Unknown')
        has_response = thread.get('has_attorney_response', False)
        thread_id = thread.get('thread_id', '')
        snippet = thread.get('snippet', '')
        
        # Thread status indicator
        if has_response:
            status_icon = "✅"
            status_text = "Attorney responded"
            status_color = "#4CAF50"
        else:
            status_icon = "⏳"
            status_text = "Awaiting response"
            status_color = "#FF9800"
        
        # Header with subject and status
        header_layout = QHBoxLayout()
        subject_label = QLabel(f"<b>{subject}</b>")
        header_layout.addWidget(subject_label)
        header_layout.addStretch()
        
        status_label = QLabel(f"{status_icon} {status_text}")
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        header_layout.addWidget(status_label)
        layout.addLayout(header_layout)
        
        # Thread metadata
        meta_text = f"📧 {message_count} messages | Last activity: {last_date} | From: {last_sender}"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(meta_label)
        
        # Snippet preview
        if snippet:
            snippet_label = QLabel(f"<i>{snippet[:150]}{'...' if len(snippet) > 150 else ''}</i>")
            snippet_label.setWordWrap(True)
            snippet_label.setStyleSheet("color: #888; font-size: 10px; margin-top: 5px;")
            layout.addWidget(snippet_label)
        
        # Thread ID (small, for reference)
        thread_id_label = QLabel(f"Thread ID: {thread_id[:20]}...")
        thread_id_label.setStyleSheet("color: #AAA; font-size: 9px; margin-top: 3px;")
        layout.addWidget(thread_id_label)
        
        widget.setLayout(layout)
        
        # Style the widget - make background transparent so selection shows through
        widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                padding: 5px;
            }
        """)
        
        # Set widget to allow selection highlighting to show through
        widget.setAttribute(Qt.WA_TranslucentBackground)
        
        return widget
    
    def on_new_thread_toggled(self, checked):
        """Handle new thread checkbox toggle"""
        if checked:
            self.thread_list.setEnabled(False)
            self.thread_list.clearSelection()
        else:
            self.thread_list.setEnabled(True)
            if self.threads:
                self.thread_list.setCurrentRow(0)
    
    def accept_selection(self):
        """Accept the selected thread or new thread option"""
        if self.new_thread_checkbox.isChecked():
            self.start_new_thread = True
            self.selected_thread = None
        else:
            current_item = self.thread_list.currentItem()
            if current_item:
                self.selected_thread = current_item.data(Qt.UserRole)
            else:
                QMessageBox.warning(self, "No Selection", "Please select a thread or choose to start a new thread.")
                return
        
        self.accept()


class EmailDraftDialog(QDialog):
    """Dialog for reviewing and editing email drafts"""
    
    def __init__(self, case, email_body, subject="", thread_id=None, parent=None):
        super().__init__(parent)
        self.case = case
        self.email_body = email_body
        self.subject = subject
        self.thread_id = thread_id
        self.approved = False
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Email Draft Review")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Case info
        case_info = QLabel(f"<b>Case:</b> {self.case.get('Name', '')} (PV: {self.case.get('PV', '')})")
        layout.addWidget(case_info)
        
        # Recipient
        recipient_layout = QHBoxLayout()
        recipient_layout.addWidget(QLabel("To:"))
        self.recipient_input = QLineEdit(self.case.get('Attorney Email', ''))
        recipient_layout.addWidget(self.recipient_input)
        layout.addLayout(recipient_layout)
        
        # Subject (if not a reply)
        if not self.thread_id:
            subject_layout = QHBoxLayout()
            subject_layout.addWidget(QLabel("Subject:"))
            self.subject_input = QLineEdit(self.subject)
            subject_layout.addWidget(self.subject_input)
            layout.addLayout(subject_layout)
        
        # Email body
        layout.addWidget(QLabel("Message:"))
        self.body_edit = QTextEdit()
        self.body_edit.setPlainText(self.email_body)
        layout.addWidget(self.body_edit)
        
        # Thread info
        if self.thread_id:
            thread_info = QLabel(f"<i>This will be sent as a reply (Thread ID: {self.thread_id})</i>")
            layout.addWidget(thread_info)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("✅ Send Email")
        self.send_btn.clicked.connect(self.approve_and_send)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def approve_and_send(self):
        """Mark as approved and close"""
        self.approved = True
        self.email_body = self.body_edit.toPlainText()
        self.recipient = self.recipient_input.text()
        if hasattr(self, 'subject_input'):
            self.subject = self.subject_input.text()
        self.accept()
    
    def get_email_data(self):
        """Get the final email data"""
        return {
            'approved': self.approved,
            'recipient': self.recipient if self.approved else None,
            'subject': self.subject if self.approved and not self.thread_id else None,
            'body': self.email_body if self.approved else None,
            'thread_id': self.thread_id
        }


class BulkEmailWidget(QWidget):
    """Widget for bulk email processing"""
    
    def __init__(self, bulk_service, case_manager, parent=None):
        super().__init__(parent)
        self.bulk_service = bulk_service
        self.case_manager = case_manager
        self.parent_window = parent
        self.ack_service = CaseAcknowledgmentService()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>📨 Bulk Email Processing</h2>"))
        header_layout.addStretch()
        
        # Test mode toggle
        self.test_mode_check = QCheckBox("Test Mode")
        self.test_mode_check.setChecked(self.bulk_service.test_mode)
        self.test_mode_check.stateChanged.connect(self.toggle_test_mode)
        header_layout.addWidget(self.test_mode_check)
        
        layout.addLayout(header_layout)
        
        # Test mode info
        self.test_mode_info = QLabel()
        self.update_test_mode_info()
        layout.addWidget(self.test_mode_info)
        
        # Category selection
        category_group = QGroupBox("Select Processing Mode")
        category_layout = QVBoxLayout()
        
        # Radio buttons for processing modes
        self.by_category_radio = QRadioButton("Process by Category")
        self.by_firm_radio = QRadioButton("Process by Firm")
        self.by_status_radio = QRadioButton("Process by Status")
        self.by_priority_radio = QRadioButton("Process by Priority Score")
        self.by_balance_radio = QRadioButton("Process by Balance")
        self.custom_selection_radio = QRadioButton("Custom Selection")
        
        self.by_category_radio.setChecked(True)
        
        category_layout.addWidget(self.by_category_radio)
        category_layout.addWidget(self.by_firm_radio)
        category_layout.addWidget(self.by_status_radio)
        category_layout.addWidget(self.by_priority_radio)
        category_layout.addWidget(self.by_balance_radio)
        category_layout.addWidget(self.custom_selection_radio)
        
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # Category/Firm selection
        self.selection_combo = QComboBox()
        self.update_selection_combo()
        layout.addWidget(self.selection_combo)
        
        # Balance filter controls for custom range (hidden by default)
        self.balance_filter_widget = QWidget()
        balance_filter_layout = QHBoxLayout()
        balance_filter_layout.addWidget(QLabel("Filter:"))
        
        self.bulk_balance_filter = QComboBox()
        self.bulk_balance_filter.addItems(["Above", "Below"])
        balance_filter_layout.addWidget(self.bulk_balance_filter)
        
        self.bulk_balance_threshold = QLineEdit()
        self.bulk_balance_threshold.setPlaceholderText("Enter amount (e.g., 5000)")
        balance_filter_layout.addWidget(self.bulk_balance_threshold)
        balance_filter_layout.addStretch()
        
        self.balance_filter_widget.setLayout(balance_filter_layout)
        self.balance_filter_widget.hide()
        layout.addWidget(self.balance_filter_widget)
        
        # Custom PV input (hidden by default)
        self.custom_input = QTextEdit()
        self.custom_input.setPlaceholderText("Enter PV numbers (one per line or comma-separated)")
        self.custom_input.setMaximumHeight(100)
        self.custom_input.hide()
        layout.addWidget(self.custom_input)
        
        # Limit input
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Number to process:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setMinimum(0)
        self.limit_spin.setMaximum(1000)
        self.limit_spin.setValue(10)
        self.limit_spin.setSpecialValueText("All")
        limit_layout.addWidget(self.limit_spin)
        limit_layout.addStretch()
        layout.addLayout(limit_layout)
        
        # Preview area
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(9)
        self.preview_table.setHorizontalHeaderLabels([
            "PV #", "Name", "Balance", "Law Firm", "Email", "Status", "Acknowledged", "Actions", "Select"
        ])
        self.preview_table.setSortingEnabled(True)
        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.preview_table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.refresh_categories_btn = QPushButton("🔄 Refresh Categories")
        self.refresh_categories_btn.clicked.connect(self.refresh_categories)
        self.refresh_categories_btn.setToolTip("Recalculate case categories (including CCP 335.1)")
        
        self.populate_btn = QPushButton("📋 Populate Batch")
        self.populate_btn.clicked.connect(self.populate_batch)
        
        self.preview_btn = QPushButton("📋 Preview Selected")
        self.preview_btn.clicked.connect(self.preview_batch)
        self.preview_btn.setEnabled(False)
        
        self.send_btn = QPushButton("📮 Send Selected Emails")
        self.send_btn.clicked.connect(self.send_batch)
        self.send_btn.setEnabled(False)
        
        self.export_btn = QPushButton("💾 Export to Excel")
        self.export_btn.clicked.connect(self.export_batch)
        
        button_layout.addWidget(self.refresh_categories_btn)
        button_layout.addWidget(self.populate_btn)
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        
        # Simple status label (minimal space)
        self.status_label = QLabel("Ready to process emails")
        self.status_label.setStyleSheet("padding: 3px; color: #666;")
        layout.addWidget(self.status_label)
        
        # Statistics
        self.stats_label = QLabel()
        self.update_statistics()
        layout.addWidget(self.stats_label)
        
        self.setLayout(layout)
        
        # Connect radio button changes
        self.by_category_radio.toggled.connect(self.on_mode_changed)
        self.by_firm_radio.toggled.connect(self.on_mode_changed)
        self.by_status_radio.toggled.connect(self.on_mode_changed)
        self.by_priority_radio.toggled.connect(self.on_mode_changed)
        self.by_balance_radio.toggled.connect(self.on_mode_changed)
        self.custom_selection_radio.toggled.connect(self.on_mode_changed)
    
    def on_mode_changed(self):
        """Handle processing mode change"""
        self.update_selection_combo()
        self.custom_input.setVisible(self.custom_selection_radio.isChecked())
        
        # Show balance filter widget only when "Custom Range" is selected
        show_balance_filter = (self.by_balance_radio.isChecked() and 
                             self.selection_combo.currentText() == "Custom Range")
        self.balance_filter_widget.setVisible(show_balance_filter)
        
        # Connect combo change to show/hide balance filter
        if self.by_balance_radio.isChecked():
            try:
                self.selection_combo.currentTextChanged.disconnect()
            except:
                pass
            self.selection_combo.currentTextChanged.connect(self.on_balance_selection_changed)
    
    def on_balance_selection_changed(self):
        """Handle balance selection change"""
        show_balance_filter = self.selection_combo.currentText() == "Custom Range"
        self.balance_filter_widget.setVisible(show_balance_filter)
    
    def refresh_categories(self):
        """Force refresh of case categories"""
        try:
            # Use enhanced progress with live logs
            with ProgressContext(self, "Refreshing Categories", "Analyzing cases...", 
                               pulse=False, maximum=100, show_logs=True) as progress:
                
                # Clear cache and force recategorization
                progress.set_message("Clearing cache...")
                progress.log("🗑️ Clearing category cache")
                self.bulk_service.force_recategorization()
                
                # Also refresh the collections tracker data if it's enhanced
                if hasattr(self.bulk_service.collections_tracker, '_load_tracking_data'):
                    progress.log("🔄 Refreshing collections tracker data")
                    self.bulk_service.collections_tracker.data = self.bulk_service.collections_tracker._load_tracking_data()
                
                # Run fresh categorization with enhanced progress
                progress.log("📂 Starting case categorization")
                self.bulk_service.categorize_cases(
                    force_refresh=True, 
                    progress=progress
                )
                
                # Update combo box if in firm mode
                if self.by_firm_radio.isChecked():
                    progress.set_message("Updating display...")
                    self.update_selection_combo()
                    
                progress.update(100, "Categories refreshed!")
            
            # Show statistics in a message box
            stats = self.bulk_service.categorized_cases
            if stats:
                ccp_count = len(stats.get('ccp_335_1', []))
                old_count = len(stats.get('old_cases', []))
                
                QMessageBox.information(
                    self, 
                    "Categories Refreshed",
                    f"Case categories have been refreshed!\n\n"
                    f"Old cases (>2 years): {old_count}\n"
                    f"CCP 335.1 eligible: {ccp_count}\n"
                    f"\nCache will be used for the next 5 minutes."
                )
            
            self.update_statistics()
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to refresh categories: {str(e)}")
    
    def update_selection_combo(self):
        """Update the selection combo based on mode"""
        self.selection_combo.clear()
        
        if self.by_category_radio.isChecked():
            self.selection_combo.addItems([
                # Stale case categories
                "Critical (90+ days no response)",
                "High Priority (60+ days no response)",
                "No Response (30+ days no response)",
                "Recently Sent (<30 days)",
                "Never Contacted",
                "Missing DOI",
                "CCP 335.1 (>2yr Statute Inquiry)"
            ])
        elif self.by_firm_radio.isChecked():
            # Get firms from categorized cases
            if not self.bulk_service.categorized_cases:
                self.bulk_service.categorize_cases()
            firms = list(self.bulk_service.categorized_cases.get("by_firm", {}).keys())[:50]
            self.selection_combo.addItems(firms)
        elif self.by_status_radio.isChecked():
            # Get unique statuses from case manager
            unique_statuses = set()
            if self.case_manager and not self.case_manager.df.empty:
                # Status is in column 2 (index 2)
                status_column = self.case_manager.df.iloc[:, 2]
                unique_statuses = set(status_column.dropna().astype(str).unique())
                # Remove empty strings and 'nan'
                unique_statuses = {s for s in unique_statuses if s and s != 'nan'}
            
            # Add common statuses if found
            status_list = sorted(list(unique_statuses))
            if status_list:
                self.selection_combo.addItems(status_list)
            else:
                # Default statuses if none found
                self.selection_combo.addItems(["NEW", "ACTIVE", "PENDING", "CLOSED"])
        elif self.by_priority_radio.isChecked():
            self.selection_combo.addItems([
                "Critical (90+ days no response)",
                "High Priority (60+ days no response)",
                "No Response (30+ days no response)"
            ])
        elif self.by_balance_radio.isChecked():
            self.selection_combo.addItems([
                "All Active Cases",
                "Above $5,000",
                "Above $10,000",
                "Above $20,000",
                "Below $5,000",
                "Below $2,000",
                "Custom Range"
            ])
    
    def toggle_test_mode(self, state):
        """Toggle test mode"""
        if state == Qt.Checked:
            email, ok = QInputDialog.getText(
                self, "Test Email", 
                "Enter test email address:",
                text=self.bulk_service.test_email or "test@example.com"
            )
            if ok:
                self.bulk_service.set_test_mode(True, email)
        else:
            self.bulk_service.set_test_mode(False)
        
        self.update_test_mode_info()
    
    def update_test_mode_info(self):
        """Update test mode information display"""
        if self.bulk_service.test_mode:
            self.test_mode_info.setText(
                f"<b style='color: orange'>⚠️ TEST MODE ACTIVE - Emails will go to: {self.bulk_service.test_email}</b>"
            )
            self.test_mode_info.setStyleSheet("background-color: yellow; padding: 5px; border: 2px solid red;")
        else:
            self.test_mode_info.setText(
                "<b style='color: green'>✅ PRODUCTION MODE - Emails will go to actual recipients</b>"
            )
            self.test_mode_info.setStyleSheet("background-color: lightgreen; padding: 5px; border: 1px solid green;")
    
    def update_test_mode_display(self):
        """Update test mode display when toggled from main window"""
        self.test_mode_check.setChecked(self.bulk_service.test_mode)
        self.update_test_mode_info()
        
        # Update preview if there are emails loaded
        if hasattr(self, 'current_batch') and self.current_batch:
            self.preview_batch()
    
    def populate_batch(self):
        """Populate the batch based on selected criteria"""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Store the batch emails for later use
            self.current_batch = self.get_selected_batch()
            
            if not self.current_batch:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "No Cases", "No cases found for the selected criteria.")
                return
            
            # Populate preview table
            self.preview_table.setRowCount(len(self.current_batch))
            
            for row, email in enumerate(self.current_batch):
                pv = str(email.get('pv', ''))
                
                # PV #
                self.preview_table.setItem(row, 0, QTableWidgetItem(pv))
                
                # Name
                self.preview_table.setItem(row, 1, QTableWidgetItem(str(email.get('name', ''))))
                
                # Balance - format as currency
                balance = email.get('case_data', {}).get('Balance', 0.0) if 'case_data' in email else 0.0
                if not balance:
                    # Try to get from case manager
                    case = self.case_manager.get_case_by_pv(pv)
                    if case:
                        balance = case.get('Balance', 0.0)
                balance_item = QTableWidgetItem(f"${balance:,.2f}")
                balance_item.setData(Qt.UserRole, balance)  # Store raw value for sorting
                self.preview_table.setItem(row, 2, balance_item)
                
                # Law Firm - try multiple sources
                law_firm = ""
                if 'case_data' in email:
                    law_firm = email['case_data'].get('Law Firm', '') or email['case_data'].get('law_firm', '')
                if not law_firm:
                    law_firm = email.get('law_firm', '')
                if not law_firm and pv:
                    # Try to get from case manager as last resort
                    case = self.case_manager.get_case_by_pv(pv)
                    if case:
                        law_firm = case.get('Law Firm', '')
                self.preview_table.setItem(row, 3, QTableWidgetItem(str(law_firm)))
                
                # Email - show TEST MODE clearly
                email_to = str(email.get('to', ''))
                email_item = QTableWidgetItem(email_to)
                if self.bulk_service.test_mode:
                    email_item.setBackground(QColor(255, 255, 0))  # Yellow background
                    email_item.setForeground(QColor(255, 0, 0))  # Red text
                    email_item.setToolTip(f"TEST MODE: Actually sending to {email_to}\nOriginal: {email.get('original_to', 'N/A')}")
                self.preview_table.setItem(row, 4, email_item)
                
                # Status - try multiple sources
                status = ""
                if 'case_data' in email:
                    status = email['case_data'].get('Status', '') or email['case_data'].get('status', '')
                if not status:
                    status = email.get('status', '')
                if not status and pv:
                    # Try to get from case manager as last resort
                    case = self.case_manager.get_case_by_pv(pv)
                    if case:
                        status = case.get('Status', '')
                self.preview_table.setItem(row, 5, QTableWidgetItem(str(status)))
                
                # Acknowledgment status
                ack_info = self.ack_service.get_acknowledgment_info(pv)
                if ack_info:
                    ack_text = f"✅ {ack_info.get('reason', 'Acknowledged')[:15]}..."
                    ack_item = QTableWidgetItem(ack_text)
                    ack_item.setForeground(QColor(0, 200, 0))
                    self.preview_table.setItem(row, 6, ack_item)
                else:
                    self.preview_table.setItem(row, 6, QTableWidgetItem(""))
                
                # Actions button
                action_btn = QPushButton("Actions")
                action_menu = QMenu()
                
                # Add summarize, draft follow-up, and draft status request options
                case_data = email.get('case_data', {})
                
                # Summarize option
                summarize_action = action_menu.addAction("📊 Summarize")
                summarize_action.triggered.connect(lambda checked, cd=case_data: self.summarize_case_from_bulk(cd))
                
                # Draft follow-up option
                draft_followup_action = action_menu.addAction("📧 Draft Follow-up")
                draft_followup_action.triggered.connect(lambda checked, cd=case_data: self.draft_followup_from_bulk(cd))
                
                # Draft status request option
                draft_status_action = action_menu.addAction("📋 Draft Status Request")
                draft_status_action.triggered.connect(lambda checked, cd=case_data: self.draft_status_request_from_bulk(cd))
                
                action_menu.addSeparator()
                
                if ack_info:
                    unack_action = action_menu.addAction("❌ Remove Acknowledgment")
                    unack_action.triggered.connect(lambda checked, p=pv: self.unacknowledge_case(p))
                else:
                    ack_action = action_menu.addAction("✅ Acknowledge Case")
                    ack_action.triggered.connect(lambda checked, p=pv, n=email.get('name', ''), s=status: 
                                               self.acknowledge_case(p, n, s))
                
                action_btn.setMenu(action_menu)
                self.preview_table.setCellWidget(row, 7, action_btn)
                
                # Checkbox for selection (now in column 8)
                checkbox = QCheckBox()
                # Don't auto-check acknowledged cases
                checkbox.setChecked(not bool(ack_info))
                self.preview_table.setCellWidget(row, 8, checkbox)
            
            self.preview_table.resizeColumnsToContents()
            self.preview_btn.setEnabled(True)
            self.send_btn.setEnabled(True)
            
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Batch Populated", f"Populated {len(self.current_batch)} cases for review.")
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to populate batch: {str(e)}")
    
    def preview_batch(self):
        """Preview selected emails from the batch"""
        try:
            if not hasattr(self, 'current_batch') or not self.current_batch:
                QMessageBox.warning(self, "No Batch", "Please populate a batch first.")
                return
            
            # Get selected emails from preview table
            selected_emails = []
            for row in range(self.preview_table.rowCount()):
                checkbox = self.preview_table.cellWidget(row, 8)  # Updated column
                if checkbox and checkbox.isChecked():
                    selected_emails.append(self.current_batch[row])
            
            if not selected_emails:
                QMessageBox.warning(self, "No Selection", "Please select at least one email to preview.")
                return
            
            # Show preview dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Email Preview - All Selected Emails")
            dialog.setMinimumSize(900, 700)
            
            layout = QVBoxLayout()
            
            # Create text area for preview
            preview_text = QTextEdit()
            preview_text.setReadOnly(True)
            
            preview_content = []
            preview_content.append(f"Total emails to send: {len(selected_emails)}\n")
            preview_content.append("="*60 + "\n")
            
            # Show ALL emails
            for i, email in enumerate(selected_emails, 1):
                preview_content.append(f"[{i}] {email.get('subject', 'No Subject')}")
                preview_content.append(f"To: {email.get('to', '')}")
                preview_content.append(f"\n{email.get('body', 'No content')}")
                preview_content.append("\n" + "="*60 + "\n")
            
            preview_text.setPlainText("\n".join(preview_content))
            layout.addWidget(preview_text)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to preview emails: {str(e)}")
    
    def get_selected_batch(self):
        """Get the selected batch of emails"""
        try:
            # Ensure cases have been categorized at least once
            if not self.bulk_service.categorized_cases:
                self.bulk_service.categorize_cases()
            
            limit = self.limit_spin.value() if self.limit_spin.value() > 0 else None
            
            if self.by_category_radio.isChecked():
                category_map = {
                    "Critical (90+ days no response)": "critical",
                    "High Priority (60+ days no response)": "high_priority",
                    "No Response (30+ days no response)": "no_response",
                    "Recently Sent (<30 days)": "recently_sent",
                    "Never Contacted": "never_contacted",
                    "Missing DOI": "missing_doi",
                    "CCP 335.1 (>2yr Statute Inquiry)": "ccp_335_1"
                }
                category = category_map.get(self.selection_combo.currentText())
                return self.bulk_service.prepare_batch(category, limit=limit)
                
            elif self.by_firm_radio.isChecked():
                firm = self.selection_combo.currentText()
                return self.bulk_service.prepare_batch("by_firm", subcategory=firm, limit=limit)
                
            elif self.by_status_radio.isChecked():
                status = self.selection_combo.currentText()
                if not status:
                    return []
                
                # Get all cases with this status
                filtered_emails = []
                df = self.case_manager.df
                
                # Status is in column 2
                status_matches = df[df.iloc[:, 2].astype(str).str.upper() == status.upper()]
                
                for _, row in status_matches.iterrows():
                    case_info = self.case_manager.format_case(row)
                    pv = str(case_info.get("PV", ""))
                    
                    # Skip if already sent
                    if pv in self.bulk_service.sent_pids or pv in self.bulk_service.session_sent_pids:
                        continue
                    
                    # Skip acknowledged cases
                    from services.case_acknowledgment_service import CaseAcknowledgmentService
                    ack_service = CaseAcknowledgmentService()
                    if ack_service.is_acknowledged(pv):
                        continue
                    
                    # Create case_data object with lowercase keys that generate_email_content expects
                    case_data = {
                        "pv": case_info.get("PV", ""),
                        "name": case_info.get("Name", ""),
                        "doi": case_info.get("DOI", ""),
                        "cms": case_info.get("CMS", ""),
                        "attorney_email": case_info.get("Attorney Email", ""),
                        "law_firm": case_info.get("Law Firm", ""),
                        "status": case_info.get("Status", ""),
                        "balance": case_info.get("Balance", 0.0),
                        "full_case": case_info
                    }
                    
                    # Generate email content
                    email_data = self.bulk_service.generate_email_content(case_data)
                    if email_data:
                        filtered_emails.append(email_data)
                    
                    # Apply limit if specified
                    if limit and len(filtered_emails) >= limit:
                        break
                
                return filtered_emails
                
            elif self.by_priority_radio.isChecked():
                # Map to the actual category names (same as time-based categories)
                priority_map = {
                    "Critical (90+ days no response)": "critical",
                    "High Priority (60+ days no response)": "high_priority",
                    "No Response (30+ days no response)": "no_response"
                }
                priority = priority_map.get(self.selection_combo.currentText())
                return self.bulk_service.prepare_batch(priority, limit=limit)
                
            elif self.by_balance_radio.isChecked():
                # Get balance selection
                balance_option = self.selection_combo.currentText()
                
                # Get all active cases
                all_cases = self.bulk_service.get_active_cases()
                filtered_emails = []
                
                # Define thresholds
                thresholds = {
                    "Above $5,000": (5000, None),
                    "Above $10,000": (10000, None),
                    "Above $20,000": (20000, None),
                    "Below $5,000": (None, 5000),
                    "Below $2,000": (None, 2000)
                }
                
                if balance_option == "All Active Cases":
                    # Return all active cases
                    for case_info in all_cases[:limit] if limit else all_cases:
                        email_data = self.bulk_service.generate_email_content(case_info)
                        if email_data:
                            filtered_emails.append(email_data)
                elif balance_option == "Custom Range":
                    # Use the balance filter inputs from the header
                    filter_type = self.bulk_balance_filter.currentText()
                    threshold_text = self.bulk_balance_threshold.text()
                    
                    if threshold_text:
                        try:
                            threshold = float(threshold_text.replace(',', '').replace('$', ''))
                            for case_info in all_cases:
                                balance = case_info.get('Balance', 0.0)
                                if filter_type == "Above" and balance >= threshold:
                                    email_data = self.bulk_service.generate_email_content(case_info)
                                    if email_data:
                                        filtered_emails.append(email_data)
                                elif filter_type == "Below" and balance <= threshold:
                                    email_data = self.bulk_service.generate_email_content(case_info)
                                    if email_data:
                                        filtered_emails.append(email_data)
                                if limit and len(filtered_emails) >= limit:
                                    break
                        except ValueError:
                            pass
                elif balance_option in thresholds:
                    min_val, max_val = thresholds[balance_option]
                    for case_info in all_cases:
                        balance = case_info.get('Balance', 0.0)
                        if min_val is not None and balance >= min_val:
                            email_data = self.bulk_service.generate_email_content(case_info)
                            if email_data:
                                filtered_emails.append(email_data)
                        elif max_val is not None and balance <= max_val:
                            email_data = self.bulk_service.generate_email_content(case_info)
                            if email_data:
                                filtered_emails.append(email_data)
                        if limit and len(filtered_emails) >= limit:
                            break
                
                return filtered_emails
                
            elif self.custom_selection_radio.isChecked():
                # Parse custom PV numbers
                text = self.custom_input.toPlainText()
                numbers = []
                for line in text.split('\n'):
                    if ',' in line:
                        numbers.extend([n.strip() for n in line.split(',')])
                    else:
                        numbers.append(line.strip())
                numbers = [n for n in numbers if n]
                return self.bulk_service.prepare_batch_from_numbers(numbers)
            
            return []
        except Exception as e:
            if self.parent_window:
                self.parent_window.log_activity(f"Error getting batch: {str(e)}")
            return []
    
    def send_batch(self):
        """Send the selected emails with progress tracking"""
        try:
            if not hasattr(self, 'current_batch') or not self.current_batch:
                QMessageBox.warning(self, "No Batch", "Please populate a batch first.")
                return
            
            # Get selected emails from preview
            selected_emails = []
            for row in range(self.preview_table.rowCount()):
                checkbox = self.preview_table.cellWidget(row, 8)  # Updated column
                if checkbox and checkbox.isChecked():
                    # Use the full email data from current_batch
                    selected_emails.append(self.current_batch[row])
            
            if not selected_emails:
                QMessageBox.warning(self, "No Selection", "No emails selected for sending.")
                return
            
            # Confirm sending
            reply = QMessageBox.question(
                self, "Confirm Send",
                f"Send {len(selected_emails)} emails?\n"
                f"Mode: {'TEST' if self.bulk_service.test_mode else 'PRODUCTION'}",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Create progress dialog
                progress_dialog = QProgressDialog(
                    "Sending emails...", "Cancel", 0, len(selected_emails), self
                )
                progress_dialog.setWindowTitle("Bulk Email Progress")
                progress_dialog.setWindowModality(Qt.WindowModal)
                progress_dialog.setMinimumDuration(0)
                progress_dialog.setValue(0)
                
                # Update status
                self.status_label.setText(f"Starting to send {len(selected_emails)} emails...")
                
                # Log start of batch to main activity log
                if self.parent_window:
                    self.parent_window.log_activity(f"📤 Starting bulk email batch: {len(selected_emails)} emails")
                
                # Process emails with progress updates
                sent_emails = []
                failed_emails = []
                
                for i, email_data in enumerate(selected_emails):
                    if progress_dialog.wasCanceled():
                        if self.parent_window:
                            self.parent_window.log_activity("⚠️ Processing cancelled by user")
                        break
                    
                    # Update progress
                    pv = email_data.get('pv', 'Unknown')
                    name = email_data.get('name', 'Unknown')
                    progress_dialog.setLabelText(f"Sending email {i+1}/{len(selected_emails)}\nPV: {pv} - {name}")
                    progress_dialog.setValue(i)
                    
                    # Process email
                    try:
                        # Send individual email
                        result = self.bulk_service.send_batch([email_data])
                        if result['sent']:
                            sent_emails.extend(result['sent'])
                            # Log successful send to main activity log
                            if self.parent_window:
                                self.parent_window.log_activity(f"✅ Sent email for PV {pv} - {name}")
                        else:
                            failed_emails.extend(result['failed'])
                            # Log failed send to main activity log
                            if self.parent_window:
                                self.parent_window.log_activity(f"❌ Failed to send for PV {pv} - {name}")
                    except Exception as e:
                        failed_emails.append({'pv': pv, 'error': str(e)})
                        if self.parent_window:
                            self.parent_window.log_activity(f"❌ Error sending email for PV {pv}: {str(e)}")
                    
                    # Update status label with progress
                    self.status_label.setText(f"Processing: {i+1}/{len(selected_emails)} | Sent: {len(sent_emails)} | Failed: {len(failed_emails)}")
                    QApplication.processEvents()
                
                progress_dialog.setValue(len(selected_emails))
                progress_dialog.close()
                
                # Log completion to main activity log
                self.status_label.setText(f"Batch complete: {len(sent_emails)} sent, {len(failed_emails)} failed")
                if self.parent_window:
                    self.parent_window.log_activity(f"📊 Batch complete: {len(sent_emails)} sent, {len(failed_emails)} failed")
                
                # Show detailed results
                result_msg = f"Batch Processing Complete!\n\n"
                result_msg += f"✅ Successfully Sent: {len(sent_emails)} emails\n"
                result_msg += f"❌ Failed: {len(failed_emails)} emails\n\n"
                
                if failed_emails:
                    result_msg += "Failed emails:\n"
                    for fail in failed_emails[:5]:  # Show first 5 failures
                        result_msg += f"  • PV {fail.get('pv', 'Unknown')}: {fail.get('error', 'Unknown error')}\n"
                    if len(failed_emails) > 5:
                        result_msg += f"  ... and {len(failed_emails) - 5} more\n"
                
                QMessageBox.information(self, "Batch Complete", result_msg)
                
                # Clear preview and reset batch
                self.preview_table.setRowCount(0)
                self.current_batch = []
                self.send_btn.setEnabled(False)
                self.preview_btn.setEnabled(False)
                
                # Update statistics and CMS card
                self.update_statistics()
                
                # Update the CMS card to reflect new pending notes
                if hasattr(self.parent_window, 'update_cms_card'):
                    self.parent_window.update_cms_card()
                    self.parent_window.log_activity(f"Added {len(sent_emails)} emails to CMS notes queue")
                
        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to send batch: {str(e)}")
    
    def export_batch(self):
        """Export batch to Excel"""
        try:
            emails = self.get_selected_batch()
            if not emails:
                QMessageBox.warning(self, "No Data", "No emails to export.")
                return
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Export Batch",
                f"email_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if filepath:
                filepath = self.bulk_service.export_batch_for_review(emails)
                QMessageBox.information(self, "Success", f"Exported to {filepath}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
    
    def acknowledge_case(self, pv, case_name="", status=""):
        """Acknowledge a case with snooze options"""
        dialog = CaseAcknowledgmentDialog(pv, case_name, status, self)
        if dialog.exec_():
            data = dialog.get_acknowledgment_data()
            
            # Get the full case data to retrieve CMS number
            case = self.parent_window.case_manager.get_case_by_pv(pv) if self.parent_window else None
            cms_number = case.get('CMS') if case else None
            
            success = self.ack_service.acknowledge_case(
                pv=pv,
                reason=data['reason'],
                snooze_days=data['snooze_days'],
                status=status,
                notes=data['notes'],
                cms_number=cms_number
            )
            
            if success:
                QMessageBox.information(self, "Success", f"Case {pv} acknowledged successfully!")
                # Refresh the batch to update acknowledgment status
                self.populate_batch()
            else:
                QMessageBox.critical(self, "Error", f"Failed to acknowledge case {pv}")
    
    def unacknowledge_case(self, pv):
        """Remove acknowledgment from a case"""
        reply = QMessageBox.question(
            self, "Remove Acknowledgment",
            f"Remove acknowledgment for case {pv}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.ack_service.unacknowledge_case(pv):
                QMessageBox.information(self, "Success", f"Acknowledgment removed for case {pv}")
                # Refresh the batch to update acknowledgment status
                self.populate_batch()
            else:
                QMessageBox.critical(self, "Error", f"Failed to remove acknowledgment")
    
    def summarize_case_from_bulk(self, case_data):
        """Summarize a case from the bulk email view"""
        try:
            pv = case_data.get('pv', '')
            name = case_data.get('name', '')
            
            if not pv:
                QMessageBox.warning(self, "No Case", "No case data available for summarization.")
                return
            
            # Directly trigger summarization without switching tabs
            if self.parent_window:
                self.parent_window.summarize_case_by_pv(pv)
                self.parent_window.log_activity(f"Summarizing case {pv} - {name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to summarize case: {str(e)}")
    
    def draft_followup_from_bulk(self, case_data):
        """Draft a follow-up email for a case from the bulk email view"""
        try:
            pv = case_data.get('pv', '')
            
            if not pv:
                QMessageBox.warning(self, "No Case", "No case data available.")
                return
            
            # Use the main draft_followup_by_pv method for consistency
            if self.parent_window:
                self.parent_window.draft_followup_by_pv(pv)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to draft follow-up: {str(e)}")
    
    def draft_status_request_from_bulk(self, case_data):
        """Draft a status request email for a case from the bulk email view"""
        try:
            pv = case_data.get('pv', '')
            
            if not pv:
                QMessageBox.warning(self, "No Case", "No case data available.")
                return
            
            # Use the main draft_status_request_by_pv method for consistency
            if self.parent_window:
                self.parent_window.draft_status_request_by_pv(pv)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to draft status request: {str(e)}")
    
    def send_individual_email(self, to_email, subject, body, pv, dialog):
        """Send an individual email"""
        try:
            if not self.parent_window or not self.parent_window.gmail_service:
                QMessageBox.warning(self, "No Gmail Service", "Gmail service not available.")
                return
            
            # Send the email
            self.parent_window.gmail_service.send_email(to_email, subject, body)
            
            # Log the sent email
            log_sent_email(to_email, subject, pv)
            
            # Add CMS note if enabled
            if self.parent_window.cms_integration_enabled:
                from services.cms_integration import log_session_email
                log_session_email(pv, to_email, "INDIVIDUAL")
            
            QMessageBox.information(self, "Success", f"Email sent to {to_email}")
            dialog.accept()
            
            # Log activity
            if self.parent_window:
                self.parent_window.log_activity(f"Sent individual email for {pv} to {to_email}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")
    
    def copy_to_clipboard(self, subject, body):
        """Copy email content to clipboard"""
        clipboard = QApplication.clipboard()
        full_text = f"Subject: {subject}\n\n{body}"
        clipboard.setText(full_text)
        QMessageBox.information(self, "Copied", "Email content copied to clipboard!")
    
    def update_statistics(self):
        """Update statistics display"""
        try:
            stats = self.bulk_service.get_statistics()
            
            stats_text = f"""
            <b>📊 Bulk Email Statistics:</b><br>
            Test Mode: {'ON' if stats['test_mode'] else 'OFF'}<br>
            Session Sent: {stats.get('session_sent_production', 0)}<br>
            Total Sent: {stats.get('total_sent_production', 0)}<br>
            Test Emails: {stats.get('test_emails_sent', 0)}
            """
            
            self.stats_label.setText(stats_text)
            
        except Exception as e:
            self.stats_label.setText(f"Error loading statistics: {str(e)}")


class AcknowledgedCasesWidget(QWidget):
    """Widget for viewing and managing acknowledged cases"""
    
    def __init__(self, case_manager, parent=None):
        super().__init__(parent)
        self.case_manager = case_manager
        self.parent_window = parent
        self.ack_service = CaseAcknowledgmentService()
        self.init_ui()
        self.load_acknowledged_cases()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("Acknowledged Cases")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_acknowledged_cases)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by name, PV#, or reason...")
        self.filter_input.textChanged.connect(self.filter_cases)
        toolbar_layout.addWidget(self.filter_input)
        
        self.export_btn = QPushButton("📥 Export to CSV")
        self.export_btn.clicked.connect(self.export_to_csv)
        toolbar_layout.addWidget(self.export_btn)
        
        toolbar_layout.addStretch()
        
        # Stats label
        self.stats_label = QLabel()
        toolbar_layout.addWidget(self.stats_label)
        
        layout.addLayout(toolbar_layout)
        
        # Table for acknowledged cases
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "PV#", "Name", "DOI", "Law Firm", "Status", 
            "Acknowledged Date", "Reason", "Actions"
        ])
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        # Summary text area
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(150)
        layout.addWidget(self.summary_text)
        
        self.setLayout(layout)
    
    def load_acknowledged_cases(self):
        """Load all acknowledged cases"""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Get all acknowledged cases
            all_ack = self.ack_service.get_all_acknowledged()
            
            # Clear table
            self.table.setRowCount(0)
            
            # Populate table with acknowledged cases
            for pv, info in all_ack.items():
                # Get case details from case manager
                case_data = self.get_case_details(pv)
                if not case_data:
                    continue
                
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # PV#
                self.table.setItem(row, 0, QTableWidgetItem(str(pv)))
                
                # Name
                self.table.setItem(row, 1, QTableWidgetItem(case_data.get('Name', '')))
                
                # DOI
                doi = case_data.get('DOI', '')
                if hasattr(doi, 'strftime'):
                    doi = doi.strftime("%m/%d/%Y")
                self.table.setItem(row, 2, QTableWidgetItem(str(doi)))
                
                # Law Firm
                self.table.setItem(row, 3, QTableWidgetItem(case_data.get('Law Firm', '')))
                
                # Status
                self.table.setItem(row, 4, QTableWidgetItem(case_data.get('Status', '')))
                
                # Acknowledged Date
                ack_date = info.get('acknowledged_date', '')
                self.table.setItem(row, 5, QTableWidgetItem(ack_date))
                
                # Reason
                reason = info.get('reason', '')
                self.table.setItem(row, 6, QTableWidgetItem(reason))
                
                # Actions
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(2, 2, 2, 2)
                
                # View button
                view_btn = QPushButton("👁️")
                view_btn.setToolTip("View case details")
                view_btn.clicked.connect(lambda checked, p=pv: self.view_case(p))
                action_layout.addWidget(view_btn)
                
                # Unacknowledge button
                unack_btn = QPushButton("❌")
                unack_btn.setToolTip("Remove acknowledgment")
                unack_btn.clicked.connect(lambda checked, p=pv: self.unacknowledge_case(p))
                action_layout.addWidget(unack_btn)
                
                # Email button
                email_btn = QPushButton("📧")
                email_btn.setToolTip("Draft email")
                email_btn.clicked.connect(lambda checked, cd=case_data: self.draft_email(cd))
                action_layout.addWidget(email_btn)
                
                action_widget.setLayout(action_layout)
                self.table.setCellWidget(row, 7, action_widget)
            
            self.table.resizeColumnsToContents()
            
            # Update stats
            total = len(all_ack)
            self.stats_label.setText(f"Total: {total} cases")
            
            # Update summary
            summary = self.generate_summary(all_ack)
            self.summary_text.setPlainText(summary)
            
            QApplication.restoreOverrideCursor()
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to load acknowledged cases: {str(e)}")
    
    def add_acknowledged_case(self, pv, case_data, acknowledgment_data):
        """Add a newly acknowledged case to the display without refreshing"""
        try:
            # Add to the table
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # PV#
            self.table.setItem(row, 0, QTableWidgetItem(str(pv)))
            
            # Name
            self.table.setItem(row, 1, QTableWidgetItem(case_data.get('Name', '')))
            
            # DOI
            doi = case_data.get('DOI', '')
            if hasattr(doi, 'strftime'):
                doi = doi.strftime("%m/%d/%Y")
            self.table.setItem(row, 2, QTableWidgetItem(str(doi)))
            
            # Law Firm
            self.table.setItem(row, 3, QTableWidgetItem(case_data.get('Law Firm', '')))
            
            # Status
            self.table.setItem(row, 4, QTableWidgetItem(case_data.get('Status', '')))
            
            # Acknowledged Date
            from datetime import datetime
            ack_date = datetime.now().strftime("%m/%d/%Y")
            self.table.setItem(row, 5, QTableWidgetItem(ack_date))
            
            # Reason
            self.table.setItem(row, 6, QTableWidgetItem(acknowledgment_data.get('reason', '')))
            
            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            # View button
            view_btn = QPushButton("👁️")
            view_btn.setToolTip("View details")
            view_btn.clicked.connect(lambda checked, p=pv: self.view_details(p))
            action_layout.addWidget(view_btn)
            
            # Unacknowledge button
            unack_btn = QPushButton("❌")
            unack_btn.setToolTip("Remove acknowledgment")
            unack_btn.clicked.connect(lambda checked, p=pv: self.unacknowledge_case(p))
            action_layout.addWidget(unack_btn)
            
            # Email button
            email_btn = QPushButton("📧")
            email_btn.setToolTip("Draft email")
            email_btn.clicked.connect(lambda checked, cd=case_data: self.draft_email(cd))
            action_layout.addWidget(email_btn)
            
            action_widget.setLayout(action_layout)
            self.table.setCellWidget(row, 7, action_widget)
            
            # Update stats
            current_count = self.table.rowCount()
            self.stats_label.setText(f"Total: {current_count} cases")
            
            # Sort table to show newest at top
            self.table.sortByColumn(5, Qt.DescendingOrder)
            
        except Exception as e:
            print(f"Error adding acknowledged case to display: {e}")
    
    def get_case_details(self, pv):
        """Get case details from case manager"""
        try:
            df = self.case_manager.df
            case_row = df[df[1].astype(str) == str(pv)]
            if not case_row.empty:
                return self.case_manager.format_case(case_row.iloc[0])
        except:
            pass
        return None
    
    def filter_cases(self):
        """Filter displayed cases based on search text"""
        search_text = self.filter_input.text().lower()
        
        for row in range(self.table.rowCount()):
            should_show = False
            
            if not search_text:
                should_show = True
            else:
                # Check all columns for match
                for col in range(self.table.columnCount() - 1):  # Skip actions column
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        should_show = True
                        break
            
            self.table.setRowHidden(row, not should_show)
    
    def view_case(self, pv):
        """View case details in main tab"""
        if self.parent_window:
            # Switch to Cases tab (index 1)
            self.parent_window.tabs.setCurrentIndex(1)
            
            # Load case
            self.parent_window.case_search_input.setText(str(pv))
            self.parent_window.search_cases()
    
    def remove_case_from_display(self, pv):
        """Remove a case from the acknowledged display instantly"""
        try:
            # Find and remove the row with this PV
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)  # PV# is in column 0
                if item and item.text() == str(pv):
                    self.table.removeRow(row)
                    break
            
            # Update stats
            current_count = self.table.rowCount()
            self.stats_label.setText(f"Total: {current_count} cases")
            
        except Exception as e:
            print(f"Error removing case from acknowledged display: {e}")
    
    def unacknowledge_case(self, pv):
        """Remove acknowledgment from a case"""
        reply = QMessageBox.question(
            self, "Remove Acknowledgment",
            f"Remove acknowledgment for case {pv}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.ack_service.unacknowledge_case(pv):
                QMessageBox.information(self, "Success", f"Acknowledgment removed for case {pv}")
                # Remove from display instantly instead of reloading
                self.remove_case_from_display(pv)
            else:
                QMessageBox.critical(self, "Error", "Failed to remove acknowledgment")
    
    def draft_email(self, case_data):
        """Draft an email for an acknowledged case"""
        try:
            # Generate email content
            from templates.followup_template import get_followup_email
            subject, body = get_followup_email(case_data)
            
            # Show email dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Draft Email - {case_data.get('Name', '')}")
            dialog.setMinimumSize(600, 500)
            
            layout = QVBoxLayout()
            
            layout.addWidget(QLabel("Subject:"))
            subject_input = QLineEdit(subject)
            layout.addWidget(subject_input)
            
            layout.addWidget(QLabel("Body:"))
            body_text = QTextEdit()
            body_text.setPlainText(body)
            layout.addWidget(body_text)
            
            button_layout = QHBoxLayout()
            
            send_btn = QPushButton("Send")
            send_btn.clicked.connect(lambda: self.send_email(
                case_data.get('Attorney Email', ''),
                subject_input.text(),
                body_text.toPlainText(),
                case_data.get('PV', ''),
                dialog
            ))
            button_layout.addWidget(send_btn)
            
            copy_btn = QPushButton("Copy")
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(
                subject_input.text(), body_text.toPlainText()
            ))
            button_layout.addWidget(copy_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to draft email: {str(e)}")
    
    def send_email(self, to_email, subject, body, pv, dialog):
        """Send email"""
        try:
            if self.parent_window and self.parent_window.gmail_service:
                self.parent_window.gmail_service.send_email(to_email, subject, body)
                log_sent_email(to_email, subject, pv)
                QMessageBox.information(self, "Success", f"Email sent to {to_email}")
                dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(e)}")
    
    def copy_to_clipboard(self, subject, body):
        """Copy email to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(f"Subject: {subject}\n\n{body}")
        QMessageBox.information(self, "Copied", "Email copied to clipboard!")
    
    def export_to_csv(self):
        """Export acknowledged cases to CSV"""
        try:
            import csv
            from datetime import datetime
            
            filename = f"acknowledged_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save CSV", filename, "CSV Files (*.csv)"
            )
            
            if filepath:
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write headers
                    headers = []
                    for col in range(self.table.columnCount() - 1):  # Skip actions column
                        headers.append(self.table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    # Write data
                    for row in range(self.table.rowCount()):
                        row_data = []
                        for col in range(self.table.columnCount() - 1):
                            item = self.table.item(row, col)
                            row_data.append(item.text() if item else '')
                        writer.writerow(row_data)
                
                QMessageBox.information(self, "Success", f"Data exported to {filepath}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")
    
    def generate_summary(self, all_ack):
        """Generate summary of acknowledged cases"""
        try:
            total = len(all_ack)
            
            # Count by reason
            reasons = {}
            for info in all_ack.values():
                reason = info.get('reason', 'Unknown')
                reasons[reason] = reasons.get(reason, 0) + 1
            
            # Build summary
            summary = f"Total Acknowledged Cases: {total}\n\n"
            summary += "Breakdown by Reason:\n"
            for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
                summary += f"  • {reason}: {count} cases\n"
            
            return summary
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"


class EnhancedMainWindow(QMainWindow):
    """Enhanced main application window with all features"""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Prohealth", "AIAssistantEnhanced")
        self.dark_mode = False
        self.init_services()
        self.init_ui()
        self.load_settings()
        self.apply_theme()
    
    def init_services(self):
        """Initialize backend services"""
        try:
            setup_logging()
            
            # Initialize AI service first
            self.ai_service = AIService()
            
            # Try to initialize Gmail service
            user_email = "unknown"
            try:
                self.gmail_service = GmailService()
                # Get user email for error tracking
                try:
                    user_email = self.gmail_service.service.users().getProfile(userId='me').execute().get('emailAddress', 'unknown')
                except:
                    pass
                
                # Check for CMS credentials on first run
                self.check_and_setup_cms_credentials()
                
            except Exception as gmail_error:
                self.gmail_service = None
                QMessageBox.warning(None, "Gmail Service", 
                                  f"Gmail service not available: {str(gmail_error)}\n\n"
                                  "Run 'python ai_assistant\\gmail_auth_refresh.py' to authenticate.\n"
                                  "Email features will be disabled.")
            
            # Initialize error tracking if available
            if ERROR_TRACKING_AVAILABLE:
                self.error_tracker = initialize_error_tracker(user_email)
            else:
                self.error_tracker = None
            
            # Initialize case manager with user-specific spreadsheet if available
            self.user_spreadsheet_path = self.load_user_spreadsheet_path()
            if self.user_spreadsheet_path and os.path.exists(self.user_spreadsheet_path):
                self.case_manager = CaseManager(self.user_spreadsheet_path)
            else:
                self.case_manager = CaseManager()
            
            # Initialize other services
            # Create email cache service and link it to Gmail service for auto-caching
            self.email_cache_service = EmailCacheService(self.gmail_service) if self.gmail_service else None
            if self.gmail_service and self.email_cache_service:
                # Link the cache service to Gmail for auto-caching sent emails
                self.gmail_service.email_cache_service = self.email_cache_service
                logger.info("Email auto-caching enabled for sent emails")
            
            # Initialize collections tracker
            self.collections_tracker = CollectionsTracker()
            logger.info("Initialized CollectionsTracker")
            
            # Initialize template summary service
            self.template_summary_service = TemplateSummaryService(
                email_cache_service=self.email_cache_service,
                case_manager=self.case_manager
            )
            logger.info("Initialized TemplateSummaryService")
            
            # Set email cache on tracker if available
            if self.email_cache_service:
                self.collections_tracker.email_cache = self.email_cache_service
                logger.info("Email cache service linked to CollectionsTracker")
            
            # Don't auto-bootstrap on startup - user should run Analyze Email Cache
            # This ensures ALL emails are processed, not just a subset
            if (self.email_cache_service and 
                len(self.collections_tracker.data.get("cases", {})) == 0):
                logger.info("No tracking data found - run 'Analyze Email Cache' to populate")
            else:
                logger.info("CollectionsTracker already has data, skipping bootstrap")
            
            # Initialize bulk email service with the collections tracker
            if self.gmail_service:
                self.bulk_email_service = BulkEmailService(
                    self.gmail_service, 
                    self.case_manager, 
                    self.ai_service, 
                    self.collections_tracker,
                    self.email_cache_service
                )
            else:
                self.bulk_email_service = None
            
        except Exception as e:
            QMessageBox.critical(None, "Initialization Error", 
                               f"Failed to initialize core services: {str(e)}\n\n"
                               "Please check your configuration and try again.")
            sys.exit(1)
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Prohealth AI Assistant - Enhanced Medical Lien Management")
        self.setGeometry(100, 100, 1600, 900)
        
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
        
        # Create main tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        
        # Dashboard tab
        self.dashboard_tab = self.create_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        
        # Case Management tab
        self.case_tab = self.create_case_management_tab()
        self.tabs.addTab(self.case_tab, "📁 Cases")
        
        # Email Analysis tab
        self.email_tab = self.create_email_analysis_tab()
        self.tabs.addTab(self.email_tab, "📧 Email Analysis")
        
        # Categories tab - use enhanced tracker if available, otherwise standard
        tracker_to_use = self.collections_tracker
        self.categories_tab = CategoriesWidget(tracker_to_use, self.case_manager, self)
        self.tabs.addTab(self.categories_tab, "📂 Categories")
        
        # Acknowledged Cases tab
        self.acknowledged_cases_tab = AcknowledgedCasesWidget(self.case_manager, self)
        self.tabs.addTab(self.acknowledged_cases_tab, "✅ Acknowledged")
        
        # Bulk Email tab
        if self.bulk_email_service:
            self.bulk_email_tab = BulkEmailWidget(self.bulk_email_service, self.case_manager, self)
            self.tabs.addTab(self.bulk_email_tab, "📨 Bulk Email")
        
        # Collections Tracker tab
        self.collections_tab = self.create_collections_tab()
        self.tabs.addTab(self.collections_tab, "💰 Collections")
        
        # Settings tab
        self.settings_tab = self.create_settings_tab()
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        
        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        
        # Create dock widgets
        self.create_dock_widgets()
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Cases File", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_cases_file)
        
        export_action = QAction("&Export Results", self)
        export_action.setShortcut("Ctrl+E")
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        
        # Spreadsheet management actions
        upload_spreadsheet_action = QAction("📊 &Upload Spreadsheet", self)
        upload_spreadsheet_action.setShortcut("Ctrl+U")
        upload_spreadsheet_action.triggered.connect(self.upload_spreadsheet)
        
        current_spreadsheet_action = QAction("📋 &Current Spreadsheet", self)
        current_spreadsheet_action.triggered.connect(self.show_current_spreadsheet)
        
        file_menu.addAction(upload_spreadsheet_action)
        file_menu.addAction(current_spreadsheet_action)
        file_menu.addSeparator()
        
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        dark_mode_action = QAction("🌙 &Dark Mode", self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        
        view_menu.addAction(dark_mode_action)
        self.dark_mode_action = dark_mode_action
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        refresh_cache_action = QAction("🔄 &Refresh Email Cache", self)
        refresh_cache_action.triggered.connect(self.refresh_email_cache)
        
        bootstrap_emails_action = QAction("📥 Download Email &History", self)
        bootstrap_emails_action.triggered.connect(self.bootstrap_emails)
        
        bootstrap_collections_action = QAction("📊 Analyze Email &Cache", self)
        bootstrap_collections_action.triggered.connect(self.bootstrap_collections)
        
        clear_cache_action = QAction("🗑️ &Clear Cache", self)
        clear_cache_action.triggered.connect(self.clear_cache)
        
        cms_init_action = QAction("🏥 Initialize &CMS Session", self)
        cms_init_action.triggered.connect(self.init_cms_session)
        
        cms_process_notes_action = QAction("📝 Process CMS &Session Notes", self)
        cms_process_notes_action.triggered.connect(self.process_cms_session_notes)
        
        cms_credentials_action = QAction("🔑 Update CMS &Credentials", self)
        cms_credentials_action.triggered.connect(self.update_cms_credentials)
        
        tools_menu.addAction(refresh_cache_action)
        tools_menu.addAction(bootstrap_emails_action)
        tools_menu.addAction(bootstrap_collections_action)
        tools_menu.addSeparator()
        tools_menu.addAction(clear_cache_action)
        tools_menu.addSeparator()
        tools_menu.addAction(cms_credentials_action)
        tools_menu.addAction(cms_init_action)
        tools_menu.addAction(cms_process_notes_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Quick actions
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self.refresh_current_tab)
        
        search_action = QAction("🔍 Search", self)
        search_action.triggered.connect(self.quick_search)
        
        compose_action = QAction("✉️ Compose", self)
        compose_action.triggered.connect(self.quick_compose)
        
        toolbar.addAction(refresh_action)
        toolbar.addAction(search_action)
        toolbar.addAction(compose_action)
        toolbar.addSeparator()
        
        # Add CMS session notes button to toolbar
        cms_notes_action = QAction("📝 CMS Notes", self)
        cms_notes_action.setToolTip("Process pending CMS session notes")
        cms_notes_action.triggered.connect(self.process_cms_session_notes)
        toolbar.addAction(cms_notes_action)
        toolbar.addSeparator()
        
        # Add TEST MODE toggle to toolbar
        self.test_mode_action = QAction("🧪 TEST MODE", self)
        self.test_mode_action.setCheckable(True)
        self.test_mode_action.setToolTip("Toggle TEST MODE - All emails will be sent to test address")
        self.test_mode_action.triggered.connect(self.toggle_test_mode)
        toolbar.addAction(self.test_mode_action)
        
        # Add test mode indicator label
        self.test_mode_indicator = QLabel("")
        self.test_mode_indicator.setStyleSheet("color: red; font-weight: bold; padding: 0 10px;")
        toolbar.addWidget(self.test_mode_indicator)
        toolbar.addSeparator()
        
        # Add dark mode toggle to toolbar
        dark_mode_btn = QPushButton("🌙")
        dark_mode_btn.setCheckable(True)
        dark_mode_btn.clicked.connect(self.toggle_dark_mode)
        toolbar.addWidget(dark_mode_btn)
        self.dark_mode_btn = dark_mode_btn
    
    def create_dock_widgets(self):
        """Create dockable widgets"""
        # Activity log dock
        log_dock = QDockWidget("Activity Log", self)
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(150)
        log_dock.setWidget(self.log_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, log_dock)
        
        # Quick stats dock
        stats_dock = QDockWidget("Quick Stats", self)
        self.stats_widget = QLabel()
        self.update_quick_stats()
        stats_dock.setWidget(self.stats_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, stats_dock)
        
        # Set up timer for periodic updates
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_quick_stats)
        self.stats_timer.start(60000)  # Update every minute
    
    def create_dashboard_tab(self):
        """Create dashboard tab with overview"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Welcome message
        welcome_label = QLabel("<h1>Welcome to Prohealth AI Assistant</h1>")
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Quick stats cards
        cards_layout = QHBoxLayout()
        
        # Total cases card
        total_cases_card = self.create_stat_card(
            "Total Cases", 
            str(len(self.case_manager.df)),
            "📊"
        )
        cards_layout.addWidget(total_cases_card)
        
        # Categories card
        try:
            dashboard = self.collections_tracker.get_collections_dashboard()
            aging_count = dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['30_days']
        except:
            aging_count = 0
        
        aging_cases_card = self.create_stat_card(
            "Case Categories",
            str(aging_count),
            "⏰"
        )
        cards_layout.addWidget(aging_cases_card)
        
        # Emails today card
        emails_today_card = self.create_stat_card(
            "Emails Today",
            "0",  # This would be updated dynamically
            "📧"
        )
        cards_layout.addWidget(emails_today_card)
        
        # CMS Notes card with action button
        self.cms_notes_card = self.create_cms_card()
        cards_layout.addWidget(self.cms_notes_card)
        
        layout.addLayout(cards_layout)
        
        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QGridLayout()
        
        # Create action buttons
        btn_summarize = QPushButton("📄 Summarize Case")
        btn_summarize.clicked.connect(self.quick_summarize)
        
        btn_followup = QPushButton("✉️ Draft Follow-up")
        btn_followup.clicked.connect(self.quick_followup)
        
        btn_bulk = QPushButton("📨 Bulk Email")
        btn_bulk.clicked.connect(lambda: self.tabs.setCurrentWidget(self.bulk_email_tab) if hasattr(self, 'bulk_email_tab') else None)
        
        btn_stale = QPushButton("📂 View Categories")
        btn_stale.clicked.connect(lambda: self.tabs.setCurrentWidget(self.categories_tab) if hasattr(self, 'categories_tab') else None)
        
        actions_layout.addWidget(btn_summarize, 0, 0)
        actions_layout.addWidget(btn_followup, 0, 1)
        actions_layout.addWidget(btn_bulk, 1, 0)
        actions_layout.addWidget(btn_stale, 1, 1)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Recent activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        
        self.activity_list = QListWidget()
        self.activity_list.addItem("Application started")
        activity_layout.addWidget(self.activity_list)
        
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_stat_card(self, title, value, icon):
        """Create a statistics card widget"""
        card = QGroupBox()
        layout = QVBoxLayout()
        
        # Icon and title
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(value_label)
        
        card.setLayout(layout)
        return card
    
    def create_cms_card(self):
        """Create CMS notes card with action button"""
        card = QGroupBox()
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("📝 CMS Notes")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        
        # Get stats
        try:
            if CMS_AVAILABLE and get_session_stats:
                cms_stats = get_session_stats()
                pending_count = cms_stats.get('pending_count', 0)
                processed_count = cms_stats.get('processed_count', 0)
                total_notes = cms_stats.get('notes_added_count', 0)
                status_color = "red" if pending_count > 0 else "green"
            else:
                pending_count = "N/A"
                processed_count = 0
                total_notes = 0
                status_color = "gray"
        except:
            pending_count = "N/A"
            processed_count = 0
            total_notes = 0
            status_color = "gray"
        
        # Display pending/processed counts
        self.cms_count_label = QLabel()
        if pending_count != "N/A":
            if pending_count > 0:
                self.cms_count_label.setText(f"{pending_count} pending")
                self.cms_count_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {status_color};")
            else:
                self.cms_count_label.setText("All processed")
                self.cms_count_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: green;")
            
            # Only add the pending/processed status label
            layout.addWidget(self.cms_count_label)
        else:
            self.cms_count_label.setText("N/A")
            self.cms_count_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: gray;")
            layout.addWidget(self.cms_count_label)
        
        # Process button
        if CMS_AVAILABLE:
            process_btn = QPushButton("Process Notes")
            process_btn.clicked.connect(self.process_cms_session_notes)
            if pending_count == "N/A" or pending_count == 0:
                process_btn.setEnabled(False)
            layout.addWidget(process_btn)
        else:
            na_label = QLabel("CMS not available")
            na_label.setStyleSheet("font-size: 10px; color: gray;")
            layout.addWidget(na_label)
        
        card.setLayout(layout)
        return card
    
    def create_case_management_tab(self):
        """Create case management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.case_search_input = QLineEdit()
        self.case_search_input.setPlaceholderText("Search by PV#, Name, or CMS#...")
        self.case_search_button = QPushButton("🔍 Search")
        self.case_search_button.clicked.connect(self.search_cases)
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.case_search_input)
        search_layout.addWidget(self.case_search_button)
        
        # Case table
        self.case_table = QTableWidget()
        self.case_table.setColumnCount(8)
        self.case_table.setHorizontalHeaderLabels([
            "PV #", "Name", "CMS #", "DOI", 
            "Attorney Email", "Law Firm", "Status", "Actions"
        ])
        self.case_table.setAlternatingRowColors(True)
        self.case_table.setSortingEnabled(True)
        
        # Load cases on startup (wrapped in try-except for initialization safety)
        # Defer loading to after UI is shown to prevent blocking
        # try:
        #     self.load_all_cases()
        # except Exception as e:
        #     print(f"Initial case load deferred: {e}")
        QTimer.singleShot(100, self.load_all_cases)  # Load after UI is shown
        
        layout.addLayout(search_layout)
        layout.addWidget(self.case_table)
        
        widget.setLayout(layout)
        return widget
    
    def check_and_setup_cms_credentials(self):
        """Check if CMS credentials exist, prompt for them if not"""
        import os
        from dotenv import load_dotenv, set_key
        
        # Get the config.env path
        config_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(config_dir, 'config.env')
        
        # Load current environment
        load_dotenv(env_path)
        
        # Check if CMS credentials are already configured
        cms_username = os.getenv("CMS_USERNAME")
        cms_password = os.getenv("CMS_PASSWORD")
        
        # If not configured or still have placeholder values, prompt user
        if (not cms_username or not cms_password or 
            cms_username == "YOUR_CMS_USERNAME_HERE" or 
            cms_password == "YOUR_CMS_PASSWORD_HERE"):
            
            # Create dialog for CMS credentials
            dialog = QDialog(self)
            dialog.setWindowTitle("CMS Setup Required")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout()
            
            # Instructions
            instructions = QLabel(
                "Welcome! Please enter your CMS credentials.\n"
                "These will be saved securely in your config.env file.\n"
                "You can update them later by editing config.env directly."
            )
            instructions.setWordWrap(True)
            layout.addWidget(instructions)
            
            # Username input
            username_label = QLabel("CMS Username:")
            layout.addWidget(username_label)
            username_input = QLineEdit()
            if cms_username and cms_username != "YOUR_CMS_USERNAME_HERE":
                username_input.setText(cms_username)
            layout.addWidget(username_input)
            
            # Password input
            password_label = QLabel("CMS Password:")
            layout.addWidget(password_label)
            password_input = QLineEdit()
            password_input.setEchoMode(QLineEdit.Password)
            if cms_password and cms_password != "YOUR_CMS_PASSWORD_HERE":
                password_input.setText(cms_password)
            layout.addWidget(password_input)
            
            # Buttons
            button_layout = QHBoxLayout()
            save_btn = QPushButton("Save Credentials")
            skip_btn = QPushButton("Skip (CMS features disabled)")
            button_layout.addWidget(save_btn)
            button_layout.addWidget(skip_btn)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # Button handlers
            def save_credentials():
                username = username_input.text().strip()
                password = password_input.text().strip()
                
                if not username or not password:
                    QMessageBox.warning(dialog, "Missing Information", 
                                       "Please enter both username and password.")
                    return
                
                try:
                    # Save to config.env
                    set_key(env_path, "CMS_USERNAME", username)
                    set_key(env_path, "CMS_PASSWORD", password)
                    
                    # Reload environment
                    os.environ["CMS_USERNAME"] = username
                    os.environ["CMS_PASSWORD"] = password
                    
                    QMessageBox.information(dialog, "Success", 
                                          "CMS credentials saved successfully!")
                    dialog.accept()
                except Exception as e:
                    QMessageBox.critical(dialog, "Error", 
                                       f"Failed to save credentials: {str(e)}")
            
            def skip_setup():
                reply = QMessageBox.question(dialog, "Skip CMS Setup?",
                                           "Are you sure you want to skip CMS setup?\n"
                                           "CMS features will be disabled until you configure credentials.",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    dialog.reject()
            
            save_btn.clicked.connect(save_credentials)
            skip_btn.clicked.connect(skip_setup)
            
            # Show dialog
            dialog.exec_()
    
    def update_cms_credentials(self):
        """Allow user to update CMS credentials at any time"""
        import os
        from dotenv import load_dotenv, set_key
        
        # Get the config.env path
        config_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(config_dir, 'config.env')
        
        # Load current environment
        load_dotenv(env_path)
        
        # Get current credentials
        cms_username = os.getenv("CMS_USERNAME", "")
        cms_password = os.getenv("CMS_PASSWORD", "")
        
        # Create dialog for CMS credentials
        dialog = QDialog(self)
        dialog.setWindowTitle("Update CMS Credentials")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Update your CMS credentials below.\n"
            "These will be saved in your config.env file and used for all CMS operations.\n"
            "Leave blank to keep existing values."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Username input
        username_label = QLabel("CMS Username:")
        layout.addWidget(username_label)
        username_input = QLineEdit()
        if cms_username and cms_username != "YOUR_CMS_USERNAME_HERE":
            username_input.setText(cms_username)
            username_input.setPlaceholderText(f"Current: {cms_username}")
        else:
            username_input.setPlaceholderText("Enter username")
        layout.addWidget(username_input)
        
        # Password input  
        password_label = QLabel("CMS Password:")
        layout.addWidget(password_label)
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        if cms_password and cms_password != "YOUR_CMS_PASSWORD_HERE":
            password_input.setPlaceholderText("Current password is set")
        else:
            password_input.setPlaceholderText("Enter password")
        layout.addWidget(password_input)
        
        # Show password checkbox
        show_password = QCheckBox("Show password")
        def toggle_password():
            if show_password.isChecked():
                password_input.setEchoMode(QLineEdit.Normal)
            else:
                password_input.setEchoMode(QLineEdit.Password)
        show_password.toggled.connect(toggle_password)
        layout.addWidget(show_password)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Credentials")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Button handlers
        def save_credentials():
            new_username = username_input.text().strip()
            new_password = password_input.text().strip()
            
            # Use existing values if not changed
            if not new_username:
                new_username = cms_username
            if not new_password:
                new_password = cms_password
                
            if not new_username or not new_password:
                QMessageBox.warning(dialog, "Missing Information", 
                                   "Please enter both username and password.")
                return
            
            try:
                # Save to config.env
                set_key(env_path, "CMS_USERNAME", new_username)
                set_key(env_path, "CMS_PASSWORD", new_password)
                
                # Update environment variables immediately
                os.environ["CMS_USERNAME"] = new_username
                os.environ["CMS_PASSWORD"] = new_password
                
                # Force CMS service to reload credentials if it exists
                if hasattr(self, 'cms_service') and self.cms_service:
                    self.cms_service.username = new_username
                    self.cms_service.password = new_password
                
                # Reset CMS session to use new credentials
                if CMS_AVAILABLE:
                    from services.cms_integration import CMSIntegrationService
                    CMSIntegrationService._persistent_logged_in = False
                
                QMessageBox.information(dialog, "Success", 
                                      "CMS credentials updated successfully!\n"
                                      "New credentials will be used for all future CMS operations.")
                dialog.accept()
                
                # Log the activity
                self.log_activity("CMS credentials updated")
                
            except Exception as e:
                QMessageBox.critical(dialog, "Error", 
                                   f"Failed to save credentials: {str(e)}")
        
        save_btn.clicked.connect(save_credentials)
        cancel_btn.clicked.connect(dialog.reject)
        
        # Show dialog
        dialog.exec_()
    
    def create_email_analysis_tab(self):
        """Create email analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Case selection
        case_layout = QHBoxLayout()
        case_layout.addWidget(QLabel("Case PV:"))
        self.email_case_input = QLineEdit()
        self.email_case_input.setPlaceholderText("Enter PV number...")
        case_layout.addWidget(self.email_case_input)
        
        self.analyze_btn = QPushButton("🔍 Analyze Emails")
        self.analyze_btn.clicked.connect(self.analyze_case_emails)
        case_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(case_layout)
        
        # Results area
        splitter = QSplitter(Qt.Horizontal)
        
        # Email list
        email_group = QGroupBox("Email Threads")
        email_layout = QVBoxLayout()
        self.email_list = QListWidget()
        email_layout.addWidget(self.email_list)
        email_group.setLayout(email_layout)
        
        # AI Summary
        summary_group = QGroupBox("AI Analysis")
        summary_layout = QVBoxLayout()
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.draft_followup_btn = QPushButton("✉️ Draft Follow-up")
        self.draft_followup_btn.clicked.connect(self.draft_followup_from_analysis)
        self.draft_followup_btn.setEnabled(False)
        
        self.draft_status_btn = QPushButton("📮 Draft Status Request")
        self.draft_status_btn.clicked.connect(self.draft_status_from_analysis)
        self.draft_status_btn.setEnabled(False)
        
        action_layout.addWidget(self.draft_followup_btn)
        action_layout.addWidget(self.draft_status_btn)
        summary_layout.addLayout(action_layout)
        
        summary_group.setLayout(summary_layout)
        
        splitter.addWidget(email_group)
        splitter.addWidget(summary_group)
        
        layout.addWidget(splitter)
        widget.setLayout(layout)
        return widget
    
    def create_collections_tab(self):
        """Create collections tracker tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Dashboard
        dashboard_group = QGroupBox("Collections Dashboard")
        dashboard_layout = QVBoxLayout()
        
        self.collections_stats = QTextEdit()
        self.collections_stats.setReadOnly(True)
        self.collections_stats.setMaximumHeight(200)
        
        refresh_btn = QPushButton("🔄 Refresh Dashboard")
        refresh_btn.clicked.connect(self.refresh_collections_dashboard)
        
        dashboard_layout.addWidget(self.collections_stats)
        dashboard_layout.addWidget(refresh_btn)
        dashboard_group.setLayout(dashboard_layout)
        
        # Top responsive firms
        firms_group = QGroupBox("Top Responsive Firms")
        firms_layout = QVBoxLayout()
        
        self.firms_table = QTableWidget()
        self.firms_table.setColumnCount(3)
        self.firms_table.setHorizontalHeaderLabels(["Law Firm", "Response Rate", "Total Cases"])
        
        firms_layout.addWidget(self.firms_table)
        firms_group.setLayout(firms_layout)
        
        layout.addWidget(dashboard_group)
        layout.addWidget(firms_group)
        
        widget.setLayout(layout)
        
        # Load initial data - defer to prevent blocking
        # self.refresh_collections_dashboard()
        QTimer.singleShot(500, self.refresh_collections_dashboard)
        
        return widget
    
    def create_settings_tab(self):
        """Create settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # API Settings
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout()
        
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("OpenAI API Key:", self.openai_key_input)
        
        self.gmail_creds_path = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_credentials)
        creds_layout = QHBoxLayout()
        creds_layout.addWidget(self.gmail_creds_path)
        creds_layout.addWidget(browse_btn)
        api_layout.addRow("Gmail Credentials:", creds_layout)
        
        api_group.setLayout(api_layout)
        
        # Display Settings
        display_group = QGroupBox("Display Settings")
        display_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Auto"])
        display_layout.addRow("Theme:", self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(8)
        self.font_size_spin.setMaximum(20)
        self.font_size_spin.setValue(10)
        display_layout.addRow("Font Size:", self.font_size_spin)
        
        display_group.setLayout(display_layout)
        
        # Automation Settings
        auto_group = QGroupBox("Automation Settings")
        auto_layout = QFormLayout()
        
        self.auto_refresh_check = QCheckBox("Enable Auto-refresh")
        auto_layout.addRow("Auto-refresh:", self.auto_refresh_check)
        
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setMinimum(1)
        self.refresh_interval_spin.setMaximum(60)
        self.refresh_interval_spin.setValue(5)
        self.refresh_interval_spin.setSuffix(" minutes")
        auto_layout.addRow("Refresh Interval:", self.refresh_interval_spin)
        
        self.auto_cms_check = QCheckBox("Auto-add CMS notes")
        auto_layout.addRow("CMS Integration:", self.auto_cms_check)
        
        auto_group.setLayout(auto_layout)
        
        # Email Cadence Settings
        cadence_group = QGroupBox("Email Cadence Profile")
        cadence_layout = QVBoxLayout()
        
        cadence_info = QLabel(
            "Choose which email cadence profile to use for drafting emails.\n"
            "Your personal cadence is based on your email history."
        )
        cadence_info.setWordWrap(True)
        cadence_layout.addWidget(cadence_info)
        
        # Radio buttons for cadence selection
        self.personal_cadence_radio = QRadioButton("Use my personal email cadence")
        self.default_cadence_radio = QRadioButton("Use default professional cadence (standard/mellow)")
        
        # Set initial selection based on current profile
        if hasattr(self, 'email_cache_service') and self.email_cache_service:
            current_profile = self.email_cache_service.get_cadence_profile_name()
            if current_profile == 'default':
                self.default_cadence_radio.setChecked(True)
            else:
                self.personal_cadence_radio.setChecked(True)
        else:
            self.personal_cadence_radio.setChecked(True)
        
        # Connect radio buttons to handler
        self.personal_cadence_radio.toggled.connect(self.on_cadence_profile_changed)
        self.default_cadence_radio.toggled.connect(self.on_cadence_profile_changed)
        
        cadence_layout.addWidget(self.personal_cadence_radio)
        cadence_layout.addWidget(self.default_cadence_radio)
        
        # Add view button to see cadence details
        view_cadence_btn = QPushButton("📊 View Cadence Details")
        view_cadence_btn.clicked.connect(self.show_cadence_details)
        cadence_layout.addWidget(view_cadence_btn)
        
        cadence_group.setLayout(cadence_layout)
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        
        layout.addWidget(api_group)
        layout.addWidget(display_group)
        layout.addWidget(auto_group)
        layout.addWidget(cadence_group)
        layout.addWidget(save_btn)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    # Helper methods
    def toggle_dark_mode(self):
        """Toggle dark mode"""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.dark_mode_action.setChecked(self.dark_mode)
        self.dark_mode_btn.setChecked(self.dark_mode)
    
    def toggle_test_mode(self):
        """Toggle test mode for bulk emails"""
        if not hasattr(self, 'bulk_email_service') or not self.bulk_email_service:
            QMessageBox.warning(self, "Not Available", "Bulk email service is not initialized.")
            self.test_mode_action.setChecked(False)
            return
        
        if self.test_mode_action.isChecked():
            # Enable test mode - ask for test email
            test_email, ok = QInputDialog.getText(
                self, "Enable TEST MODE",
                "Enter test email address where ALL emails will be sent:",
                text="deanh.transcon@gmail.com"
            )
            
            if ok and test_email:
                self.bulk_email_service.set_test_mode(True, test_email)
                self.test_mode_indicator.setText(f"🧪 TEST MODE: {test_email}")
                self.test_mode_indicator.setStyleSheet("color: red; font-weight: bold; padding: 0 10px; background-color: yellow;")
                
                # Update the title bar to show TEST MODE
                self.update_window_title()
                
                # Show warning message
                QMessageBox.information(
                    self, "TEST MODE ENABLED",
                    f"TEST MODE is now ACTIVE!\n\n"
                    f"• ALL emails will be sent to: {test_email}\n"
                    f"• Email subjects will include [TEST MODE]\n"
                    f"• CMS notes will be prefixed with (TEST)\n\n"
                    f"Remember to disable TEST MODE when done testing!"
                )
                
                self.log_activity(f"TEST MODE ENABLED - Emails will go to: {test_email}")
                
                # Update bulk email tab if it exists
                if hasattr(self, 'bulk_email_tab'):
                    self.bulk_email_tab.update_test_mode_display()
            else:
                # User cancelled
                self.test_mode_action.setChecked(False)
        else:
            # Disable test mode
            self.bulk_email_service.set_test_mode(False)
            self.test_mode_indicator.setText("")
            self.test_mode_indicator.setStyleSheet("")
            
            # Update the title bar
            self.update_window_title()
            
            QMessageBox.information(
                self, "TEST MODE DISABLED",
                "TEST MODE has been disabled.\n"
                "Emails will now be sent to actual recipients."
            )
            
            self.log_activity("TEST MODE DISABLED - Normal operation resumed")
            
            # Update bulk email tab if it exists
            if hasattr(self, 'bulk_email_tab'):
                self.bulk_email_tab.update_test_mode_display()
    
    def update_window_title(self):
        """Update window title with TEST MODE indicator if active"""
        base_title = "Prohealth AI Assistant"
        if hasattr(self, 'test_mode_action') and self.test_mode_action.isChecked():
            self.setWindowTitle(f"🧪 {base_title} - TEST MODE ACTIVE")
        else:
            self.setWindowTitle(base_title)
    
    def show_log_viewer(self):
        """Show the log viewer dialog"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("System Logs and Error Reports")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout()
            
            # Tab widget for different log types
            tabs = QTabWidget()
            
            # Activity Log Tab
            activity_tab = QWidget()
            activity_layout = QVBoxLayout()
            
            activity_text = QTextEdit()
            activity_text.setReadOnly(True)
            activity_text.setPlainText(self.activity_log.toPlainText())
            activity_layout.addWidget(activity_text)
            
            activity_tab.setLayout(activity_layout)
            tabs.addTab(activity_tab, "Activity Log")
            
            # Error Log Tab
            if ERROR_TRACKING_AVAILABLE and self.error_tracker:
                error_tab = QWidget()
                error_layout = QVBoxLayout()
                
                error_text = QTextEdit()
                error_text.setReadOnly(True)
                
                # Get error summary
                summary = self.error_tracker.get_error_summary()
                report = self.error_tracker.create_error_report(include_system=False)
                
                error_text.setPlainText(f"""Error Summary:
--------------
Total Errors Today: {summary['total_errors_today']}
Session Errors: {summary['total_errors_session']}

Detailed Report:
----------------
{report}""")
                
                error_layout.addWidget(error_text)
                
                # Export button
                export_btn = QPushButton("Export Full Error Report")
                export_btn.clicked.connect(lambda: self.export_error_report(from_dialog=True))
                error_layout.addWidget(export_btn)
                
                error_tab.setLayout(error_layout)
                tabs.addTab(error_tab, f"Error Log ({summary['total_errors_today']})")
            
            # System Info Tab
            info_tab = QWidget()
            info_layout = QVBoxLayout()
            
            info_text = QTextEdit()
            info_text.setReadOnly(True)
            
            system_info = "System Information:\\n-------------------\\n"
            if ERROR_TRACKING_AVAILABLE and self.error_tracker:
                for key, value in self.error_tracker.system_info.items():
                    if key != "python_version":
                        system_info += f"{key}: {value}\\n"
            
            info_text.setPlainText(system_info)
            info_layout.addWidget(info_text)
            
            info_tab.setLayout(info_layout)
            tabs.addTab(info_tab, "System Info")
            
            layout.addWidget(tabs)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show log viewer: {str(e)}")
    
    def export_error_report(self, from_dialog: bool = False):
        """Export error report for support"""
        try:
            if not ERROR_TRACKING_AVAILABLE or not self.error_tracker:
                QMessageBox.warning(self, "Not Available", 
                                   "Error tracking is not available.")
                return
            
            # Generate report
            report_file = self.error_tracker.export_for_support()
            
            # Ask user where to save
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Error Report",
                f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt)"
            )
            
            if save_path:
                import shutil
                shutil.copy2(report_file, save_path)
                
                QMessageBox.information(
                    self, "Report Exported",
                    f"Error report saved to:\\n{save_path}\\n\\n"
                    "You can share this file with support for debugging."
                )
                
                self.log_activity(f"Error report exported to: {save_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export error report: {str(e)}")
    
    def apply_theme(self):
        """Apply the current theme"""
        if self.dark_mode:
            # Dark theme
            dark_stylesheet = """
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444444;
                background-color: #353535;
            }
            QTabBar::tab {
                background-color: #353535;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #404040;
                border-bottom: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QLineEdit, QTextEdit, QListWidget, QTableWidget {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QSpinBox {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QCheckBox {
                color: #ffffff;
            }
            QMenuBar {
                background-color: #353535;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #404040;
            }
            QMenu {
                background-color: #353535;
                color: #ffffff;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
            }
            QToolBar {
                background-color: #353535;
                border: none;
            }
            QStatusBar {
                background-color: #353535;
                color: #ffffff;
            }
            QDockWidget {
                color: #ffffff;
            }
            QDockWidget::title {
                background-color: #353535;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }
            """
            self.setStyleSheet(dark_stylesheet)
        else:
            # Light theme
            light_stylesheet = """
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
            QTableWidget {
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            """
            self.setStyleSheet(light_stylesheet)
    
    def load_all_cases(self):
        """Load all cases into the table"""
        try:
            # Check if case_manager and df exist and have data
            if not hasattr(self, 'case_manager'):
                print("ERROR: No case_manager initialized")
                return
            
            if self.case_manager.df.empty:
                print("WARNING: Case manager DataFrame is empty")
                print(f"DataFrame shape: {self.case_manager.df.shape}")
                return
            
            cases = []
            for _, row in self.case_manager.df.iterrows():
                case = self.case_manager.format_case(row)
                cases.append(case)
            
            self.case_table.setRowCount(len(cases))
            
            for row, case in enumerate(cases):
                self.case_table.setItem(row, 0, QTableWidgetItem(str(case.get('PV', ''))))
                self.case_table.setItem(row, 1, QTableWidgetItem(str(case.get('Name', ''))))
                self.case_table.setItem(row, 2, QTableWidgetItem(str(case.get('CMS', ''))))
                self.case_table.setItem(row, 3, QTableWidgetItem(str(case.get('DOI', ''))))
                self.case_table.setItem(row, 4, QTableWidgetItem(str(case.get('Attorney Email', ''))))
                self.case_table.setItem(row, 5, QTableWidgetItem(str(case.get('Law Firm', ''))))
                self.case_table.setItem(row, 6, QTableWidgetItem(str(case.get('Status', ''))))
                
                # Actions button
                action_btn = QPushButton("Actions")
                action_menu = QMenu()
                
                summarize_action = action_menu.addAction("📄 Summarize")
                summarize_action.triggered.connect(lambda checked, pv=case.get('PV'): self.summarize_case_by_pv(pv))
                
                followup_action = action_menu.addAction("✉️ Draft Follow-up")
                followup_action.triggered.connect(lambda checked, pv=case.get('PV'): self.draft_followup_by_pv(pv))
                
                status_action = action_menu.addAction("📮 Draft Status Request")
                status_action.triggered.connect(lambda checked, pv=case.get('PV'): self.draft_status_request_by_pv(pv))
                
                action_btn.setMenu(action_menu)
                self.case_table.setCellWidget(row, 7, action_btn)
            
            self.case_table.resizeColumnsToContents()
            self.log_activity(f"Loaded {len(cases)} cases")
            
        except Exception as e:
            import traceback
            print(f"ERROR loading cases: {str(e)}")
            print(f"Full traceback:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to load cases: {str(e)}\n\nCheck console for details.")
    
    def search_cases(self):
        """Search for cases"""
        search_term = self.case_search_input.text().strip()
        if not search_term:
            self.load_all_cases()
            return
        
        try:
            results = self.case_manager.search_case(search_term)
            if results:
                cases = [results] if isinstance(results, dict) else results
                self.case_table.setRowCount(len(cases))
                
                for row, case in enumerate(cases):
                    self.case_table.setItem(row, 0, QTableWidgetItem(str(case.get('PV', ''))))
                    self.case_table.setItem(row, 1, QTableWidgetItem(str(case.get('Name', ''))))
                    self.case_table.setItem(row, 2, QTableWidgetItem(str(case.get('CMS', ''))))
                    self.case_table.setItem(row, 3, QTableWidgetItem(str(case.get('DOI', ''))))
                    self.case_table.setItem(row, 4, QTableWidgetItem(str(case.get('Attorney Email', ''))))
                    self.case_table.setItem(row, 5, QTableWidgetItem(str(case.get('Law Firm', ''))))
                    self.case_table.setItem(row, 6, QTableWidgetItem(str(case.get('Status', ''))))
                    
                    # Actions button
                    action_btn = QPushButton("Actions")
                    action_menu = QMenu()
                    
                    summarize_action = action_menu.addAction("📄 Summarize")
                    summarize_action.triggered.connect(lambda checked, pv=case.get('PV'): self.summarize_case_by_pv(pv))
                    
                    followup_action = action_menu.addAction("✉️ Draft Follow-up")
                    followup_action.triggered.connect(lambda checked, pv=case.get('PV'): self.draft_followup_by_pv(pv))
                    
                    status_action = action_menu.addAction("📮 Draft Status Request")
                    status_action.triggered.connect(lambda checked, pv=case.get('PV'): self.draft_status_request_by_pv(pv))
                    
                    action_btn.setMenu(action_menu)
                    self.case_table.setCellWidget(row, 7, action_btn)
                
                self.case_table.resizeColumnsToContents()
                self.log_activity(f"Found {len(cases)} cases for '{search_term}'")
            else:
                QMessageBox.information(self, "No Results", "No cases found matching your search.")
                
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"Error searching cases: {str(e)}")
    
    def analyze_case_emails(self):
        """Analyze emails for a case"""
        pv = self.email_case_input.text().strip()
        if not pv:
            QMessageBox.warning(self, "Warning", "Please enter a PV number.")
            return
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Get case
            case = self.case_manager.get_case_by_pv(pv)
            if not case:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "Not Found", f"Case PV {pv} not found.")
                return
            
            # Build search query
            query = f'"{case["Name"]}" OR {case["PV"]}'
            if case.get('CMS'):
                query += f' OR {case["CMS"]}'
            
            # Search for emails
            if self.gmail_service:
                email_messages = self.gmail_service.search_messages(query, max_results=10)
            else:
                email_messages = []
            
            # Display emails
            self.email_list.clear()
            for msg in email_messages:
                item_text = f"{msg.get('from', 'Unknown')} - {msg.get('subject', 'No Subject')}"
                self.email_list.addItem(item_text)
            
            # Generate AI summary
            if email_messages and self.ai_service:
                summary = self.ai_service.summarize_case_emails(case, email_messages)
                self.summary_text.setPlainText(summary)
            else:
                self.summary_text.setPlainText("No emails found or AI service unavailable.")
            
            # Enable action buttons
            self.draft_followup_btn.setEnabled(True)
            self.draft_status_btn.setEnabled(True)
            
            # Store current case for actions
            self.current_analysis_case = case
            self.current_analysis_emails = email_messages
            
            QApplication.restoreOverrideCursor()
            self.log_activity(f"Analyzed emails for PV {pv}")
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to analyze emails: {str(e)}")
    
    def draft_followup_from_analysis(self):
        """Draft follow-up from current analysis"""
        if hasattr(self, 'current_analysis_case'):
            self.draft_followup_by_pv(self.current_analysis_case['PV'])
    
    def draft_status_from_analysis(self):
        """Draft status request from current analysis"""
        if hasattr(self, 'current_analysis_case'):
            self.draft_status_request_by_pv(self.current_analysis_case['PV'])
    
    def refresh_collections_dashboard(self):
        """Refresh collections dashboard"""
        try:
            dashboard = self.collections_tracker.get_collections_dashboard()
            
            stats_text = f"""
Total tracked cases: {dashboard['total_cases']}

Case Status Breakdown:
"""
            for status, count in dashboard['status_breakdown'].items():
                stats_text += f"  {status.title()}: {count}\n"
            
            stats_text += f"""
Case Aging:
  30+ days: {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['30_days']} cases
  60+ days: {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['60_days']} cases
  90+ days: {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['90_days']} cases
"""
            
            self.collections_stats.setPlainText(stats_text)
            
            # Update firms table
            if dashboard['top_responsive_firms']:
                self.firms_table.setRowCount(len(dashboard['top_responsive_firms']))
                for row, (firm, rate) in enumerate(dashboard['top_responsive_firms']):
                    self.firms_table.setItem(row, 0, QTableWidgetItem(firm))
                    self.firms_table.setItem(row, 1, QTableWidgetItem(f"{rate:.1f}%"))
                    # Would need to get total cases for firm
                    self.firms_table.setItem(row, 2, QTableWidgetItem("N/A"))
            
            self.log_activity("Refreshed collections dashboard")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh dashboard: {str(e)}")
    
    def update_quick_stats(self):
        """Update quick statistics in dock"""
        try:
            dashboard = self.collections_tracker.get_collections_dashboard()
            
            # Get pending CMS notes count
            try:
                cms_stats = get_session_stats()
                pending_cms = cms_stats.get('pending_count', 0)
            except:
                pending_cms = 0
            
            stats_html = f"""
            <b>Quick Stats:</b><br>
            Total Cases: {len(self.case_manager.df)}<br>
            No Response (30+ days): {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['30_days']}<br>
            Critical (90+ days): {dashboard.get('aging_cases', dashboard.get('stale_cases', {}))['90_days']}<br>
            Pending CMS Notes: {pending_cms}<br>
            <br>
            <small>Updated: {datetime.now().strftime('%H:%M')}</small>
            """
            
            self.stats_widget.setText(stats_html)
            
        except Exception as e:
            self.stats_widget.setText(f"Error loading stats: {str(e)}")
    
    def update_cms_card(self):
        """Update the CMS card with current pending notes count"""
        if not hasattr(self, 'cms_count_label'):
            return
        
        try:
            if CMS_AVAILABLE and get_session_stats:
                cms_stats = get_session_stats()
                pending_count = cms_stats.get('pending_count', 0)
                processed_count = cms_stats.get('processed_count', 0)
                total_notes = cms_stats.get('notes_added_count', 0)
                
                # Update label text and color
                if pending_count > 0:
                    self.cms_count_label.setText(f"{pending_count} pending")
                    self.cms_count_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
                else:
                    self.cms_count_label.setText("All processed")
                    self.cms_count_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
                
                # Update button state if it exists
                if hasattr(self, 'cms_notes_card'):
                    # Find the process button in the card
                    for widget in self.cms_notes_card.findChildren(QPushButton):
                        if widget.text() == "Process Notes":
                            widget.setEnabled(pending_count > 0)
                            break
            else:
                self.cms_count_label.setText("N/A")
                self.cms_count_label.setStyleSheet("font-size: 24px; font-weight: bold; color: gray;")
                
        except Exception as e:
            print(f"Error updating CMS card: {e}")
            self.cms_count_label.setText("Error")
            self.cms_count_label.setStyleSheet("font-size: 24px; font-weight: bold; color: orange;")
    
    # Action methods
    def summarize_case_by_pv(self, pv, category_widget=None):
        """Summarize a case by PV number
        
        Args:
            pv: Patient Visit number
            category_widget: Optional reference to the category widget that opened this summary
        """
        try:
            case = self.case_manager.get_case_by_pv(pv)
            if not case:
                QMessageBox.warning(self, "Not Found", f"Case PV {pv} not found.")
                return
            
            # Show summary dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Case Summary - PV {pv}")
            dialog.setMinimumSize(800, 600)
            
            layout = QVBoxLayout()
            
            # Case info
            info_text = f"""
            <b>Patient:</b> {case['Name']}<br>
            <b>PV #:</b> {case['PV']} | <b>CMS:</b> {case['CMS']}<br>
            <b>DOI:</b> {case['DOI']}<br>
            <b>Attorney:</b> {case['Attorney Email']}<br>
            <b>Law Firm:</b> {case['Law Firm']}
            """
            info_label = QLabel(info_text)
            layout.addWidget(info_label)
            
            # Summary text
            summary_text = QTextEdit()
            summary_text.setReadOnly(True)
            summary_text.setFont(QFont("Consolas", 10))  # Use monospace font for better formatting
            
            # Generate template-based summary FIRST (instant)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Use template summary service for instant results
            if hasattr(self, 'template_summary_service'):
                template_summary = self.template_summary_service.generate_summary(pv, case)
                summary_text.setPlainText(template_summary)
                summary_label = QLabel("<b>Case Analysis:</b>")
            else:
                # Fallback to AI if template service not available
                summary_label = QLabel("<b>AI Summary:</b>")
                # Search for emails
                query = f'"{case["Name"]}" OR {case["PV"]}'
                if case.get('CMS'):
                    query += f' OR {case["CMS"]}'
                
                if self.gmail_service:
                    email_messages = self.gmail_service.search_messages(query, max_results=10)
                    if email_messages and self.ai_service:
                        summary = self.ai_service.summarize_case_emails(case, email_messages)
                        summary_text.setPlainText(summary)
                    else:
                        summary_text.setPlainText("No emails found or AI service unavailable.")
                else:
                    summary_text.setPlainText("Gmail service not available.")
            
            QApplication.restoreOverrideCursor()
            
            layout.addWidget(summary_label)
            layout.addWidget(summary_text)
            
            # Add refresh button to optionally enhance with AI
            if hasattr(self, 'template_summary_service') and self.ai_service and self.gmail_service:
                enhance_layout = QHBoxLayout()
                enhance_btn = QPushButton("🤖 Enhance with AI")
                enhance_btn.setToolTip("Use ChatGPT to add more insights")
                
                def enhance_with_ai():
                    QApplication.setOverrideCursor(Qt.WaitCursor)
                    query = f'"{case["Name"]}" OR {case["PV"]}'
                    if case.get('CMS'):
                        query += f' OR {case["CMS"]}'
                    email_messages = self.gmail_service.search_messages(query, max_results=10)
                    if email_messages:
                        ai_summary = self.ai_service.summarize_case_emails(case, email_messages)
                        # Append AI insights to existing summary
                        current_text = summary_text.toPlainText()
                        enhanced = f"{current_text}\n\n{'='*60}\n🤖 AI ENHANCED INSIGHTS\n{'='*60}\n{ai_summary}"
                        summary_text.setPlainText(enhanced)
                    QApplication.restoreOverrideCursor()
                    enhance_btn.setEnabled(False)
                    enhance_btn.setText("✅ Enhanced")
                
                enhance_btn.clicked.connect(enhance_with_ai)
                enhance_layout.addWidget(enhance_btn)
                enhance_layout.addStretch()
                layout.addLayout(enhance_layout)
            
            # Action buttons
            button_layout = QHBoxLayout()
            
            followup_btn = QPushButton("✉️ Draft Follow-up")
            # Pass category_widget through to ensure case is removed from category after sending
            followup_btn.clicked.connect(lambda: self.draft_followup_by_pv(pv, category_widget=category_widget))
            
            status_btn = QPushButton("📮 Draft Status Request")
            # Pass category_widget through to ensure case is removed from category after sending
            status_btn.clicked.connect(lambda: self.draft_status_request_by_pv(pv, category_widget=category_widget))
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            
            button_layout.addWidget(followup_btn)
            button_layout.addWidget(status_btn)
            button_layout.addStretch()
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
            self.log_activity(f"Summarized case PV {pv}")
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to summarize case: {str(e)}")
    
    def draft_followup_by_pv(self, pv, category_widget=None):
        """Draft follow-up email for a case"""
        try:
            case = self.case_manager.get_case_by_pv(pv)
            if not case:
                QMessageBox.warning(self, "Not Found", f"Case PV {pv} not found.")
                return
            
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Search for email threads
            query = f'"{case["Name"]}" OR {case["PV"]}'
            if case.get('CMS'):
                query += f' OR {case["CMS"]}'
            
            if not self.gmail_service:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(self, "Service Unavailable", "Gmail service not available.")
                return
            
            # Get organized threads using the new method
            organized_threads = self.gmail_service.get_organized_threads(query, max_threads=10)
            
            QApplication.restoreOverrideCursor()
            
            # Handle no threads found
            if not organized_threads:
                QMessageBox.information(self, "No Emails", 
                                       "No email threads found. Use 'Draft Status Request' to send initial email.")
                return
            
            # Show thread selector dialog
            thread_selector = ThreadSelectorDialog(organized_threads, case, parent=self)
            if thread_selector.exec_() != QDialog.Accepted:
                return  # User cancelled
            
            # Determine if we're starting a new thread or replying
            if thread_selector.start_new_thread:
                # Start new thread - similar to status request
                thread_id = None
                thread_messages = []
                # Convert name to title case
                name_title_case = ' '.join(word.capitalize() for word in str(case['Name']).split())
                subject = f"Follow-up: {name_title_case} DOI {case['DOI']} // Prohealth Advanced Imaging"
            else:
                # Use selected thread
                selected_thread = thread_selector.selected_thread
                if not selected_thread:
                    return
                
                thread_id = selected_thread['thread_id']
                subject = selected_thread.get('subject', '')
                
                # Get full thread messages for context
                thread_messages = selected_thread.get('messages', [])
            
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Generate follow-up email with context
            cadence_guidance = self.email_cache_service.get_cadence_guidance() if self.email_cache_service else None
            email_body = self.ai_service.generate_followup_email(case, thread_messages, cadence_guidance)
            
            QApplication.restoreOverrideCursor()
            
            # Show draft dialog
            dialog = EmailDraftDialog(case, email_body, subject=subject if not thread_id else "", thread_id=thread_id, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                email_data = dialog.get_email_data()
                
                if email_data['approved']:
                    # Send email
                    if thread_id:
                        # Reply to thread
                        msg_id = self.gmail_service.send_email(
                            email_data['recipient'],
                            None,  # No subject for replies
                            email_data['body'],
                            thread_id=email_data['thread_id']
                        )
                    else:
                        # New thread
                        msg_id = self.gmail_service.send_email(
                            email_data['recipient'],
                            email_data['subject'],
                            email_data['body']
                        )
                    
                    QMessageBox.information(self, "Success", f"Email sent! ID: {msg_id}")
                    log_sent_email(case['PV'], email_data['recipient'], 
                                 email_data.get('subject', 'Follow-up reply'), msg_id)
                    
                    # Invalidate cache
                    self.collections_tracker.invalidate_stale_case_cache()
                    
                    # Add CMS note
                    try:
                        success = asyncio.run(add_cms_note_for_email(case, "follow_up", email_data['recipient']))
                        if success:
                            self.log_activity(f"CMS note added for PV {pv}")
                    except Exception as e:
                        self.log_activity(f"CMS note failed: {str(e)}")
                    
                    self.log_activity(f"Sent follow-up for PV {pv}")
                    
                    # Update CMS card to reflect the new pending note
                    self.update_cms_card()
                    
                    # Remove from category display if sent from category widget
                    if category_widget:
                        category_widget.remove_case_from_display(pv)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to draft follow-up: {str(e)}")
    
    def draft_status_request_by_pv(self, pv, category_widget=None):
        """Draft status request email for a case"""
        try:
            case = self.case_manager.get_case_by_pv(pv)
            if not case:
                QMessageBox.warning(self, "Not Found", f"Case PV {pv} not found.")
                return
            
            with ProgressContext(self, "Generating Email", "Creating status request email...", pulse=True) as progress:
                # Generate status request
                progress.set_message("Generating email content...")
                email_body = self.ai_service.generate_status_request_email(case)
                # Convert name to title case (e.g., "John Smith" not "JOHN SMITH")
                name_title_case = ' '.join(word.capitalize() for word in str(case['Name']).split())
                subject = f"{name_title_case} DOI {case['DOI']} // Prohealth Advanced Imaging"
            
            # Show draft dialog
            dialog = EmailDraftDialog(case, email_body, subject=subject, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                email_data = dialog.get_email_data()
                
                if email_data['approved']:
                    # Send email
                    msg_id = self.gmail_service.send_email(
                        email_data['recipient'],
                        email_data['subject'],
                        email_data['body']
                    )
                    
                    QMessageBox.information(self, "Success", f"Email sent! ID: {msg_id}")
                    log_sent_email(case['PV'], email_data['recipient'], email_data['subject'], msg_id)
                    
                    # Invalidate cache
                    self.collections_tracker.invalidate_stale_case_cache()
                    
                    # Add CMS note
                    try:
                        success = asyncio.run(add_cms_note_for_email(case, "status_request", email_data['recipient']))
                        if success:
                            self.log_activity(f"CMS note added for PV {pv}")
                    except Exception as e:
                        self.log_activity(f"CMS note failed: {str(e)}")
                    
                    self.log_activity(f"Sent status request for PV {pv}")
                    
                    # Update CMS card to reflect the new pending note
                    self.update_cms_card()
                    
                    # Remove from category display if sent from category widget
                    if category_widget:
                        category_widget.remove_case_from_display(pv)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to draft status request: {str(e)}")
    
    def process_bulk_category(self, category):
        """Process bulk emails for a category"""
        if self.bulk_email_tab:
            self.tabs.setCurrentWidget(self.bulk_email_tab)
            # Set the category in bulk email widget
            if hasattr(self.bulk_email_tab, 'process_category'):
                self.bulk_email_tab.process_category(category)
            else:
                # Fallback: Set the category and populate
                self.bulk_email_tab.by_category_radio.setChecked(True)
                
                # Map category to display name
                category_map = {
                    "critical": "Critical (90+ days no response)",
                    "high_priority": "High Priority (60+ days no response)",
                    "no_response": "No Response (30+ days no response)",
                    "recently_sent": "Recently Sent (<30 days)",
                    "never_contacted": "Never Contacted",
                    "missing_doi": "Missing DOI",
                    "ccp_335_1": "CCP 335.1 (>2yr Statute Inquiry)"
                }
                
                display_name = category_map.get(category, category)
                index = self.bulk_email_tab.selection_combo.findText(display_name)
                if index >= 0:
                    self.bulk_email_tab.selection_combo.setCurrentIndex(index)
                    self.bulk_email_tab.populate_batch()
    
    # Menu actions
    def open_cases_file(self):
        """Open a cases Excel file"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Cases File", "", "Excel Files (*.xlsx *.xls)")
        
        if filepath:
            try:
                self.case_manager = CaseManager(filepath)
                self.load_all_cases()
                QMessageBox.information(self, "Success", f"Loaded {len(self.case_manager.df)} cases.")
                self.log_activity(f"Loaded cases from {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load cases: {str(e)}")
    
    def load_user_spreadsheet_path(self):
        """Load the user's saved spreadsheet path"""
        try:
            # Get current user email from Gmail service
            user_email = self.gmail_service.service.users().getProfile(userId='me').execute().get('emailAddress', 'default') if self.gmail_service else 'default'
            
            # Create user settings file path
            user_settings_dir = os.path.join('data', 'user_settings')
            os.makedirs(user_settings_dir, exist_ok=True)
            
            user_file = os.path.join(user_settings_dir, f"{user_email}_spreadsheet.json")
            
            if os.path.exists(user_file):
                with open(user_file, 'r') as f:
                    data = json.load(f)
                    return data.get('spreadsheet_path')
        except Exception as e:
            print(f"Error loading user spreadsheet path: {e}")
        return None
    
    def save_user_spreadsheet_path(self, path):
        """Save the user's spreadsheet path"""
        try:
            # Get current user email
            user_email = self.gmail_service.service.users().getProfile(userId='me').execute().get('emailAddress', 'default') if self.gmail_service else 'default'
            
            # Create user settings file
            user_settings_dir = os.path.join('data', 'user_settings')
            os.makedirs(user_settings_dir, exist_ok=True)
            
            user_file = os.path.join(user_settings_dir, f"{user_email}_spreadsheet.json")
            
            with open(user_file, 'w') as f:
                json.dump({
                    'spreadsheet_path': path,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving user spreadsheet path: {e}")
            return False
    
    def upload_spreadsheet(self):
        """Upload a new spreadsheet for the current user"""
        try:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Upload Your Spreadsheet", "", 
                "Excel Files (*.xlsx *.xls);;All Files (*.*)")
            
            if filepath:
                with ProgressContext(self, "Uploading Spreadsheet", "Processing spreadsheet...", pulse=True) as progress:
                    # Copy the file to a user-specific location
                    progress.set_message("Getting user profile...")
                    user_email = self.gmail_service.service.users().getProfile(userId='me').execute().get('emailAddress', 'default') if self.gmail_service else 'default'
                    user_dir = os.path.join('data', 'user_spreadsheets')
                    os.makedirs(user_dir, exist_ok=True)
                    
                    # Create unique filename
                    progress.set_message("Copying spreadsheet...")
                    filename = f"{user_email}_{os.path.basename(filepath)}"
                    dest_path = os.path.join(user_dir, filename)
                    
                    # Copy the file
                    shutil.copy2(filepath, dest_path)
                    
                    # Save the path
                    progress.set_message("Saving settings...")
                    self.save_user_spreadsheet_path(dest_path)
                    
                    # Reload case manager with new spreadsheet
                    progress.set_message("Loading case data...")
                    self.case_manager = CaseManager(dest_path)
                self.user_spreadsheet_path = dest_path
                
                # Reload all dependent services
                if hasattr(self, 'bulk_service'):
                    self.bulk_service.case_manager = self.case_manager
                    # Clear the categorization cache to force re-analysis
                    self.bulk_service.categorized_cases = {}
                    self.bulk_service.categorization_timestamp = None
                    self.bulk_service.force_recategorization()
                    logger.info("Cleared bulk service cache after spreadsheet upload")
                    
                if hasattr(self, 'bulk_email_tab'):
                    self.bulk_email_tab.case_manager = self.case_manager
                    # Trigger refresh of categories
                    if hasattr(self.bulk_email_tab, 'refresh_categories'):
                        QTimer.singleShot(100, self.bulk_email_tab.refresh_categories)
                    
                if hasattr(self, 'stale_widget'):
                    self.stale_widget.case_manager = self.case_manager
                    # Trigger refresh of stale cases
                    if hasattr(self.stale_widget, 'refresh_analysis'):
                        QTimer.singleShot(100, self.stale_widget.refresh_analysis)
                
                # Update collections tracker with new case data
                if hasattr(self, 'collections_tracker'):
                    # Re-analyze with new spreadsheet data
                    logger.info("Re-analyzing collections with new spreadsheet")
                    # Clear cache to force fresh analysis on next refresh
                    QTimer.singleShot(200, lambda: self.collections_tracker.clear_stale_cache())
                    
                # Refresh displays
                self.load_all_cases()
                
                QMessageBox.information(
                    self, "Success", 
                    f"Spreadsheet uploaded successfully!\n\n"
                    f"Loaded {len(self.case_manager.df)} cases from:\n{os.path.basename(filepath)}\n\n"
                    f"This spreadsheet will be used for all your sessions."
                )
                
                self.log_activity(f"Uploaded new spreadsheet: {os.path.basename(filepath)}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload spreadsheet: {str(e)}")
    
    def show_current_spreadsheet(self):
        """Show information about the current spreadsheet"""
        try:
            if self.user_spreadsheet_path:
                file_info = os.stat(self.user_spreadsheet_path)
                modified_time = datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                info_text = f"""
                <h3>Current Spreadsheet Information</h3>
                <p><b>File:</b> {os.path.basename(self.user_spreadsheet_path)}</p>
                <p><b>Total Cases:</b> {len(self.case_manager.df)}</p>
                <p><b>Active Cases:</b> {len(self.case_manager.df[self.case_manager.df[2].str.lower() == 'active'])}</p>
                <p><b>Last Modified:</b> {modified_time}</p>
                <p><b>Full Path:</b> {self.user_spreadsheet_path}</p>
                """
            else:
                info_text = """
                <h3>Using Default Spreadsheet</h3>
                <p>You are currently using the default system spreadsheet.</p>
                <p>Use <b>File → Upload Spreadsheet</b> to upload your own collector list.</p>
                """
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Current Spreadsheet")
            msg.setTextFormat(Qt.RichText)
            msg.setText(info_text)
            msg.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get spreadsheet info: {str(e)}")
    
    def refresh_email_cache(self):
        """Refresh email cache using background thread"""
        if not self.email_cache_service:
            QMessageBox.warning(self, "Service Unavailable", "Email cache service not available.")
            return
        
        try:
            # Create progress dialog
            progress = ProgressManager(self)
            progress.show_progress("Refreshing Email Cache", "Downloading recent emails...", 
                                 maximum=100, show_logs=True)
            progress.log("🔄 Starting email cache refresh")
            
            # Create and start worker thread
            self.email_worker = EmailCacheWorker(self.email_cache_service, 'refresh', 500)
            
            # Connect signals
            self.email_worker.progress_update.connect(
                lambda pct, msg: progress.update(pct, msg)
            )
            self.email_worker.log_message.connect(progress.log)
            self.email_worker.finished.connect(
                lambda result: self._on_email_refresh_complete(result, progress)
            )
            self.email_worker.error.connect(
                lambda err: self._on_email_operation_error(err, progress)
            )
            
            # Start the worker
            self.email_worker.start()
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to start refresh: {str(e)}")
    
    def bootstrap_emails(self):
        """Bootstrap all emails with download options"""
        if not self.email_cache_service:
            QMessageBox.warning(self, "Service Unavailable", "Email cache service not available.")
            return
        
        # Create custom dialog for email download options
        dialog = QDialog(self)
        dialog.setWindowTitle("Download Email History")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Add instruction label
        instruction_label = QLabel(
            "Choose how you want to download your email history:\n\n"
            "This creates a local cache for faster operations and may take 10-30 minutes."
        )
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)
        
        # Add separator
        layout.addWidget(QFrame())
        
        # Option 1: Full download
        full_radio = QRadioButton("Download entire email history")
        full_radio.setChecked(True)
        full_desc = QLabel("   Downloads ALL emails from the beginning of time")
        full_desc.setStyleSheet("color: gray; margin-left: 20px;")
        
        # Option 2: From date
        date_radio = QRadioButton("Download from specific date")
        date_desc = QLabel("   Only download emails from a selected date forward")
        date_desc.setStyleSheet("color: gray; margin-left: 20px;")
        
        # Date selector (initially disabled)
        date_layout = QHBoxLayout()
        date_label = QLabel("   Start date:")
        date_selector = QDateEdit()
        date_selector.setCalendarPopup(True)
        date_selector.setDate(QDate.currentDate().addMonths(-6))  # Default to 6 months ago
        date_selector.setDisplayFormat("yyyy-MM-dd")
        date_selector.setEnabled(False)
        date_layout.addWidget(date_label)
        date_layout.addWidget(date_selector)
        date_layout.addStretch()
        
        # Enable/disable date selector based on radio selection
        date_radio.toggled.connect(date_selector.setEnabled)
        
        # Add all widgets
        layout.addWidget(full_radio)
        layout.addWidget(full_desc)
        layout.addSpacing(10)
        layout.addWidget(date_radio)
        layout.addWidget(date_desc)
        layout.addLayout(date_layout)
        layout.addSpacing(20)
        
        # Add buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        proceed_btn = QPushButton("Download")
        proceed_btn.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(proceed_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Connect buttons
        cancel_btn.clicked.connect(dialog.reject)
        proceed_btn.clicked.connect(dialog.accept)
        
        # Show dialog and get result
        if dialog.exec_() == QDialog.Accepted:
            try:
                # Determine download mode
                from_date = None
                if date_radio.isChecked():
                    # Convert QDate to string format for Gmail API
                    selected_date = date_selector.date()
                    from_date = selected_date.toString("yyyy/MM/dd")
                
                # Create progress dialog
                progress = ProgressManager(self)
                if from_date:
                    progress.show_progress("Downloading Email History", 
                                         f"Downloading emails from {from_date} forward...", 
                                         maximum=100, show_logs=True)
                    progress.log(f"🚀 Starting email download from {from_date}")
                else:
                    progress.show_progress("Downloading Email History", 
                                         "Downloading all emails (this may take 10-30 minutes)...", 
                                         maximum=100, show_logs=True)
                    progress.log("🚀 Starting full email bootstrap")
                
                # Create and start worker thread with date parameter
                self.email_worker = EmailCacheWorker(self.email_cache_service, 'bootstrap', from_date=from_date)
                
                # Connect signals
                self.email_worker.progress_update.connect(
                    lambda pct, msg: progress.update(pct, msg)
                )
                self.email_worker.log_message.connect(progress.log)
                self.email_worker.finished.connect(
                    lambda result: self._on_bootstrap_complete(result, progress)
                )
                self.email_worker.error.connect(
                    lambda err: self._on_email_operation_error(err, progress)
                )
                
                # Start the worker
                self.email_worker.start()
                
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error", f"Bootstrap failed: {str(e)}")
    
    def _on_email_refresh_complete(self, result, progress):
        """Handle email refresh completion"""
        progress.update(100, "Email cache updated successfully!")
        progress.log("✅ Refresh complete")
        QTimer.singleShot(500, progress.close)  # Close after short delay
        QMessageBox.information(self, "Success", "Email cache refreshed!")
        self.log_activity("Refreshed email cache")
    
    def _on_bootstrap_complete(self, emails, progress):
        """Handle bootstrap completion"""
        if emails:
            progress.update(100, f"Downloaded {len(emails)} emails!")
            progress.log(f"✅ Bootstrap complete - {len(emails)} emails")
            QTimer.singleShot(500, progress.close)
            QMessageBox.information(self, "Success", f"Downloaded {len(emails)} emails!")
            self.log_activity(f"Bootstrapped {len(emails)} emails")
        else:
            progress.close()
            QMessageBox.warning(self, "No Emails", "No emails were found.")
    
    def _on_email_operation_error(self, error, progress):
        """Handle email operation errors"""
        progress.log(f"❌ Error: {error}")
        progress.close()
        QMessageBox.critical(self, "Error", f"Operation failed: {error}")
    
    def bootstrap_collections(self):
        """Bootstrap collections tracker"""
        reply = QMessageBox.question(
            self, "Analyze Email Cache",
            "This will analyze your cached emails to track case correspondence and identify patterns.\nMake sure you've downloaded email history first.\nProceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Use collections tracker
                if self.collections_tracker:
                    # Set the email cache on the tracker if not already set
                    if not hasattr(self.collections_tracker, 'email_cache'):
                        self.collections_tracker.email_cache = self.email_cache_service
                    
                    # Create progress manager
                    progress_manager = ProgressManager(self)
                    progress_manager.show_progress(
                        "Analyzing Email Cache",
                        "Preparing to analyze cached emails...",
                        show_logs=True
                    )
                    
                    # Create worker thread
                    self.collections_worker = CollectionsAnalyzerWorker(
                        self.collections_tracker,
                        self.case_manager
                    )
                    
                    # Connect signals
                    self.collections_worker.progress_update.connect(
                        lambda pct, msg: progress_manager.update(pct, msg)
                    )
                    self.collections_worker.log_message.connect(
                        lambda msg: progress_manager.log(msg)
                    )
                    self.collections_worker.finished.connect(
                        lambda success, results: self._on_collections_analysis_complete(
                            success, results, progress_manager
                        )
                    )
                    self.collections_worker.error.connect(
                        lambda err: self._on_collections_analysis_error(err, progress_manager)
                    )
                    
                    # Start analysis
                    self.collections_worker.start()
                    # Process events to keep dialog responsive
                    while self.collections_worker.isRunning():
                        QApplication.processEvents()
                        self.collections_worker.wait(100)
                    
                else:
                    # Fallback to standard bootstrap with progress context
                    with ProgressContext(self, "Analyzing Email Cache", 
                                       "Analyzing email patterns...", 
                                       pulse=True) as progress:
                        results = self.collections_tracker.bootstrap_from_gmail_direct(
                            self.gmail_service,
                            self.case_manager
                        )
                        
                        if results:
                            QMessageBox.information(
                                self, "Success",
                                f"Processed {results['processed_cases']} cases\n"
                                f"Found {results['matched_activities']} activities\n"
                                f"Tracking {results['cases_tracked']} cases"
                            )
                            self.log_activity("Bootstrapped collections from Gmail")
                
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error", f"Bootstrap failed: {str(e)}")
    
    def _on_collections_analysis_complete(self, success, results, progress_manager):
        """Handle collections analysis completion"""
        progress_manager.close()
        if success:
            QMessageBox.information(self, "Success", "Collections analysis complete!")
            self.log_activity("Completed collections analysis from cache")
            # Refresh categories view if visible
            if hasattr(self, 'categories_tab'):
                self.categories_tab.refresh_analysis()
        else:
            QMessageBox.warning(self, "Warning", "Analysis completed with warnings. Check logs for details.")
    
    def _on_collections_analysis_error(self, error, progress_manager):
        """Handle collections analysis error"""
        progress_manager.close()
        QMessageBox.critical(self, "Error", f"Analysis failed: {error}")
        self.log_activity(f"Collections analysis error: {error}")
    
    def clear_cache(self):
        """Clear category cache"""
        try:
            self.collections_tracker.clear_stale_cache()
            QMessageBox.information(self, "Success", "Cache cleared!")
            self.log_activity("Cleared category cache")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear cache: {str(e)}")
    
    def init_cms_session(self):
        """Initialize CMS session"""
        reply = QMessageBox.question(
            self, "Initialize CMS",
            "This will open a browser for CMS integration.\n"
            "You'll need to manually click 'Cancel' on the certificate popup.\n"
            "Proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from services.cms_integration import CMSIntegrationService
                QApplication.setOverrideCursor(Qt.WaitCursor)
                success = asyncio.run(CMSIntegrationService.initialize_persistent_session())
                QApplication.restoreOverrideCursor()
                
                if success:
                    QMessageBox.information(self, "Success", "CMS session initialized!")
                    self.log_activity("Initialized CMS session")
                else:
                    QMessageBox.warning(self, "Failed", "CMS session initialization failed.")
                    
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error", f"CMS initialization failed: {str(e)}")
    
    def process_cms_session_notes(self):
        """Process pending CMS session notes"""
        if not CMS_AVAILABLE:
            QMessageBox.warning(self, "CMS Not Available", 
                              "CMS integration is not available.\n"
                              "Please install playwright: pip install playwright")
            return
        
        # Get current session stats
        try:
            stats = get_session_stats()
            pending_count = stats.get('pending_count', 0)
            
            if pending_count == 0:
                QMessageBox.information(self, "No Pending Notes", 
                                       "There are no pending CMS notes to process.")
                return
            
            # Show confirmation dialog with details
            details = f"""
            Pending CMS Notes: {pending_count}
            
            Session Statistics:
            - Total Emails Sent: {stats.get('total_sent', 0)}
            - Notes Added: {stats.get('notes_added', 0)}
            - Failed: {stats.get('failed', 0)}
            
            This will:
            1. Process all pending CMS notes
            2. Clear the session log after successful processing
            
            Continue?
            """
            
            reply = QMessageBox.question(
                self, "Process CMS Session Notes",
                details,
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    with ProgressContext(self, "Processing CMS Notes", 
                                       f"Processing {pending_count} CMS notes...", 
                                       maximum=pending_count) as progress:
                        
                        # Process the session notes directly (it's not an async generator)
                        async def process_with_progress():
                            # Update progress periodically while processing
                            progress.update(0, f"Processing {pending_count} CMS notes...")
                            result = await process_session_cms_notes()
                            progress.update(pending_count, f"Completed processing {pending_count} notes")
                            return result
                        
                        # Run the async function
                        results = asyncio.run(process_with_progress())
                    
                    if results:
                        # Get updated stats after processing
                        updated_stats = get_session_stats()
                        
                        success_msg = f"""
                        CMS Notes Processing Complete!
                        
                        Results:
                        - Notes Added: {updated_stats.get('processed_count', 0)}
                        - Still Pending: {updated_stats.get('pending_count', 0)}
                        - Total Processed: {updated_stats.get('notes_added_count', 0)}
                        """
                        
                        QMessageBox.information(self, "Success", success_msg)
                        self.log_activity(f"Processed {pending_count} CMS notes")
                        
                        # Update quick stats and CMS card
                        self.update_quick_stats()
                        self.update_cms_card()
                    else:
                        QMessageBox.warning(self, "Processing Failed", 
                                          "Failed to process CMS notes. Check the logs for details.")
                        
                except Exception as e:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.critical(self, "Error", 
                                       f"Error processing CMS notes: {str(e)}\n\n"
                                       "Make sure CMS session is initialized first.")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get session stats: {str(e)}")
    
    def browse_credentials(self):
        """Browse for credentials file"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Credentials File", "", "JSON Files (*.json)")
        
        if filepath:
            self.gmail_creds_path.setText(filepath)
    
    def refresh_current_tab(self):
        """Refresh the current tab"""
        current_widget = self.tabs.currentWidget()
        
        if current_widget == self.dashboard_tab:
            self.update_quick_stats()
            self.update_cms_card()
            self.log_activity("Refreshed dashboard")
        elif current_widget == self.categories_tab:
            self.categories_tab.refresh_analysis()
        elif current_widget == self.collections_tab:
            self.refresh_collections_dashboard()
        else:
            self.log_activity("Refreshed current tab")
    
    def quick_search(self):
        """Quick search dialog"""
        text, ok = QInputDialog.getText(self, "Quick Search", "Enter PV# or Name:")
        if ok and text:
            self.tabs.setCurrentIndex(1)  # Switch to Cases tab
            self.case_search_input.setText(text)
            self.search_cases()
    
    def quick_compose(self):
        """Quick compose email"""
        self.tabs.setCurrentIndex(2)  # Switch to Email tab
    
    def quick_summarize(self):
        """Quick summarize case"""
        text, ok = QInputDialog.getText(self, "Summarize Case", "Enter PV#:")
        if ok and text:
            self.summarize_case_by_pv(text)
    
    def quick_followup(self):
        """Quick draft follow-up"""
        text, ok = QInputDialog.getText(self, "Draft Follow-up", "Enter PV#:")
        if ok and text:
            self.draft_followup_by_pv(text)
    
    def on_cadence_profile_changed(self):
        """Handle cadence profile selection change"""
        if not self.email_cache_service:
            return
        
        if self.personal_cadence_radio.isChecked():
            self.email_cache_service.set_cadence_profile('personal')
            self.log_activity("Switched to personal email cadence profile")
        else:
            self.email_cache_service.set_cadence_profile('default')
            self.log_activity("Switched to default professional cadence profile")
    
    def show_cadence_details(self):
        """Show detailed view of the active cadence profile"""
        if not self.email_cache_service:
            QMessageBox.warning(self, "Not Available", "Email cache service is not available.")
            return
        
        # Get the active cadence data
        profile_name = self.email_cache_service.get_cadence_profile_name()
        cadence_data = self.email_cache_service.get_active_cadence()
        
        if not cadence_data:
            QMessageBox.information(self, "No Cadence Data", 
                                   f"No cadence data available for {profile_name} profile.\n"
                                   "Please download email history first.")
            return
        
        # Create dialog to show cadence details
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Cadence Profile Details - {profile_name.title()}")
        dialog.setModal(True)
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        # Create text browser for details
        details_browser = QTextBrowser()
        details_browser.setOpenExternalLinks(False)
        
        # Format the cadence data
        html_content = f"""
        <h2>{'Personal' if profile_name == 'personal' else 'Default Professional'} Cadence Profile</h2>
        
        <h3>Analysis Summary</h3>
        <ul>
            <li><b>Total emails analyzed:</b> {cadence_data.get('total_emails_analyzed', 'N/A')}</li>
            <li><b>Average frequency:</b> {cadence_data.get('average_frequency_days', 'N/A')} days</li>
        </ul>
        
        <h3>Writing Style</h3>
        <ul>
        """
        
        style = cadence_data.get('style_patterns', {})
        for key, value in style.items():
            formatted_key = key.replace('_', ' ').title()
            html_content += f"<li><b>{formatted_key}:</b> {value}{'%' if isinstance(value, (int, float)) and key != 'average_length' else ''}</li>"
        
        html_content += """
        </ul>
        
        <h3>Tone Indicators</h3>
        <ul>
        """
        
        tone = cadence_data.get('tone_indicators', {})
        for key, value in tone.items():
            formatted_key = key.replace('_', ' ').title()
            html_content += f"<li><b>{formatted_key}:</b> {value}%</li>"
        
        html_content += """
        </ul>
        
        <h3>Common Subject Words</h3>
        <p>
        """
        
        subject_words = cadence_data.get('common_subject_words', [])[:10]
        html_content += ", ".join(subject_words) if subject_words else "No data available"
        
        html_content += """
        </p>
        
        <h3>Sample Greetings</h3>
        <ul>
        """
        
        greetings = cadence_data.get('greeting_patterns', [])[:3]
        for greeting in greetings:
            html_content += f"<li>{greeting}</li>"
        
        if not greetings:
            html_content += "<li>No greeting patterns available</li>"
        
        html_content += """
        </ul>
        
        <h3>Sample Closings</h3>
        <ul>
        """
        
        closings = cadence_data.get('closing_patterns', [])[:3]
        for closing in closings:
            html_content += f"<li>{closing[:100]}...</li>" if len(closing) > 100 else f"<li>{closing}</li>"
        
        if not closings:
            html_content += "<li>No closing patterns available</li>"
        
        html_content += "</ul>"
        
        details_browser.setHtml(html_content)
        layout.addWidget(details_browser)
        
        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About",
            "Prohealth AI Assistant - Enhanced Edition\n\n"
            "Medical Lien Case Management System\n"
            "Version 2.0.0\n\n"
            "Features:\n"
            "• Comprehensive case management\n"
            "• AI-powered email analysis\n"
            "• Case organization by categories\n"
            "• Bulk email processing\n"
            "• Collections dashboard\n"
            "• Dark mode support\n\n"
            "Powered by OpenAI GPT-4 and Gmail API"
        )
    
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("openai_key", self.openai_key_input.text())
        self.settings.setValue("gmail_creds", self.gmail_creds_path.text())
        self.settings.setValue("theme", self.theme_combo.currentText())
        self.settings.setValue("font_size", self.font_size_spin.value())
        self.settings.setValue("auto_refresh", self.auto_refresh_check.isChecked())
        self.settings.setValue("refresh_interval", self.refresh_interval_spin.value())
        self.settings.setValue("auto_cms", self.auto_cms_check.isChecked())
        self.settings.setValue("dark_mode", self.dark_mode)
        
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        self.log_activity("Saved settings")
    
    def load_settings(self):
        """Load application settings"""
        self.openai_key_input.setText(self.settings.value("openai_key", ""))
        self.gmail_creds_path.setText(self.settings.value("gmail_creds", ""))
        
        theme = self.settings.value("theme", "Light")
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        self.font_size_spin.setValue(self.settings.value("font_size", 10, type=int))
        self.auto_refresh_check.setChecked(self.settings.value("auto_refresh", False, type=bool))
        self.refresh_interval_spin.setValue(self.settings.value("refresh_interval", 5, type=int))
        self.auto_cms_check.setChecked(self.settings.value("auto_cms", False, type=bool))
        self.dark_mode = self.settings.value("dark_mode", False, type=bool)
        
        # Apply loaded dark mode setting
        if self.dark_mode:
            self.dark_mode_action.setChecked(True)
            self.dark_mode_btn.setChecked(True)
    
    def log_activity(self, message):
        """Log activity to the activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Check if log_widget exists before using it
        if hasattr(self, 'log_widget'):
            self.log_widget.append(f"[{timestamp}] {message}")
            
            # Auto-scroll log to bottom
            cursor = self.log_widget.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_widget.setTextCursor(cursor)
        
        # Also add to activity list in dashboard
        if hasattr(self, 'activity_list'):
            self.activity_list.insertItem(0, f"[{timestamp}] {message}")
            # Keep only last 20 items
            while self.activity_list.count() > 20:
                self.activity_list.takeItem(20)


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Prohealth AI Assistant Enhanced")
    app.setOrganizationName("Prohealth")
    
    # Set application style
    app.setStyle("Fusion")
    
    window = EnhancedMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()