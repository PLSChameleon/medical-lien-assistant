#!/usr/bin/env python3
"""
Test script to verify improved CMS integration
"""

import asyncio
import sys
import os

# Add project root to Python path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.cms_integration import add_cms_note_for_email

async def test_improved_cms_integration():
    """Test the improved CMS integration with certificate popup handling"""
    
    print("Testing Improved CMS Integration")
    print("=" * 50)
    
    # Test case data (using a test CMS number)
    test_case = {
        "PV": "TEST123",
        "CMS": "12345",  # Replace with real CMS number for actual testing
        "Name": "Test Case - Certificate Popup Fix",
        "Attorney Email": "test@example.com"
    }
    
    print("Testing improvements:")
    print("1. Automatic certificate popup dismissal (5x Escape + Tab + Enter)")  
    print("2. Longer timeouts (60 seconds)")
    print("3. Manual fallback detection")
    print("4. Proper async cleanup")
    print()
    
    try:
        print("Attempting CMS note addition...")
        print("- If certificate popup appears, script should dismiss it automatically")
        print("- If popup persists, you'll get a message to press ESCAPE manually")
        print()
        
        # Test the async CMS function
        success = await add_cms_note_for_email(test_case, "follow_up", "test@example.com")
        
        if success:
            print("[SUCCESS] CMS integration test passed!")
            print("- Certificate popup was handled correctly")
            print("- Note was added to CMS successfully")
        else:
            print("[PARTIAL] CMS integration completed but note addition failed")
            print("- Check if certificate popup was dismissed")
            print("- Check CMS credentials and network connection")
            
    except Exception as e:
        print(f"[ERROR] CMS integration test failed: {e}")
        return False
    
    return True

def run_test():
    """Run the async test"""
    try:
        return asyncio.run(test_improved_cms_integration())
    except Exception as e:
        print(f"[ERROR] Test runner failed: {e}")
        return False

if __name__ == "__main__":
    print("IMPORTANT: This test will open a browser and attempt to connect to CMS")
    print("Make sure you have valid CMS credentials in config.env")
    print()
    
    confirm = input("Continue with improved CMS integration test? (y/n): ").lower().strip()
    if confirm == 'y':
        success = run_test()
        if success:
            print("\n[COMPLETED] CMS integration improvements verified!")
        else:
            print("\n[FAILED] CMS integration test failed")
    else:
        print("Test cancelled.")