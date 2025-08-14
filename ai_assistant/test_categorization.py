#!/usr/bin/env python3
"""
Test script to verify categorization logic
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import Config
from utils.logging_config import setup_logging
from services.gmail_service import GmailService
from services.ai_service import AIService
from services.collections_tracker import CollectionsTracker
from services.bulk_email_service import BulkEmailService
from case_manager import CaseManager


def main():
    """Test categorization logic"""
    print("=" * 60)
    print("Testing Categorization Logic")
    print("=" * 60)
    
    try:
        # Initialize services
        print("\n[INIT] Initializing services...")
        setup_logging()
        
        # Initialize core services
        ai_service = AIService()
        case_manager = CaseManager()
        collections_tracker = CollectionsTracker()
        
        # Try to initialize Gmail (optional)
        try:
            gmail_service = GmailService()
            print("[SUCCESS] Gmail service initialized")
        except:
            gmail_service = None
            print("[WARNING] Gmail service not available")
        
        # Initialize bulk email service
        bulk_email_service = BulkEmailService(
            gmail_service,
            case_manager,
            ai_service,
            collections_tracker
        )
        
        print(f"[INFO] Loaded {len(case_manager.df)} cases")
        
        # Test categorization
        print("\n[TEST] Running categorization...")
        categories = bulk_email_service.categorize_cases()
        
        print("\n" + "=" * 60)
        print("CATEGORIZATION RESULTS")
        print("=" * 60)
        
        # Show never contacted
        never_contacted = categories.get("never_contacted", [])
        print(f"\n[NEVER CONTACTED]: {len(never_contacted)} cases")
        if never_contacted:
            print("  Sample cases:")
            for case in never_contacted[:3]:
                print(f"    - PV: {case['pv']}, Name: {case['name']}, Firm: {case['law_firm']}")
        
        # Show no recent contact
        no_recent = categories.get("no_recent_contact", [])
        print(f"\n[NO RECENT CONTACT (>60 days)]: {len(no_recent)} cases")
        if no_recent:
            print("  Sample cases:")
            for case in no_recent[:3]:
                days = case.get('days_since_contact', 'Unknown')
                print(f"    - PV: {case['pv']}, Name: {case['name']}, Days: {days}")
        
        # Show missing DOI
        missing_doi = categories.get("missing_doi", [])
        print(f"\n[MISSING DOI]: {len(missing_doi)} cases")
        if missing_doi:
            print("  Sample cases:")
            for case in missing_doi[:3]:
                print(f"    - PV: {case['pv']}, Name: {case['name']}")
        
        # Show old cases
        old_cases = categories.get("old_cases", [])
        print(f"\n[OLD CASES (>2 years)]: {len(old_cases)} cases")
        if old_cases:
            print("  Sample cases:")
            for case in old_cases[:3]:
                print(f"    - PV: {case['pv']}, Name: {case['name']}, DOI: {case.get('doi', 'N/A')}")
        
        # Show firms breakdown
        by_firm = categories.get("by_firm", {})
        print(f"\n[BY FIRM]: {len(by_firm)} firms")
        if by_firm:
            # Sort firms by case count
            sorted_firms = sorted(by_firm.items(), key=lambda x: len(x[1]), reverse=True)
            print("  Top 5 firms by case count:")
            for firm, cases in sorted_firms[:5]:
                print(f"    - {firm}: {len(cases)} cases")
        
        # Show priority breakdown
        by_priority = categories.get("by_priority", {})
        print(f"\n[BY PRIORITY]:")
        for priority_level in ["high", "medium", "low"]:
            cases = by_priority.get(priority_level, [])
            print(f"  {priority_level.upper()}: {len(cases)} cases")
        
        # Test stale case detection
        print("\n" + "=" * 60)
        print("STALE CASE ANALYSIS")
        print("=" * 60)
        
        # Get stale cases breakdown
        stale_categories = collections_tracker.get_comprehensive_stale_cases(case_manager)
        
        print(f"\n[CRITICAL (90+ days)]: {len(stale_categories.get('critical', []))} cases")
        print(f"[HIGH PRIORITY (60+ days)]: {len(stale_categories.get('high_priority', []))} cases")
        print(f"[NEEDS FOLLOW-UP (30+ days)]: {len(stale_categories.get('needs_follow_up', []))} cases")
        print(f"[NEVER CONTACTED]: {len(stale_categories.get('never_contacted', []))} cases")
        print(f"[NO RESPONSE]: {len(stale_categories.get('no_response', []))} cases")
        
        # Show collections dashboard
        print("\n" + "=" * 60)
        print("COLLECTIONS DASHBOARD")
        print("=" * 60)
        
        dashboard = collections_tracker.get_collections_dashboard()
        
        print(f"\n[TOTAL TRACKED]: {dashboard['total_cases']} cases")
        print(f"[STATUS BREAKDOWN]:")
        for status, count in dashboard['status_breakdown'].items():
            print(f"  - {status.title()}: {count}")
        
        print(f"\n[STALE CASES]:")
        print(f"  - 30+ days: {dashboard['stale_cases']['30_days']}")
        print(f"  - 60+ days: {dashboard['stale_cases']['60_days']}")
        print(f"  - 90+ days: {dashboard['stale_cases']['90_days']}")
        
        if dashboard['top_responsive_firms']:
            print(f"\n[TOP RESPONSIVE FIRMS]:")
            for firm, rate in dashboard['top_responsive_firms'][:5]:
                print(f"  - {firm}: {rate:.1f}% response rate")
        
        print("\n" + "=" * 60)
        print("CATEGORIZATION TEST COMPLETE")
        print("=" * 60)
        
        # Summary
        total_categorized = (
            len(never_contacted) + 
            len(no_recent) + 
            len(missing_doi) + 
            len(old_cases)
        )
        
        print(f"\n[SUMMARY]")
        print(f"  Total cases: {len(case_manager.df)}")
        print(f"  Categorized cases: {total_categorized}")
        print(f"  Firms identified: {len(by_firm)}")
        print(f"  Cases needing attention: {dashboard['stale_cases']['30_days']}")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)