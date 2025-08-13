#!/usr/bin/env python3
"""
Debug script to check what's in the collections_tracking.json cache
"""

import json
import os
from datetime import datetime

def debug_cache():
    cache_file = "data/collections_tracking.json"
    
    if not os.path.exists(cache_file):
        print("❌ No cache file found")
        return
    
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Cache Statistics:")
    print(f"   Total cases: {len(data.get('cases', {}))}")
    
    # Check a few specific cases
    test_cases = ["333925", "295187", "276295"]
    
    for pv in test_cases:
        if pv in data["cases"]:
            case_data = data["cases"][pv]
            activities = len(case_data.get("activities", []))
            last_contact = case_data.get("last_contact")
            
            print(f"\n🔍 Case {pv}:")
            print(f"   Activities: {activities}")
            print(f"   Last Contact: {last_contact}")
            
            # Check if all dates are today (bootstrap bug)
            if last_contact:
                contact_date = datetime.fromisoformat(last_contact).date()
                today = datetime.now().date()
                is_today = contact_date == today
                print(f"   Is Today's Date: {is_today} {'❌ BOOTSTRAP BUG!' if is_today else '✅ Historical date'}")
            
            # Show first activity for comparison
            if case_data.get("activities"):
                first_activity = case_data["activities"][0]
                activity_details = first_activity.get("details", {})
                sent_date = activity_details.get("sent_date")
                print(f"   Activity sent_date: {sent_date}")

if __name__ == "__main__":
    debug_cache()