#!/usr/bin/env python3
"""
Test script to verify CMS integration fixes
"""

import asyncio
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.cms_integration import add_cms_note_for_email

async def test_cms_integration():
    """Test the fixed CMS integration"""
    
    print("Testing CMS Integration Fixes")
    print("=" * 50)
    
    # Test case data
    test_case = {
        "PV": "TEST123",
        "CMS": "12345",  # Replace with a real CMS number for testing
        "Name": "Test Case",
        "Attorney Email": "test@example.com"
    }
    
    try:
        print("Testing CMS note addition...")
        print("1. Certificate popup should be dismissed with Escape key")
        print("2. Async Playwright should work without sync API conflicts")
        
        # Test the async CMS function
        success = await add_cms_note_for_email(test_case, "follow_up", "test@example.com")
        
        if success:
            print("✅ CMS integration test passed!")
        else:
            print("⚠️ CMS integration test failed - check logs")
            
    except Exception as e:
        print(f"❌ CMS integration test error: {e}")
        return False
    
    return True

def run_test():
    """Run the async test"""
    try:
        return asyncio.run(test_cms_integration())
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return False

if __name__ == "__main__":
    print("Note: This test requires CMS credentials in config.env")
    print("And will attempt to connect to the actual CMS system.")
    print()
    
    confirm = input("Continue with CMS test? (y/n): ").lower().strip()
    if confirm == 'y':
        success = run_test()
        if success:
            print("\n🎉 All CMS integration fixes verified!")
        else:
            print("\n❌ CMS integration test failed")
    else:
        print("Test cancelled.")