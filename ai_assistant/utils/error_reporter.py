"""
Automatic Error Reporting via Email
Sends error reports to administrator automatically
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import logging

class ErrorReporter:
    """Automatically report errors to administrator"""
    
    def __init__(self, admin_email: str, gmail_service=None):
        """
        Initialize error reporter
        
        Args:
            admin_email: Email address to send error reports to
            gmail_service: GmailService instance for sending emails
        """
        self.admin_email = admin_email
        self.gmail_service = gmail_service
        self.settings_file = os.path.join('data', 'error_reporting_settings.json')
        self.load_settings()
    
    def load_settings(self):
        """Load error reporting settings"""
        self.settings = {
            'enabled': True,
            'auto_send': True,
            'severity_threshold': 'ERROR',  # Only send ERROR and CRITICAL
            'batch_errors': True,  # Batch multiple errors before sending
            'batch_interval': 300,  # 5 minutes
            'include_screenshot': False,
            'admin_emails': [self.admin_email]
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
            except:
                pass
    
    def save_settings(self):
        """Save error reporting settings"""
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def should_report(self, severity: str) -> bool:
        """Check if error should be reported based on severity"""
        if not self.settings['enabled'] or not self.settings['auto_send']:
            return False
        
        severity_levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        
        threshold = severity_levels.get(self.settings['severity_threshold'], 3)
        current = severity_levels.get(severity, 3)
        
        return current >= threshold
    
    def send_error_report(self, error_data: dict, immediate: bool = False):
        """
        Send error report to administrator
        
        Args:
            error_data: Error information dictionary
            immediate: Send immediately regardless of batching settings
        """
        if not self.should_report(error_data.get('severity', 'ERROR')):
            return False
        
        try:
            if self.gmail_service:
                # Use Gmail API
                self.send_via_gmail(error_data)
            else:
                # Fallback to saving locally
                self.save_for_manual_send(error_data)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to send error report: {e}")
            self.save_for_manual_send(error_data)
            return False
    
    def send_via_gmail(self, error_data: dict):
        """Send error report using Gmail API"""
        try:
            # Create email
            subject = f"[Error Report] {error_data.get('user', 'Unknown')} - {error_data.get('error_type', 'Unknown Error')}"
            
            # Format body
            body = self.format_error_email(error_data)
            
            # Create message
            message = MIMEMultipart()
            message['to'] = ', '.join(self.settings['admin_emails'])
            message['subject'] = subject
            message.attach(MIMEText(body, 'html'))
            
            # Attach detailed JSON data
            attachment = MIMEBase('application', 'json')
            attachment.set_payload(json.dumps(error_data, indent=2, default=str))
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="error_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            )
            message.attach(attachment)
            
            # Send via Gmail API
            self.gmail_service.send_message(message)
            
            logging.info(f"Error report sent to {self.admin_email}")
            
        except Exception as e:
            logging.error(f"Failed to send via Gmail: {e}")
            raise
    
    def format_error_email(self, error_data: dict) -> str:
        """Format error data as HTML email"""
        timestamp = error_data.get('timestamp', 'Unknown')
        user = error_data.get('user', 'Unknown')
        error_type = error_data.get('error_type', 'Unknown')
        error_msg = error_data.get('error_message', 'No message')
        context = error_data.get('context', 'No context')
        
        location = error_data.get('location', {})
        file = location.get('file', 'Unknown')
        line = location.get('line', '?')
        function = location.get('function', 'Unknown')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">Error Report</h2>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Error Summary</h3>
                <table style="width: 100%;">
                    <tr><td><b>Time:</b></td><td>{timestamp}</td></tr>
                    <tr><td><b>User:</b></td><td>{user}</td></tr>
                    <tr><td><b>Error Type:</b></td><td style="color: #d32f2f;"><b>{error_type}</b></td></tr>
                    <tr><td><b>Message:</b></td><td>{error_msg}</td></tr>
                    <tr><td><b>Context:</b></td><td>{context}</td></tr>
                </table>
            </div>
            
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Location</h3>
                <table style="width: 100%;">
                    <tr><td><b>File:</b></td><td>{file}</td></tr>
                    <tr><td><b>Line:</b></td><td>{line}</td></tr>
                    <tr><td><b>Function:</b></td><td>{function}</td></tr>
                </table>
            </div>
            
            <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>System Info</h3>
                <p>See attached JSON file for complete system information and stack trace.</p>
            </div>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                This error report was automatically generated by the Medical Lien Assistant.<br>
                Full details are in the attached JSON file.
            </p>
        </body>
        </html>
        """
        
        return html
    
    def save_for_manual_send(self, error_data: dict):
        """Save error report for manual sending later"""
        try:
            # Create pending reports directory
            pending_dir = os.path.join('data', 'pending_error_reports')
            os.makedirs(pending_dir, exist_ok=True)
            
            # Save with timestamp
            filename = f"error_{error_data.get('user', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(pending_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(error_data, f, indent=2, default=str)
            
            logging.info(f"Error report saved for manual send: {filepath}")
            
        except Exception as e:
            logging.error(f"Failed to save error report: {e}")
    
    def send_pending_reports(self):
        """Send all pending error reports"""
        pending_dir = os.path.join('data', 'pending_error_reports')
        if not os.path.exists(pending_dir):
            return
        
        sent_count = 0
        failed_count = 0
        
        for filename in os.listdir(pending_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(pending_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        error_data = json.load(f)
                    
                    if self.send_error_report(error_data, immediate=True):
                        # Delete sent report
                        os.remove(filepath)
                        sent_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logging.error(f"Failed to send pending report {filename}: {e}")
                    failed_count += 1
        
        return sent_count, failed_count
    
    def configure_auto_reporting(self, enabled: bool = True, 
                                admin_emails: list = None,
                                severity_threshold: str = 'ERROR'):
        """
        Configure automatic error reporting
        
        Args:
            enabled: Whether to enable auto-reporting
            admin_emails: List of admin emails to send to
            severity_threshold: Minimum severity to report
        """
        self.settings['enabled'] = enabled
        self.settings['auto_send'] = enabled
        
        if admin_emails:
            self.settings['admin_emails'] = admin_emails
        
        self.settings['severity_threshold'] = severity_threshold
        
        self.save_settings()
        
        return self.settings

# Global error reporter instance
_error_reporter = None

def initialize_error_reporter(admin_email: str, gmail_service=None):
    """Initialize the global error reporter"""
    global _error_reporter
    _error_reporter = ErrorReporter(admin_email, gmail_service)
    return _error_reporter

def get_error_reporter():
    """Get the global error reporter instance"""
    return _error_reporter

def report_error(error_data: dict, immediate: bool = False):
    """Report an error to administrator"""
    if _error_reporter:
        return _error_reporter.send_error_report(error_data, immediate)
    return False