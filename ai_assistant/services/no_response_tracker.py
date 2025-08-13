#!/usr/bin/env python3
"""
No Response Tracker - Identifies files where emails were sent but no replies received
"""

import json
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

class NoResponseTracker:
    """Tracks files where emails were sent but no replies received"""
    
    def __init__(self):
        self.email_history_file = "email_thread_history.json"
        self.sent_emails_log = "sent_emails.log"
        self.no_response_log = "no_response_files.log"
        
    def load_email_history(self):
        """Load email thread history"""
        try:
            if os.path.exists(self.email_history_file):
                with open(self.email_history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading email history: {e}")
            return []
    
    def load_sent_emails(self):
        """Load sent emails from log"""
        sent_emails = []
        if os.path.exists(self.sent_emails_log):
            try:
                with open(self.sent_emails_log, "r", encoding="utf-8") as f:
                    for line in f:
                        if "PV:" in line:
                            sent_emails.append(line.strip())
            except Exception as e:
                logger.error(f"Error loading sent emails: {e}")
        return sent_emails
    
    def analyze_response_patterns(self, case_manager):
        """Analyze which files have emails sent but no responses"""
        logger.info("🔍 Analyzing email response patterns...")
        
        email_threads = self.load_email_history()
        sent_emails = self.load_sent_emails()
        
        # Track outbound vs inbound emails per case
        case_email_stats = defaultdict(lambda: {
            'outbound': 0, 
            'inbound': 0,
            'last_outbound': None,
            'last_inbound': None,
            'recipient_emails': set(),
            'case_info': None
        })
        
        # Analyze email threads for responses
        for thread in email_threads:
            messages = thread.get("messages", [])
            for msg in messages:
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                from_email = headers.get("from", "")
                to_email = headers.get("to", "")
                subject = headers.get("subject", "")
                date = headers.get("date", "")
                
                # Try to extract case information from subject/content
                case_id = self.extract_case_id(subject, msg.get("snippet", ""))
                if case_id:
                    stats = case_email_stats[case_id]
                    
                    # Determine if outbound (from us) or inbound (to us)
                    if self.is_outbound_email(from_email):
                        stats['outbound'] += 1
                        stats['last_outbound'] = date
                        if to_email:
                            stats['recipient_emails'].add(to_email)
                    else:
                        stats['inbound'] += 1 
                        stats['last_inbound'] = date
        
        # Also analyze sent emails log
        for sent_line in sent_emails:
            case_id = self.extract_case_id_from_log(sent_line)
            if case_id:
                case_email_stats[case_id]['outbound'] += 1
                # Extract recipient email
                recipient = self.extract_recipient_from_log(sent_line)
                if recipient:
                    case_email_stats[case_id]['recipient_emails'].add(recipient)
        
        # Identify no-response files
        no_response_files = []
        for case_id, stats in case_email_stats.items():
            if stats['outbound'] > 0 and stats['inbound'] == 0:
                # Get case details
                case_info = case_manager.get_case_by_pv(case_id)
                if case_info:
                    no_response_data = {
                        'case_id': case_id,
                        'case_info': case_info,
                        'emails_sent': stats['outbound'],
                        'emails_received': stats['inbound'],
                        'recipient_emails': list(stats['recipient_emails']),
                        'last_outbound': stats['last_outbound'],
                        'days_since_last_email': self.calculate_days_since(stats['last_outbound'])
                    }
                    no_response_files.append(no_response_data)
        
        logger.info(f"📊 Found {len(no_response_files)} files with no responses")
        return no_response_files
    
    def extract_case_id(self, subject, snippet):
        """Extract case ID (PV number) from email subject or content"""
        text = f"{subject} {snippet}"
        
        # Look for PV patterns
        pv_patterns = [
            r'PV[:\s]*(\d+)',
            r'Case[:\s]*(\d+)', 
            r'File[:\s]*(\d+)',
            r'Patient[:\s]*(\d+)',
            r'\b(\d{6})\b'  # 6-digit numbers
        ]
        
        for pattern in pv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_case_id_from_log(self, log_line):
        """Extract case ID from sent email log line"""
        match = re.search(r'PV[:\s]*(\d+)', log_line, re.IGNORECASE)
        return match.group(1) if match else None
    
    def extract_recipient_from_log(self, log_line):
        """Extract recipient email from sent email log line"""
        match = re.search(r'To[:\s]*([^\s|]+@[^\s|]+)', log_line, re.IGNORECASE)
        return match.group(1) if match else None
    
    def is_outbound_email(self, from_email):
        """Determine if email is outbound (sent by us)"""
        # Add your email patterns here
        our_domains = ['@gmail.com']  # Update with your actual domains
        return any(domain in from_email.lower() for domain in our_domains)
    
    def calculate_days_since(self, date_str):
        """Calculate days since given date"""
        if not date_str:
            return None
        try:
            # Parse email date (this may need adjustment based on date format)
            email_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return (datetime.now() - email_date).days
        except:
            return None
    
    def save_no_response_files(self, no_response_files):
        """Save no response files to log"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.no_response_log, "w", encoding="utf-8") as f:
                f.write(f"# No Response Files Analysis - {timestamp}\n")
                f.write(f"# Files where emails were sent but no replies received\n\n")
                
                for file_data in no_response_files:
                    case_info = file_data['case_info']
                    f.write(f"PV: {file_data['case_id']} | ")
                    f.write(f"Name: {case_info.get('Name', 'Unknown')} | ")
                    f.write(f"Attorney: {case_info.get('Law Firm', 'Unknown')} | ")
                    f.write(f"Emails Sent: {file_data['emails_sent']} | ")
                    f.write(f"Responses: {file_data['emails_received']} | ")
                    f.write(f"Recipients: {', '.join(file_data['recipient_emails'])}")
                    if file_data['days_since_last_email']:
                        f.write(f" | Days Since Last Email: {file_data['days_since_last_email']}")
                    f.write("\n")
            
            logger.info(f"💾 No response files saved to {self.no_response_log}")
            
        except Exception as e:
            logger.error(f"Error saving no response files: {e}")
    
    def get_no_response_summary(self, no_response_files):
        """Get summary statistics for no response files"""
        if not no_response_files:
            return {
                'total_files': 0,
                'total_emails_sent': 0,
                'avg_emails_per_file': 0,
                'oldest_file_days': 0
            }
        
        total_emails = sum(f['emails_sent'] for f in no_response_files)
        days_list = [f['days_since_last_email'] for f in no_response_files if f['days_since_last_email']]
        
        return {
            'total_files': len(no_response_files),
            'total_emails_sent': total_emails,
            'avg_emails_per_file': round(total_emails / len(no_response_files), 1),
            'oldest_file_days': max(days_list) if days_list else 0
        }

def analyze_no_response_files(case_manager):
    """Main function to analyze and report no response files"""
    tracker = NoResponseTracker()
    
    logger.info("🔄 Starting no response analysis...")
    no_response_files = tracker.analyze_response_patterns(case_manager)
    
    if no_response_files:
        tracker.save_no_response_files(no_response_files)
        summary = tracker.get_no_response_summary(no_response_files)
        
        logger.info("📊 NO RESPONSE FILES SUMMARY:")
        logger.info(f"   📁 Total files: {summary['total_files']}")
        logger.info(f"   📧 Total emails sent: {summary['total_emails_sent']}")
        logger.info(f"   📈 Average emails per file: {summary['avg_emails_per_file']}")
        logger.info(f"   📅 Oldest file (days): {summary['oldest_file_days']}")
        
        return no_response_files
    else:
        logger.info("✅ No files found with unreturned emails")
        return []