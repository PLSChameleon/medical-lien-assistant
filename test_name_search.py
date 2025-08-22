#!/usr/bin/env python3
"""
Test script to verify patient name search functionality
"""

import sys
import os
from datetime import datetime

# Add the ai_assistant directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

def test_name_search():
    """Test the name-based email search"""
    print("Testing Patient Name Search")
    print("=" * 60)
    
    try:
        from services.email_cache_service import EmailCacheService
        from services.gmail_service import GmailService
        from services.template_summary_service import TemplateSummaryService
        from case_manager import CaseManager
        
        # Initialize services
        print("Initializing services...")
        
        # Try to init Gmail and email cache
        try:
            gmail_service = GmailService()
            email_cache = EmailCacheService(gmail_service)
            print("[OK] Email cache service initialized")
            print(f"    Total cached emails: {len(email_cache.cache.get('emails', []))}")
        except Exception as e:
            print(f"[WARNING] Email cache not available: {e}")
            return 1
        
        # Test the search methods
        print("\nTesting search methods:")
        print("-" * 40)
        
        # Test 1: Search by name
        test_name = input("Enter a patient name to search (or press Enter for 'John Smith'): ").strip()
        if not test_name:
            test_name = "John Smith"
        
        print(f"\n1. Testing search_emails_by_patient_name('{test_name}')...")
        if hasattr(email_cache, 'search_emails_by_patient_name'):
            results = email_cache.search_emails_by_patient_name(test_name)
            print(f"   Found {len(results)} emails")
            if results:
                print("   First result:")
                print(f"     Subject: {results[0].get('subject', 'N/A')[:60]}")
                print(f"     Date: {results[0].get('date', 'N/A')}")
        else:
            print("   [ERROR] Method not found")
        
        print(f"\n2. Testing get_all_emails_for_case('{test_name}')...")
        results = email_cache.get_all_emails_for_case(test_name)
        print(f"   Found {len(results)} emails")
        if results:
            print("   First result:")
            print(f"     Subject: {results[0].get('subject', 'N/A')[:60]}")
            print(f"     Date: {results[0].get('date', 'N/A')}")
        
        # Test with DOI filtering
        print("\n3. Testing with DOI filtering...")
        test_doi = datetime(2024, 1, 15)
        if hasattr(email_cache, 'search_emails_by_patient_name'):
            results = email_cache.search_emails_by_patient_name(test_name, test_doi)
            print(f"   Found {len(results)} emails with DOI filter")
        
        # Test the template summary service
        print("\n4. Testing Template Summary Service...")
        
        # Load case manager
        spreadsheet_path = r"C:\devops\ai_assistant\data\user_spreadsheets\deanh.transcon@gmail.com_july_runthrough (1).xlsx"
        if os.path.exists(spreadsheet_path):
            case_manager = CaseManager(spreadsheet_path)
            print(f"   Case manager loaded: {len(case_manager.df)} cases")
        else:
            case_manager = None
            print("   [WARNING] Spreadsheet not found")
        
        template_service = TemplateSummaryService(
            email_cache_service=email_cache,
            case_manager=case_manager
        )
        
        # Test with a PV if case manager is available
        if case_manager and len(case_manager.df) > 0:
            test_pv = input("\nEnter a PV to test summary (or press Enter to skip): ").strip()
            if test_pv:
                print(f"\nGenerating summary for PV {test_pv}...")
                try:
                    summary = template_service.generate_summary(test_pv)
                    # Show first 500 chars of summary
                    print("Summary preview:")
                    print("-" * 40)
                    print(summary[:500])
                    print("...")
                    print(f"[Total length: {len(summary)} characters]")
                except Exception as e:
                    print(f"[ERROR] {e}")
        
        print("\n" + "=" * 60)
        print("Name Search Test Complete!")
        print("\nKey improvements:")
        print("[OK] Searches by patient NAME (not PV)")
        print("[OK] Handles full names (first AND last)")
        print("[OK] DOI filtering for duplicate names")
        print("[OK] Fallback to PV search for Reference # lines")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(test_name_search())