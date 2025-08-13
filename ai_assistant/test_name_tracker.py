#!/usr/bin/env python3
"""
Test the name-based collections tracker
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.collections_tracker_name_based import NameBasedCollectionsTracker
from services.email_cache_service import EmailCacheService
from services.gmail_service import GmailService
from services.case_manager import CaseManager

def main():
    print("\n" + "="*60)
    print("TESTING NAME-BASED COLLECTIONS TRACKER")
    print("="*60)
    
    try:
        # Initialize services
        print("\n📧 Initializing services...")
        gmail_service = GmailService()
        email_cache = EmailCacheService(gmail_service)
        case_manager = CaseManager()
        
        # Create name-based tracker
        print("🔍 Creating name-based tracker...")
        tracker = NameBasedCollectionsTracker(email_cache)
        
        # Run analysis
        print("\n🚀 Starting analysis...")
        success = tracker.analyze_from_cache(case_manager)
        
        if success:
            print("\n✅ Analysis complete!")
        else:
            print("\n❌ Analysis failed")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()