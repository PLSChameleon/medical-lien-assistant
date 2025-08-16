"""
Enhanced Error Tracking and Logging System
Captures detailed error information for debugging and support
"""

import os
import sys
import json
import logging
import traceback
import platform
from datetime import datetime
from typing import Any, Dict, Optional
import socket

class ErrorTracker:
    """Centralized error tracking and reporting system"""
    
    def __init__(self, user_email: str = "unknown"):
        self.user_email = user_email
        self.error_log_dir = os.path.join("logs", "errors")
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create error log directory
        os.makedirs(self.error_log_dir, exist_ok=True)
        
        # Set up error log file
        self.error_log_file = os.path.join(
            self.error_log_dir,
            f"errors_{self.user_email.replace('@', '_')}_{datetime.now().strftime('%Y%m%d')}.json"
        )
        
        # Initialize error list
        self.errors = self.load_existing_errors()
        
        # System info
        self.system_info = self.get_system_info()
    
    def load_existing_errors(self) -> list:
        """Load existing errors from today's log file"""
        if os.path.exists(self.error_log_file):
            try:
                with open(self.error_log_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def get_system_info(self) -> Dict:
        """Collect system information for debugging"""
        try:
            import pandas as pd
            pandas_version = pd.__version__
        except:
            pandas_version = "unknown"
            
        try:
            from PyQt5.QtCore import QT_VERSION_STR
            qt_version = QT_VERSION_STR
        except:
            qt_version = "unknown"
        
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "pandas_version": pandas_version,
            "qt_version": qt_version,
            "working_directory": os.getcwd()
        }
    
    def capture_error(self, 
                     error: Exception,
                     context: str = "",
                     additional_info: Dict = None,
                     severity: str = "ERROR") -> Dict:
        """
        Capture detailed error information
        
        Args:
            error: The exception that occurred
            context: Description of what was happening when error occurred
            additional_info: Any additional debugging information
            severity: ERROR, WARNING, CRITICAL
        
        Returns:
            Error report dictionary
        """
        # Get full traceback
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        traceback_str = ''.join(tb_lines)
        
        # Get the specific line that caused the error
        tb = traceback.extract_tb(error.__traceback__)
        if tb:
            last_frame = tb[-1]
            error_location = {
                "file": last_frame.filename,
                "line": last_frame.lineno,
                "function": last_frame.name,
                "code": last_frame.line
            }
        else:
            error_location = {}
        
        # Create error report
        error_report = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "user": self.user_email,
            "severity": severity,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "location": error_location,
            "traceback": traceback_str,
            "additional_info": additional_info or {},
            "system_info": self.system_info
        }
        
        # Add to errors list
        self.errors.append(error_report)
        
        # Save to file
        self.save_errors()
        
        # Also log to standard logger
        logging.error(f"[{severity}] {context}: {error}")
        logging.debug(f"Traceback: {traceback_str}")
        
        return error_report
    
    def save_errors(self):
        """Save errors to JSON file"""
        try:
            with open(self.error_log_file, 'w') as f:
                json.dump(self.errors, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Failed to save error log: {e}")
    
    def create_error_report(self, include_system: bool = True) -> str:
        """
        Create a shareable error report
        
        Args:
            include_system: Whether to include system information
        
        Returns:
            Formatted error report string
        """
        report = []
        report.append("=" * 60)
        report.append("ERROR REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"User: {self.user_email}")
        report.append(f"Session: {self.session_id}")
        report.append("=" * 60)
        
        if include_system:
            report.append("\nSYSTEM INFORMATION:")
            report.append("-" * 40)
            for key, value in self.system_info.items():
                if key == "python_version":
                    value = value.split('\n')[0]  # Just first line
                report.append(f"{key}: {value}")
        
        # Get today's errors
        today_errors = [e for e in self.errors 
                       if e['timestamp'].startswith(datetime.now().strftime('%Y-%m-%d'))]
        
        if today_errors:
            report.append("\nERRORS TODAY:")
            report.append("-" * 40)
            
            for i, error in enumerate(today_errors[-10:], 1):  # Last 10 errors
                report.append(f"\nError #{i}:")
                report.append(f"Time: {error['timestamp']}")
                report.append(f"Type: {error['error_type']}")
                report.append(f"Message: {error['error_message']}")
                report.append(f"Context: {error['context']}")
                
                if error.get('location'):
                    loc = error['location']
                    report.append(f"Location: {loc.get('file', 'unknown')}:{loc.get('line', '?')}")
                    report.append(f"Function: {loc.get('function', 'unknown')}")
                
                report.append("-" * 20)
        else:
            report.append("\nNo errors recorded today.")
        
        report.append("\n" + "=" * 60)
        report.append("END OF REPORT")
        report.append("=" * 60)
        
        return '\n'.join(report)
    
    def export_for_support(self, output_file: str = None) -> str:
        """
        Export detailed error information for support
        
        Args:
            output_file: Optional output file path
        
        Returns:
            Path to the exported file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(
                self.error_log_dir,
                f"error_report_{self.user_email.replace('@', '_')}_{timestamp}.txt"
            )
        
        # Create detailed report
        report = self.create_error_report(include_system=True)
        
        # Add recent error details
        report += "\n\n" + "=" * 60
        report += "\nDETAILED ERROR INFORMATION (Last 5 Errors):"
        report += "\n" + "=" * 60
        
        recent_errors = self.errors[-5:] if len(self.errors) > 5 else self.errors
        
        for error in recent_errors:
            report += f"\n\n--- Error at {error['timestamp']} ---\n"
            report += f"Traceback:\n{error.get('traceback', 'Not available')}\n"
            
            if error.get('additional_info'):
                report += f"\nAdditional Info:\n"
                for key, value in error['additional_info'].items():
                    report += f"  {key}: {value}\n"
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return output_file
    
    def get_error_summary(self) -> Dict:
        """Get summary statistics of errors"""
        today = datetime.now().strftime('%Y-%m-%d')
        today_errors = [e for e in self.errors if e['timestamp'].startswith(today)]
        
        error_types = {}
        for error in today_errors:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors_today": len(today_errors),
            "total_errors_session": len([e for e in self.errors 
                                        if e['session_id'] == self.session_id]),
            "error_types": error_types,
            "last_error": today_errors[-1] if today_errors else None
        }
    
    def clear_old_logs(self, days_to_keep: int = 7):
        """Clean up old error logs"""
        import glob
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in glob.glob(os.path.join(self.error_log_dir, "*.json")):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                if file_time < cutoff_date:
                    os.remove(log_file)
                    logging.info(f"Removed old log file: {log_file}")
            except Exception as e:
                logging.warning(f"Could not remove old log: {e}")

# Global error tracker instance
_error_tracker = None

def initialize_error_tracker(user_email: str = "unknown"):
    """Initialize the global error tracker"""
    global _error_tracker
    _error_tracker = ErrorTracker(user_email)
    return _error_tracker

def get_error_tracker() -> Optional[ErrorTracker]:
    """Get the global error tracker instance"""
    return _error_tracker

def track_error(error: Exception, context: str = "", **kwargs):
    """Convenience function to track an error"""
    if _error_tracker:
        return _error_tracker.capture_error(error, context, kwargs)
    else:
        # Fallback to basic logging
        logging.error(f"{context}: {error}")
        return None