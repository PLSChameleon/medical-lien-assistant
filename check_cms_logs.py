#!/usr/bin/env python3
"""Diagnostic script to check CMS log files and counts"""

import os
import sys

# Add ai_assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

from services.cms_integration import (
    get_session_stats,
    load_pending_emails,
    SESSION_EMAILS_PENDING_LOG,
    SESSION_EMAILS_PROCESSED_LOG,
    SESSION_CMS_NOTES_LOG
)

print("=" * 60)
print("CMS LOGS DIAGNOSTIC")
print("=" * 60)

# Check if log files exist
print("\n1. LOG FILES:")
for log_file, name in [
    (SESSION_EMAILS_PENDING_LOG, "Pending"),
    (SESSION_EMAILS_PROCESSED_LOG, "Processed"),
    (SESSION_CMS_NOTES_LOG, "CMS Notes")
]:
    if os.path.exists(log_file):
        size = os.path.getsize(log_file)
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"   {name}: {log_file}")
        print(f"      - Size: {size} bytes")
        print(f"      - Lines: {len(lines)}")
        if lines and name == "Pending":
            print(f"      - Sample: {lines[0].strip()[:100]}...")
    else:
        print(f"   {name}: NOT FOUND")

# Get stats
print("\n2. STATS FROM get_session_stats():")
stats = get_session_stats()
for key, value in stats.items():
    print(f"   {key}: {value}")

# Load pending emails
print("\n3. PENDING EMAILS FROM load_pending_emails():")
pending = load_pending_emails()
print(f"   Count: {len(pending)}")
if pending:
    for pid, info in list(pending.items())[:3]:
        print(f"   - PID {pid}: {info['email']} ({info['email_type']})")
    if len(pending) > 3:
        print(f"   ... and {len(pending) - 3} more")

print("\n" + "=" * 60)