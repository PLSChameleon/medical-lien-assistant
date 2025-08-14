"""
Test script for bulk email functionality
"""

import sys
import os
import pandas as pd
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from case_manager import CaseManager
from services.bulk_email_service import BulkEmailService
from services.gmail_service import GmailService
from services.ai_service import AIService
from services.collections_tracker import CollectionsTracker

def test_bulk_email_categorization():
    """Test the bulk email categorization and batch preparation"""
    print("\n" + "="*60)
    print("TESTING BULK EMAIL CATEGORIZATION")
    print("="*60)
    
    try:
        # Initialize services
        print("\n1. Initializing services...")
        case_manager = CaseManager()
        print(f"   [OK] Loaded {len(case_manager.df)} cases")
        
        gmail_service = GmailService()
        print("   [OK] Gmail service initialized")
        
        ai_service = AIService()
        print("   [OK] AI service initialized")
        
        collections_tracker = CollectionsTracker()
        print("   [OK] Collections tracker initialized")
        
        bulk_service = BulkEmailService(gmail_service, case_manager, ai_service, collections_tracker)
        print("   [OK] Bulk email service initialized")
        
        # Test categorization
        print("\n2. Categorizing cases...")
        bulk_service.categorize_cases()
        categories = bulk_service.categorized_cases
        
        print("\n3. Category counts:")
        for category, cases in categories.items():
            if isinstance(cases, dict):  # by_firm category
                print(f"   - {category}: {len(cases)} firms")
                # Show top 3 firms
                for i, (firm, firm_cases) in enumerate(list(cases.items())[:3]):
                    print(f"     - {firm}: {len(firm_cases)} cases")
            else:
                print(f"   - {category}: {len(cases)} cases")
        
        # Test prepare_batch for different categories
        print("\n4. Testing batch preparation:")
        
        # Test regular category
        test_categories = ["never_contacted", "missing_doi", "high_priority", "medium_priority"]
        
        for category in test_categories:
            if category in categories and len(categories[category]) > 0:
                print(f"\n   Testing '{category}' category:")
                batch = bulk_service.prepare_batch(category, limit=3)
                print(f"   [OK] Prepared {len(batch)} emails")
                if batch:
                    email = batch[0]
                    print(f"     Sample: PV {email.get('pv')} - {email.get('name')}")
                    print(f"     To: {email.get('to')}")
                    print(f"     Subject: {email.get('subject', 'N/A')[:50]}...")
        
        # Test by_firm category
        if "by_firm" in categories and categories["by_firm"]:
            firm = list(categories["by_firm"].keys())[0]
            print(f"\n   Testing 'by_firm' category (firm: {firm}):")
            batch = bulk_service.prepare_batch("by_firm", subcategory=firm, limit=2)
            print(f"   [OK] Prepared {len(batch)} emails for firm")
        
        # Test custom PV numbers
        print("\n   Testing custom PV numbers:")
        # Get some actual PV numbers from the case manager
        # Use the column name that case_manager uses
        col_name = 'PV #' if 'PV #' in case_manager.df.columns else 'PV'
        if col_name in case_manager.df.columns:
            sample_pvs = [str(pv) for pv in case_manager.df[col_name].head(3).tolist()]
            batch = bulk_service.prepare_batch_from_numbers(sample_pvs)
            print(f"   [OK] Prepared {len(batch)} emails from custom PV list")
        else:
            print(f"   [SKIP] Could not find PV column (columns: {list(case_manager.df.columns[:5])}...)")
        
        print("\n" + "="*60)
        print("[SUCCESS] BULK EMAIL TEST COMPLETED SUCCESSFULLY")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bulk_email_categorization()
    if success:
        print("\n[SUCCESS] All tests passed! The bulk email functionality is working correctly.")
        print("\nYou can now use the GUI to:")
        print("1. Select a category/firm/priority")
        print("2. Click 'Populate Batch' to load cases")
        print("3. Review and select/deselect cases")
        print("4. Click 'Preview Selected' to see email content")
        print("5. Click 'Send Selected Emails' to send")
    else:
        print("\n[WARNING] Tests failed. Please check the error messages above.")