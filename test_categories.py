#!/usr/bin/env python3
"""Test category population to diagnose issues"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / "ai_assistant"))

from case_manager import CaseManager
from services.collections_tracker import CollectionsTracker
from datetime import datetime
import json

def test_categories():
    print("Testing Category Population\n" + "="*50)
    
    # Load the user's spreadsheet
    spreadsheet_path = "ai_assistant/data/user_spreadsheets/deanh.transcon@gmail.com_july_runthrough (1).xlsx"
    
    print(f"Loading spreadsheet: {spreadsheet_path}")
    case_manager = CaseManager(spreadsheet_path)
    print(f"Total cases loaded: {len(case_manager.df)}")
    
    # Initialize collections tracker
    tracker = CollectionsTracker()
    
    # Load email cache if available
    email_cache_path = "ai_assistant/data/email_cache.json"
    if os.path.exists(email_cache_path):
        print(f"\nLoading email cache from: {email_cache_path}")
        with open(email_cache_path, 'r') as f:
            email_cache = json.load(f)
        print(f"Email cache contains {len(email_cache.get('emails', {}))} emails")
        
        # Bootstrap the tracker
        print("\nBootstrapping CollectionsTracker...")
        tracker.bootstrap_from_email_cache(email_cache, case_manager)
    
    # Get categorized cases
    print("\nGetting categorized cases...")
    categories = tracker.get_comprehensive_stale_cases()
    
    print("\nCategory Results:")
    print("-" * 40)
    for category, cases in categories.items():
        print(f"{category}: {len(cases)} cases")
        if len(cases) > 0 and category in ["missing_doi", "ccp_335_1"]:
            # Show sample cases
            print(f"  Sample cases from {category}:")
            for case in cases[:3]:
                pv = case.get('pv', 'Unknown')
                name = case.get('name', 'Unknown')
                doi = case.get('doi', 'Not set')
                doa = case.get('doa', 'Not set')
                print(f"    - PV: {pv}, Name: {name}, DOI: {doi}, DOA: {doa}")
    
    # Check specific cases for DOI/DOA
    print("\n\nChecking first 5 cases for DOI/DOA values:")
    print("-" * 40)
    for i in range(min(5, len(case_manager.df))):
        row = case_manager.df.iloc[i]
        case_data = case_manager.format_case(row)
        pv = case_data.get("PV", "")
        name = case_data.get("Name", "")
        doi = case_data.get("DOI", "")
        doa = case_data.get("DOA", "")
        print(f"Case {i+1}: PV={pv}, Name={name[:20]}, DOI={doi}, DOA={doa}")
    
    # Check for 2099 dates
    print("\n\nChecking for 2099 placeholder dates:")
    print("-" * 40)
    count_2099 = 0
    for i in range(len(case_manager.df)):
        row = case_manager.df.iloc[i]
        doi_raw = row[4] if len(row) > 4 else ""
        if "2099" in str(doi_raw):
            count_2099 += 1
            if count_2099 <= 3:  # Show first 3
                print(f"  Found 2099 date in row {i}: PV={row[1]}, Name={row[3][:20]}")
    print(f"Total cases with 2099 dates: {count_2099}")

if __name__ == "__main__":
    test_categories()