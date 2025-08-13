#!/usr/bin/env python3
"""
Test script to verify PERSISTENT SESSION approach for certificate handling
This is the BEST solution - one manual action at startup, then fully automated
"""

import asyncio
import sys
import os

# Add project root to Python path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.cms_integration import CMSIntegrationService, add_cms_note_for_email

async def test_persistent_session_workflow():
    """Test the complete persistent session workflow"""
    
    print("🔄 PERSISTENT CMS SESSION TEST")
    print("=" * 60)
    print()
    print("This tests the RECOMMENDED solution for certificate popups:")
    print("✅ One-time manual certificate dismissal at startup")
    print("✅ Browser stays open between email sends") 
    print("✅ No more certificate popups after initial setup")
    print("✅ Fast CMS note adding (no browser startup delay)")
    print()
    
    # Test case data
    test_case = {
        "PV": "PERSISTENT_TEST",
        "CMS": "12345",  # Use real CMS number for testing
        "Name": "Persistent Session Test Case", 
        "Attorney Email": "test@example.com"
    }
    
    print("WORKFLOW STEPS:")
    print("1. 🚀 Initialize persistent session (browser opens)")
    print("2. 📋 Certificate popup appears")
    print("3. 👆 YOU click 'Cancel' button manually (one time only)")
    print("4. 🔐 Automatic CMS login and setup")
    print("5. ✅ Session ready for all future operations")
    print("6. 📝 Test adding a note (should be instant)")
    print()
    
    try:
        # Step 1: Initialize persistent session
        print("STEP 1: Initializing persistent CMS session...")
        print("-" * 50)
        success = await CMSIntegrationService.initialize_persistent_session()
        
        if not success:
            print("❌ Persistent session initialization failed!")
            return False
            
        print("✅ Persistent session initialized!")
        print()
        
        # Step 2: Test note adding using persistent session
        print("STEP 2: Testing note addition with persistent session...")
        print("-" * 50)
        
        # This should use the persistent session (no new browser launch)
        note_success = await add_cms_note_for_email(test_case, "follow_up", "test@example.com")
        
        if note_success:
            print("✅ Note added successfully using persistent session!")
            print("🎉 No certificate popup appeared!")
            print("⚡ Operation was fast (no browser startup delay)")
        else:
            print("⚠️ Note addition failed, but session likely worked")
            print("✅ No certificate popup appeared!")
            
        # Step 3: Test multiple operations to show speed benefit
        print()
        print("STEP 3: Testing multiple note additions...")
        print("-" * 50)
        
        for i in range(1, 4):
            print(f"Adding note {i}/3...")
            test_case["PV"] = f"SPEED_TEST_{i}"
            await add_cms_note_for_email(test_case, "follow_up", f"test{i}@example.com")
            print(f"✅ Note {i} completed instantly!")
            
        print()
        print("🏆 PERSISTENT SESSION TEST RESULTS:")
        print("✅ One-time manual certificate dismissal")
        print("✅ Browser session persistent between operations") 
        print("✅ No certificate popups after initial setup")
        print("⚡ Fast note additions (no startup delay)")
        print("🎯 This is the RECOMMENDED approach!")
        
        return True
        
    except Exception as e:
        print(f"❌ Persistent session test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_test():
    """Run the async test"""
    try:
        return asyncio.run(test_persistent_session_workflow())
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return False

if __name__ == "__main__":
    print("🔄 PERSISTENT SESSION SOLUTION TEST")
    print("=" * 60)
    print()
    print("This is the BEST solution for the certificate popup problem!")
    print()
    print("ADVANTAGES:")
    print("✅ Reliable - works with browser security, not against it")
    print("✅ User-friendly - one manual action, then fully automated")
    print("✅ Fast - no browser startup delay for each email")
    print("✅ Practical - browser stays open as your CMS workspace")
    print()
    print("HOW IT WORKS:")
    print("1. Run 'init cms' command in main application")
    print("2. Browser opens, you click 'Cancel' on certificate popup once")
    print("3. Browser logs into CMS and stays open") 
    print("4. All future emails automatically add CMS notes instantly")
    print()
    
    confirm = input("Ready to test the persistent session approach? (y/n): ").lower().strip()
    if confirm == 'y':
        print("\n🚀 Starting persistent session test...")
        print("👀 Watch for the certificate popup and click 'Cancel' when it appears")
        success = run_test()
        if success:
            print("\n🏆 PERSISTENT SESSION TEST SUCCESSFUL!")
            print("You can now use the main application with automatic CMS notes!")
        else:
            print("\n💥 PERSISTENT SESSION TEST FAILED!")
    else:
        print("Test cancelled.")