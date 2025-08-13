#!/usr/bin/env python3
"""
Test script to verify contact detection fixes
"""

import os
import sys
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.collections_tracker import CollectionsTracker
from case_manager import CaseManager

def test_contact_detection():
    """Test the fixed contact detection logic"""
    
    print("Testing Contact Detection Logic")
    print("=" * 50)
    
    # Create minimal case manager for testing
    case_manager = CaseManager("data/cases.xlsx")
    
    # Create collections tracker
    tracker = CollectionsTracker()
    
    # Test with cached data
    if os.path.exists("data/collections_tracking.json"):
        with open("data/collections_tracking.json", 'r') as f:
            tracker.data = json.load(f)
        
        print(f"Loaded {len(tracker.data.get('cases', {}))} cached cases")
        
        # Get stale case analysis
        stale_categories = tracker.get_comprehensive_stale_cases(case_manager)
        
        print("\nSTALE CASE ANALYSIS RESULTS:")
        print("-" * 30)
        for category, cases in stale_categories.items():
            print(f"{category}: {len(cases)} cases")
        
        # Test specific problematic cases
        test_cases = ["295187", "333925", "276295"]
        print(f"\nTesting specific cases: {test_cases}")
        print("-" * 30)
        
        for pv in test_cases:
            case_data = tracker.data.get('cases', {}).get(pv, {})
            if case_data:
                activities = case_data.get('activities', [])
                last_contact = case_data.get('last_contact')
                print(f"PV {pv}:")
                print(f"  Activities: {len(activities)}")
                print(f"  Last Contact: {last_contact}")
                
                # Check which category this case ended up in
                for category, cases in stale_categories.items():
                    if any(case['pv'] == pv for case in cases):
                        print(f"  Category: {category}")
                        break
                print()
        
    else:
        print("No cached data found. Run bootstrap first.")

if __name__ == "__main__":
    test_contact_detection()