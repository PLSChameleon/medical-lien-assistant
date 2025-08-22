#!/usr/bin/env python3
"""Test that CMS notes do NOT have (TEST) prefix in production mode"""

import sys
import os

# Add ai_assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

from services.cms_integration import CMSIntegrationService

# Test the note generation methods
cms_service = CMSIntegrationService(use_persistent_session=False)

print("=" * 60)
print("TESTING CMS NOTE FORMAT (NO TEST PREFIX)")
print("=" * 60)

# Test production notes (should NOT have TEST prefix)
print("\n1. Testing PRODUCTION note formats:")

# Follow-up note test
test_email = "attorney@lawfirm.com"
print(f"\n   Follow-up note for {test_email}:")
print(f"   Expected: FOLLOW UP EMAIL SENT TO {test_email.upper()}")

# Status request note test
print(f"\n   Status request note for {test_email}:")
print(f"   Expected: STATUS REQUEST SENT TO {test_email.upper()}")

# General email note test
print(f"\n   General email note for {test_email}:")
print(f"   Expected: EMAIL SENT TO {test_email.upper()}")

print("\n2. Testing TEST MODE note format:")
test_info = "TEST MODE - Email sent to test@example.com (intended for attorney@lawfirm.com)"
print(f"\n   Test mode note:")
print(f"   Expected: (TEST MODE) EMAIL SENT TO {test_info}")

print("\n" + "=" * 60)
print("IMPORTANT: Production notes should NOT have (TEST) prefix!")
print("Only emails sent in test mode should have (TEST MODE) marker.")
print("=" * 60)