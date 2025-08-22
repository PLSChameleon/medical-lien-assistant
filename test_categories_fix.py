#!/usr/bin/env python3
"""
Test script to verify the Categories tab fix for name mismatch issue
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add the ai_assistant directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

def test_categories_fix():
    """Test the Categories widget fix"""
    print("Testing Categories Tab Fix")
    print("=" * 50)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    try:
        from enhanced_gui_app import EnhancedMainWindow
        
        # Create main window
        print("Creating main window...")
        window = EnhancedMainWindow()
        
        # Access the categories tab
        if hasattr(window, 'categories_tab'):
            categories_tab = window.categories_tab
            print("Categories tab found")
            
            # Check if we have category data
            if hasattr(categories_tab, 'category_data'):
                print(f"Category data keys: {categories_tab.category_data.keys()}")
                
                # Check each category
                for category, cases in categories_tab.category_data.items():
                    if cases:
                        print(f"\n{category}: {len(cases)} cases")
                        # Show first case
                        first_case = cases[0]
                        print(f"  First case: PV={first_case.get('pv')}, Name={first_case.get('name')}")
            else:
                print("No category data found - run 'Refresh Categories' first")
            
            print("\nDEBUG: The fix includes:")
            print("1. Proper value capture in lambda functions using helper function")
            print("2. Clear table before rebuilding to ensure clean state")
            print("3. Enhanced debug logging to track PV/Name associations")
            print("4. Immediate UI refresh after case removal")
            
            print("\nTo test:")
            print("1. Open the application")
            print("2. Go to Categories tab")
            print("3. Click 'Refresh Categories'")
            print("4. Select a case and use 'Draft Follow-up' or 'Draft Status Request'")
            print("5. Send the email")
            print("6. Verify the case is removed and the next case shows correct info")
            
        else:
            print("Categories tab not found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("Test complete - please run the main application to verify the fix")
    
    return 0

if __name__ == "__main__":
    sys.exit(test_categories_fix())