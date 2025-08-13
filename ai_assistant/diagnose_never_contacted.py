#!/usr/bin/env python3
"""
Diagnose why 546 cases show as never contacted
"""

import json
import os
from services.case_manager import CaseManager

def diagnose_never_contacted():
    print("\n" + "="*60)
    print("DIAGNOSING NEVER CONTACTED CASES")
    print("="*60)
    
    # Load the enhanced tracker data
    tracking_file = "data/collections_tracking_enhanced.json"
    if not os.path.exists(tracking_file):
        print("❌ No enhanced tracking data found. Run 'bootstrap collections' first.")
        return
    
    with open(tracking_file, 'r') as f:
        data = json.load(f)
    
    # Count categories
    never_contacted = []
    no_response = []
    has_responses = []
    
    for pv, case_data in data['cases'].items():
        sent = case_data.get('sent_count', 0)
        received = case_data.get('response_count', 0)
        
        if sent == 0 and received == 0:
            never_contacted.append({
                'pv': pv,
                'name': case_data.get('case_info', {}).get('name', ''),
                'firm': case_data.get('case_info', {}).get('law_firm', '')
            })
        elif sent > 0 and received == 0:
            no_response.append({
                'pv': pv,
                'name': case_data.get('case_info', {}).get('name', ''),
                'sent': sent
            })
        else:
            has_responses.append(pv)
    
    print(f"\n📊 ENHANCED TRACKER RESULTS:")
    print(f"   Never contacted (no sent, no received): {len(never_contacted)}")
    print(f"   No response (sent but no reply): {len(no_response)}")
    print(f"   Has responses: {len(has_responses)}")
    print(f"   Total cases: {len(data['cases'])}")
    
    # Show sample of never contacted
    print(f"\n📋 Sample of 'Never Contacted' cases:")
    for case in never_contacted[:10]:
        print(f"   PV {case['pv']}: {case['name']}")
        print(f"      Firm: {case['firm']}")
    
    # Load the old tracker data for comparison
    old_tracking_file = "data/collections_tracking.json"
    if os.path.exists(old_tracking_file):
        with open(old_tracking_file, 'r') as f:
            old_data = json.load(f)
        
        # Count old tracker categories
        old_never = 0
        old_no_response = 0
        
        for pv, case_data in old_data.get('cases', {}).items():
            activities = case_data.get('activities', [])
            responses = case_data.get('response_count', 0)
            
            if not activities:
                old_never += 1
            elif activities and responses == 0:
                old_no_response += 1
        
        print(f"\n📊 OLD TRACKER RESULTS (for comparison):")
        print(f"   Never contacted: {old_never}")
        print(f"   No response: {old_no_response}")
    
    # Check email cache to verify
    cache_file = "data/email_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        
        print(f"\n📧 EMAIL CACHE:")
        print(f"   Total emails in cache: {len(cache.get('emails', []))}")
        
        # Sample check - look for a "never contacted" case in emails
        if never_contacted:
            test_case = never_contacted[0]
            pv = test_case['pv']
            name = test_case['name']
            
            print(f"\n🔍 Checking if PV {pv} ({name}) really has no emails...")
            
            found_emails = []
            for email in cache.get('emails', [])[:1000]:  # Check first 1000
                email_text = f"{email.get('subject', '')} {email.get('snippet', '')}".lower()
                
                # Check for PV
                if pv in email_text:
                    found_emails.append(email.get('subject', '')[:50])
                
                # Check for name
                if name and name.lower() in email_text:
                    found_emails.append(email.get('subject', '')[:50])
            
            if found_emails:
                print(f"   ⚠️  FOUND {len(found_emails)} emails that might match!")
                for subj in found_emails[:3]:
                    print(f"      - {subj}")
                print("\n   This suggests the matching logic is too strict!")
            else:
                print(f"   ✅ Confirmed: No emails found for this case")
    
    # Check case manager data
    print("\n📊 CHECKING CASE DATA:")
    case_manager = CaseManager()
    
    # Check for empty names or other issues
    empty_names = 0
    for _, row in case_manager.df.iterrows():
        case_info = case_manager.format_case(row)
        if not case_info.get("Name") or case_info.get("Name").strip() == "":
            empty_names += 1
    
    print(f"   Cases with empty names: {empty_names}")
    
    print("\n💡 POSSIBLE ISSUES:")
    print("1. Matching is too strict (exact substring only)")
    print("2. Name format mismatches (SMITH, JOHN vs John Smith)")
    print("3. Email cache might not have all emails")
    print("4. PV numbers not being extracted from email text")


if __name__ == "__main__":
    diagnose_never_contacted()