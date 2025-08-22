#!/usr/bin/env python3
"""
Script to initialize CMS session and process pending notes in a single process
This ensures the browser connection remains valid throughout the operation
"""

import asyncio
import logging
import sys
import os

# Add ai_assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

from services.cms_integration import (
    CMSIntegrationService, 
    load_pending_emails,
    log_cms_note_added,
    get_session_stats
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def process_all_cms_notes():
    """Initialize CMS and process all pending notes in the same process"""
    
    # Check for pending emails first
    pending_emails = load_pending_emails()
    
    if not pending_emails:
        logger.info("📭 No pending emails found to process")
        return True
    
    logger.info("=" * 60)
    logger.info(f"📧 Found {len(pending_emails)} pending emails to process")
    logger.info("=" * 60)
    
    # Show what we're going to process
    for pid, email_info in list(pending_emails.items())[:5]:
        logger.info(f"   • PID {pid} → {email_info['email']}")
    if len(pending_emails) > 5:
        logger.info(f"   ... and {len(pending_emails) - 5} more")
    
    logger.info("")
    logger.info("🚀 Starting CMS session for processing...")
    logger.info("")
    logger.info("📋 IMPORTANT: When the browser opens:")
    logger.info("   1. A certificate popup MAY appear")
    logger.info("   2. If it does, click 'CANCEL' to dismiss it")
    logger.info("   3. The script will then log in automatically")
    logger.info("")
    logger.info("Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    # Create CMS service instance (non-persistent mode for reliability)
    cms_service = CMSIntegrationService(use_persistent_session=False)
    success_count = 0
    fail_count = 0
    
    try:
        # Start fresh browser session
        logger.info("\n🌐 Opening browser and logging into CMS...")
        await cms_service.start_session()
        logger.info("✅ Successfully logged into CMS")
        
        logger.info("\n" + "=" * 60)
        logger.info("🔄 PROCESSING CMS NOTES")
        logger.info("=" * 60)
        
        # Process each pending email
        for idx, (pid, email_info) in enumerate(pending_emails.items(), 1):
            email = email_info['email']
            email_type = email_info['email_type']
            
            logger.info(f"\n[{idx}/{len(pending_emails)}] Processing PID {pid} → {email}")
            
            try:
                # Add appropriate note type
                if email_type.lower() == "follow-up":
                    success = await cms_service.add_follow_up_note(pid, email)
                elif email_type.lower() == "status_request":
                    success = await cms_service.add_status_request_note(pid, email)
                elif "test_" in email_type.lower():
                    success = await cms_service.add_test_email_note(pid, email, email_type)
                else:
                    success = await cms_service.add_general_email_note(pid, email, email_type)
                
                if success:
                    log_cms_note_added(pid, email, email_type)
                    success_count += 1
                    logger.info(f"   ✅ CMS note added successfully")
                else:
                    fail_count += 1
                    logger.error(f"   ❌ Failed to add CMS note")
                
                # Small delay between notes to avoid overwhelming the system
                if idx < len(pending_emails):
                    await asyncio.sleep(1.5)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"   ❌ Error processing: {e}")
        
        # Show final results
        logger.info("\n" + "=" * 60)
        logger.info("📊 PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"   ✅ Successful: {success_count}")
        logger.info(f"   ❌ Failed: {fail_count}")
        logger.info(f"   📊 Total: {success_count + fail_count}")
        
        # Show updated session stats
        stats = get_session_stats()
        logger.info("\n📈 Updated Session Status:")
        logger.info(f"   📧 Total emails sent: {stats['total_emails']}")
        logger.info(f"   ⏳ Still pending: {stats['pending_count']}")
        logger.info(f"   ✅ Processed: {stats['processed_count']}")
        logger.info(f"   📝 CMS notes added: {stats['notes_added_count']}")
        
        return fail_count == 0
        
    except Exception as e:
        logger.error(f"\n❌ Fatal error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Always cleanup the browser session
        logger.info("\n🗑️ Closing browser session...")
        await cms_service.cleanup()
        logger.info("✅ Browser session closed")

if __name__ == "__main__":
    logger.info("CMS NOTES PROCESSOR")
    logger.info("=" * 60)
    
    success = asyncio.run(process_all_cms_notes())
    
    if success:
        logger.info("\n✅ All pending CMS notes processed successfully!")
    else:
        logger.info("\n⚠️ Some notes failed to process. Check the logs above.")
    
    sys.exit(0 if success else 1)