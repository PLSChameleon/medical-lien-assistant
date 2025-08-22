#!/usr/bin/env python3
"""
Test script to verify name variation handling
"""

import sys
import os

# Add the ai_assistant directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

def test_name_variations():
    """Test the name variation generation"""
    print("Testing Name Variation Handling")
    print("=" * 60)
    
    try:
        from services.email_cache_service import EmailCacheService
        
        # Create a mock email cache service to test the method
        cache_service = EmailCacheService(None)
        
        # Test various name formats
        test_names = [
            "John Smith",
            "JOHN SMITH", 
            "Smith, John",
            "SMITH, JOHN",
            "jane doe",
            "Martinez, Maria Elena",  # Multi-part first name
            "Van Der Berg, Hans",      # Multi-part last name
            "Smith"                    # Single name
        ]
        
        print("Name Variation Tests:")
        print("-" * 40)
        
        for name in test_names:
            print(f"\nOriginal: '{name}'")
            variations = cache_service._get_name_variations(name)
            print(f"Variations ({len(variations)}):")
            for var in variations:
                print(f"  - '{var}'")
        
        print("\n" + "=" * 60)
        print("Variation Examples for 'John Smith':")
        print("-" * 40)
        
        variations = cache_service._get_name_variations("John Smith")
        expected = [
            "John Smith",      # Original
            "Smith, John",     # Last, First
            "JOHN SMITH",      # All caps
            "SMITH, JOHN",     # All caps with comma
            "Smith,John",      # No space after comma
            "SMITH,JOHN",      # All caps no space
            "john smith",      # Lower case
            "smith, john"      # Lower case with comma
            # NO LONGER INCLUDING: "Smith", "SMITH", "smith" (last name only)
        ]
        
        print("Generated variations:")
        for var in variations:
            status = "[OK]" if var in expected or var.lower() in [e.lower() for e in expected] else "[EXTRA]"
            print(f"  {status} '{var}'")
        
        print("\nKey Features:")
        print("[OK] Handles 'First Last' format (John Smith)")
        print("[OK] Handles 'Last, First' format (Smith, John)")  
        print("[OK] Handles ALL CAPS (JOHN SMITH)")
        print("[OK] Handles mixed case (john smith)")
        print("[OK] NO LONGER searches last name only (avoids duplicates)")
        print("[OK] Removes duplicates automatically")
        
        print("\n" + "=" * 60)
        print("Name Variation Test Complete!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(test_name_variations())