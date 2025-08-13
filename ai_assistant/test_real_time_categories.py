#!/usr/bin/env python3
"""
Test script to verify real-time case category updates after email sends
"""

import os
import sys
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.collections_tracker import CollectionsTracker, parse_sent_emails_log
from case_manager import CaseManager
from utils.logging_config import log_sent_email

def test_real_time_category_updates():
    """Test that sent emails immediately update case categories"""
    
    print("Testing Real-Time Case Category Updates")
    print("=" * 50)
    
    # Load case manager and collections tracker
    case_manager = CaseManager("data/cases.xlsx")
    tracker = CollectionsTracker()
    
    # Get initial stale case analysis
    print("1. Getting initial stale case analysis...")
    initial_categories = tracker.get_comprehensive_stale_cases(case_manager)
    
    print("\nInitial Categories:")
    for category, cases in initial_categories.items():
        print(f"  {category}: {len(cases)} cases")
    
    # Check if any critical cases exist for testing
    if not initial_categories['critical']:
        print("\n⚠️ No critical cases found for testing")
        return
    
    # Pick a critical case for testing
    test_case_pv = initial_categories['critical'][0]['pv']
    test_case = None
    for case in initial_categories['critical']:
        if case['pv'] == test_case_pv:
            test_case = case
            break
    
    print(f"\n2. Testing with case PV {test_case_pv}:")
    print(f"   Current status: CRITICAL ({test_case['days_since_contact']} days since contact)")
    
    # Test sent emails parsing
    print("\n3. Testing sent emails log parsing...")
    sent_emails = parse_sent_emails_log()
    if test_case_pv in sent_emails:
        print(f"   [OK] Found recent sent email: {sent_emails[test_case_pv]['line']}")
    else:
        print(f"   [INFO] No recent sent email found for PV {test_case_pv}")
    
    # Simulate sending an email by adding to log
    print(f"\n4. Simulating email send for PV {test_case_pv}...")
    log_sent_email(test_case_pv, "test@example.com", "Test Follow-up", "TEST_MSG_ID")
    
    # Invalidate cache and get fresh analysis
    print("5. Invalidating cache and getting fresh analysis...")
    tracker.invalidate_stale_case_cache()
    updated_categories = tracker.get_comprehensive_stale_cases(case_manager)
    
    print("\nUpdated Categories:")
    for category, cases in updated_categories.items():
        print(f"  {category}: {len(cases)} cases")
    
    # Check if our test case moved categories
    new_category = None
    new_case_data = None
    for category, cases in updated_categories.items():
        for case in cases:
            if case['pv'] == test_case_pv:
                new_category = category
                new_case_data = case
                break
        if new_category:
            break
    
    if new_category != 'critical':
        print(f"\n[SUCCESS] Case {test_case_pv} moved from 'critical' to '{new_category}'")
        print(f"   New days since contact: {new_case_data['days_since_contact']}")
        return True
    else:
        print(f"\n[ISSUE] Case {test_case_pv} still in 'critical' category")
        print(f"   Days since contact: {new_case_data['days_since_contact']}")
        return False

if __name__ == "__main__":
    try:
        success = test_real_time_category_updates()
        if success:
            print("\n[PASSED] Real-time category update test PASSED!")
        else:
            print("\n[FAILED] Real-time category update test FAILED!")
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()