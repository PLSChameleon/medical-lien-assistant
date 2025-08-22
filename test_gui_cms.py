#!/usr/bin/env python3
"""Test the GUI's CMS processing fix"""

import sys
import os
import asyncio

# Add ai_assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

from services.cms_integration import (
    log_session_email,
    get_session_stats,
    process_session_cms_notes
)

async def test_gui_cms_processing():
    """Test that the GUI's CMS processing works correctly"""
    
    print("=" * 60)
    print("TESTING GUI CMS PROCESSING")
    print("=" * 60)
    
    # Add a test email to the pending queue
    print("\n1. Adding test email to pending queue...")
    log_session_email("999999", "test@example.com", "TEST_EMAIL")
    
    # Check stats
    stats = get_session_stats()
    print(f"   Pending emails: {stats['pending_count']}")
    
    if stats['pending_count'] > 0:
        print("\n2. Processing CMS notes (as GUI would)...")
        print("   Note: Browser will open, dismiss certificate popup if it appears")
        
        # Process exactly as the GUI does
        success = await process_session_cms_notes()
        
        if success:
            print("\n3. Checking results...")
            updated_stats = get_session_stats()
            print(f"   Pending: {updated_stats['pending_count']}")
            print(f"   Processed: {updated_stats['processed_count']}")
            print(f"   Notes added: {updated_stats['notes_added_count']}")
            
            print("\n[SUCCESS] CMS processing works correctly!")
        else:
            print("\n[FAILED] CMS processing failed")
    else:
        print("\n[INFO] No pending emails to process")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_gui_cms_processing())