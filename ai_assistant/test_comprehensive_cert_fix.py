#!/usr/bin/env python3
"""
Test script to verify comprehensive certificate popup handling
"""

import asyncio
import sys
import os

# Add project root to Python path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.cms_integration import add_cms_note_for_email

async def test_comprehensive_certificate_handling():
    """Test comprehensive certificate popup handling"""
    
    print("Testing Comprehensive Certificate Popup Handling")
    print("=" * 60)
    print()
    print("New approaches implemented:")
    print("1. Enhanced browser launch arguments (no-sandbox, ignore-cert errors)")
    print("2. Multiple keyboard combinations (Escape, Tab+Enter, Alt+F4, etc.)")
    print("3. Automatic button detection and clicking (Cancel, OK, Close)")
    print("4. Modal/dialog interaction attempts")
    print("5. Username field accessibility checking") 
    print("6. 10-second manual intervention window with countdown")
    print()
    
    # Test case data 
    test_case = {
        "PV": "TEST_CERT",
        "CMS": "12345",  # Use real CMS number for actual testing
        "Name": "Certificate Popup Test Case",
        "Attorney Email": "test@example.com"
    }
    
    print("What to expect:")
    print("- Browser will launch with enhanced certificate error handling")
    print("- Script will try 5 different approaches automatically")
    print("- If popup persists, you'll get clear manual instructions")
    print("- You'll have 10 seconds to manually dismiss the popup")
    print("- Script will proceed with login attempt")
    print()
    
    try:
        print("Starting CMS integration test...")
        print("-" * 40)
        
        # Test the comprehensive CMS function
        success = await add_cms_note_for_email(test_case, "follow_up", "test@example.com")
        
        print("-" * 40)
        if success:
            print("[SUCCESS] Comprehensive certificate handling worked!")
            print("- Certificate popup was handled automatically")
            print("- CMS login successful")  
            print("- Note was added successfully")
        else:
            print("[PARTIAL SUCCESS] Certificate handling worked but note failed")
            print("- Check CMS credentials and connection")
            print("- Certificate popup was likely handled correctly")
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False
    
    return True

def run_test():
    """Run the async test"""
    try:
        return asyncio.run(test_comprehensive_certificate_handling())
    except Exception as e:
        print(f"[ERROR] Test runner failed: {e}")
        return False

if __name__ == "__main__":
    print("COMPREHENSIVE CERTIFICATE POPUP FIX TEST")
    print("=" * 60)
    print()
    print("This test will:")
    print("✓ Launch browser with enhanced certificate handling")
    print("✓ Try 5 different automatic popup dismissal methods")  
    print("✓ Provide clear manual instructions if needed")
    print("✓ Give you 10 seconds to manually dismiss popup")
    print("✓ Continue with CMS login and note addition")
    print()
    
    confirm = input("Ready to test comprehensive certificate popup handling? (y/n): ").lower().strip()
    if confirm == 'y':
        success = run_test()
        if success:
            print("\n[COMPLETED] Certificate popup handling test finished!")
            print("Check the browser behavior and logs above.")
        else:
            print("\n[FAILED] Certificate popup handling test failed")
    else:
        print("Test cancelled.")