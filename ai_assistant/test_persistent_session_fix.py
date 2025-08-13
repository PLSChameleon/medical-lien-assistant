#!/usr/bin/env python3
"""
Test script to verify PERSISTENT SESSION BUG FIX
The health check was failing due to invalid timeout parameter
"""

import asyncio
import sys
import os

# Add project root to Python path  
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.cms_integration import CMSIntegrationService

async def test_persistent_session_fix():
    """Test that persistent session health check works correctly"""
    
    print("🔧 PERSISTENT SESSION BUG FIX TEST")
    print("=" * 60)
    print()
    print("BUG IDENTIFIED:")
    print("❌ Health check used invalid timeout parameter: page.evaluate(..., timeout=5000)")
    print("✅ Fixed with asyncio.wait_for() for proper timeout handling")
    print()
    print("EXPECTED BEHAVIOR:")
    print("1. Initialize persistent session (manual certificate dismissal)")
    print("2. Health check should PASS (no timeout parameter error)")  
    print("3. Subsequent operations should reuse the session")
    print("4. No new browser windows should open")
    print()
    
    try:
        # Test 1: Check if health check works when no session exists
        print("TEST 1: Health check with no persistent session...")
        healthy = await CMSIntegrationService.is_persistent_session_healthy()
        print(f"Health check result (should be False): {healthy}")
        if not healthy:
            print("✅ Correctly identified no session exists")
        else:
            print("❌ Unexpected result - should be False")
        print()
        
        # Test 2: Initialize persistent session
        print("TEST 2: Initializing persistent session...")
        print("📋 Browser will open - please click 'Cancel' on certificate popup")
        success = await CMSIntegrationService.initialize_persistent_session()
        
        if not success:
            print("❌ Session initialization failed")
            return False
            
        print("✅ Persistent session initialized!")
        print()
        
        # Test 3: Health check should now pass
        print("TEST 3: Health check with active session...")
        healthy = await CMSIntegrationService.is_persistent_session_healthy()
        print(f"Health check result (should be True): {healthy}")
        
        if healthy:
            print("✅ Health check PASSED - session is healthy!")
            print("✅ Fixed the timeout parameter bug!")
        else:
            print("❌ Health check FAILED - there may be other issues")
            return False
        print()
        
        # Test 4: Test session reuse
        print("TEST 4: Testing session reuse...")
        service = CMSIntegrationService(use_persistent_session=True)
        await service.start_session()
        
        if service.page == CMSIntegrationService._persistent_page:
            print("✅ Session reused successfully!")
            print("✅ No new browser window opened!")
            print("🎉 Persistent session bug is FIXED!")
        else:
            print("❌ Session not reused - may still have issues")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_test():
    """Run the async test"""
    try:
        return asyncio.run(test_persistent_session_fix())
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 PERSISTENT SESSION BUG FIX VERIFICATION")
    print("=" * 60)
    print()
    print("This test verifies the fix for:")
    print("ERROR: Page.evaluate() got an unexpected keyword argument 'timeout'")
    print()
    print("FIXED BY:")
    print("- Using asyncio.wait_for() for timeout control")
    print("- Better health check logic")  
    print("- Improved logging and diagnostics")
    print()
    print("STEPS:")
    print("1. Test health check with no session (should fail gracefully)")
    print("2. Initialize session (you dismiss certificate popup)")
    print("3. Test health check with active session (should pass)")
    print("4. Test session reuse (should use existing session)")
    print()
    
    confirm = input("Ready to test the persistent session bug fix? (y/n): ").lower().strip()
    if confirm == 'y':
        success = run_test()
        if success:
            print("\n🎉 PERSISTENT SESSION BUG FIX VERIFIED!")
            print("Your CMS integration should now work properly!")
        else:
            print("\n💥 BUG FIX VERIFICATION FAILED!")
            print("There may be additional issues to resolve.")
    else:
        print("Test cancelled.")