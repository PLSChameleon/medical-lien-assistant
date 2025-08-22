#!/usr/bin/env python3
"""Check CMS session status and pending emails"""

import sys
import os
import re
from datetime import datetime

# Add ai_assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

from services.cms_integration import get_session_stats, load_pending_emails

def show_detailed_status():
    """Show detailed status of CMS integration"""
    
    print("=" * 60)
    print("CMS INTEGRATION STATUS")
    print("=" * 60)
    
    # Get stats
    stats = get_session_stats()
    pending_emails = load_pending_emails()
    
    # Show summary
    print(f"\nSUMMARY:")
    print(f"   Total emails sent: {stats['total_emails']}")
    print(f"   Pending CMS notes: {stats['pending_count']}")
    print(f"   Processed emails: {stats['processed_count']}")
    print(f"   Total CMS notes added: {stats['notes_added_count']}")
    
    # Show pending emails if any
    if pending_emails:
        print(f"\nPENDING EMAILS ({len(pending_emails)}):")
        for pid, email_info in list(pending_emails.items())[:10]:
            print(f"   - PID {pid} -> {email_info['email']} ({email_info['email_type']})")
        if len(pending_emails) > 10:
            print(f"   ... and {len(pending_emails) - 10} more")
        
        print("\nTO PROCESS PENDING EMAILS:")
        print("   Run: python process_cms_notes.py")
    else:
        print("\n[OK] No pending emails - all caught up!")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    show_detailed_status()