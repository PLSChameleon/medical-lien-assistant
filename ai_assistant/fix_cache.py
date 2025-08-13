#!/usr/bin/env python3
"""
Fix existing cache by setting last_contact from activity sent_date
"""

import json
import os
from datetime import datetime

def fix_cache():
    cache_file = "data/collections_tracking.json"
    
    if not os.path.exists(cache_file):
        print("❌ No cache file found")
        return
    
    # Load cache
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed_count = 0
    
    print("🔧 Fixing cache - setting last_contact from activity sent_dates...")
    
    for pv, case_data in data["cases"].items():
        activities = case_data.get("activities", [])
        
        if activities and not case_data.get("last_contact"):
            # Find the most recent email date from activities
            most_recent_date = None
            
            for activity in activities:
                details = activity.get("details", {})
                sent_date = details.get("sent_date")
                
                if sent_date:
                    try:
                        activity_date = datetime.fromisoformat(sent_date)
                        if not most_recent_date or activity_date > most_recent_date:
                            most_recent_date = activity_date
                    except:
                        continue
            
            # Set last_contact to most recent email date
            if most_recent_date:
                case_data["last_contact"] = most_recent_date.isoformat()
                fixed_count += 1
                
                # Also set defaults for other missing fields
                if "response_count" not in case_data:
                    case_data["response_count"] = 0
                if "current_status" not in case_data:
                    case_data["current_status"] = "unknown"
                if "firm_email" not in case_data:
                    case_data["firm_email"] = None
    
    # Save fixed cache
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"✅ Fixed {fixed_count} cases - set last_contact from activity dates")
    
    # Test a few cases
    test_cases = ["333925", "295187", "276295"]
    print("\n📋 Verification:")
    
    for pv in test_cases:
        if pv in data["cases"]:
            case_data = data["cases"][pv]
            activities = len(case_data.get("activities", []))
            last_contact = case_data.get("last_contact")
            
            print(f"   Case {pv}: {activities} activities, last_contact = {last_contact}")

if __name__ == "__main__":
    fix_cache()