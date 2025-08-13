#!/usr/bin/env python3
"""
Debug script to test email-to-case matching logic
"""

import json
import os
from services.case_manager import CaseManager
from services.email_cache_service import EmailCacheService
from services.gmail_service import GmailService

def analyze_matching_issues():
    """Debug why cases aren't matching emails"""
    
    print("\n" + "="*60)
    print("EMAIL-TO-CASE MATCHING DEBUGGER")
    print("="*60)
    
    # Load cases
    print("\n📋 Loading cases from spreadsheet...")
    case_manager = CaseManager()
    cases_df = case_manager.df
    
    # Load email cache
    print("📧 Loading email cache...")
    cache_file = "data/email_cache.json"
    if not os.path.exists(cache_file):
        print("❌ No email cache found. Run 'bootstrap emails' first.")
        return
    
    with open(cache_file, 'r') as f:
        cache = json.load(f)
    
    emails = cache.get('emails', [])
    print(f"✅ Found {len(emails)} cached emails")
    
    # Get sample of cases to test
    print("\n🔍 Analyzing matching for first 10 cases...")
    sample_cases = []
    
    for _, row in cases_df.head(10).iterrows():
        case_info = case_manager.format_case(row)
        pv = str(case_info.get("PV", "")).strip()
        if pv:
            sample_cases.append({
                "pv": pv,
                "name": case_info.get("Name", ""),
                "cms": case_info.get("CMS", "")
            })
    
    # Test matching for each case
    for case in sample_cases:
        print(f"\n📁 Case PV {case['pv']}: {case['name']}")
        print(f"   CMS: {case['cms']}")
        
        # Build search terms
        search_terms = []
        if case['pv']:
            search_terms.append(case['pv'].lower())
        if case['name']:
            # Add full name
            search_terms.append(case['name'].lower())
            # Add individual name parts
            name_parts = case['name'].split()
            for part in name_parts:
                if len(part) > 2:  # Skip short words
                    search_terms.append(part.lower())
        if case['cms']:
            search_terms.append(str(case['cms']).lower())
        
        print(f"   Search terms: {search_terms}")
        
        # Count matches
        matches = 0
        matched_emails = []
        
        for email in emails[:100]:  # Check first 100 emails
            subject = (email.get('subject') or '').lower()
            snippet = (email.get('snippet') or '').lower()
            email_text = f"{subject} {snippet}"
            
            for term in search_terms:
                if term and term in email_text:
                    matches += 1
                    matched_emails.append({
                        "subject": email.get('subject', '')[:50],
                        "term": term
                    })
                    break
        
        if matches > 0:
            print(f"   ✅ Found {matches} matching emails")
            for match in matched_emails[:3]:
                print(f"      - '{match['term']}' found in: {match['subject']}")
        else:
            print(f"   ❌ NO MATCHES FOUND")
            # Show a sample email to see format
            if emails:
                sample = emails[0]
                print(f"   Sample email subject: {sample.get('subject', '')[:50]}")
                print(f"   Sample email snippet: {sample.get('snippet', '')[:50]}")
    
    # Check common issues
    print("\n" + "="*60)
    print("COMMON MATCHING ISSUES")
    print("="*60)
    
    # Check name formats in emails
    print("\n📝 Checking name formats in emails...")
    name_formats = set()
    for email in emails[:50]:
        subject = email.get('subject', '')
        # Look for patterns like "DOI" or "//" which indicate case emails
        if "DOI" in subject or "//" in subject:
            # Extract the name part
            if "//" in subject:
                name_part = subject.split("//")[0].strip()
                name_part = name_part.replace("DOI", "").strip()
                # Remove date if present
                import re
                name_part = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', name_part).strip()
                name_part = re.sub(r'\d{4}-\d{2}-\d{2}', '', name_part).strip()
                if name_part:
                    name_formats.add(name_part[:30])
    
    print("Sample name formats found in email subjects:")
    for name in list(name_formats)[:10]:
        print(f"   - {name}")
    
    # Check PV number formats
    print("\n🔢 Checking PV number formats...")
    pv_formats = set()
    for email in emails[:50]:
        text = f"{email.get('subject', '')} {email.get('snippet', '')}"
        # Look for patterns like "PV" or "File #" or just numbers
        import re
        # Match PV followed by numbers
        pv_matches = re.findall(r'PV\s*#?\s*(\d+)', text, re.IGNORECASE)
        for pv in pv_matches:
            pv_formats.add(f"PV {pv}")
        # Match File # followed by numbers
        file_matches = re.findall(r'File\s*#?\s*:?\s*(\d+)', text, re.IGNORECASE)
        for file_num in file_matches:
            pv_formats.add(f"File # {file_num}")
    
    print("Sample PV/File number formats found:")
    for pv in list(pv_formats)[:10]:
        print(f"   - {pv}")
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. Check if case names in spreadsheet match email format")
    print("2. Consider using PV numbers as primary matcher")
    print("3. May need fuzzy matching for names (last name only, etc.)")


if __name__ == "__main__":
    analyze_matching_issues()