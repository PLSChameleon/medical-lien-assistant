#!/usr/bin/env python3
"""Script to reinitialize the CMS persistent session"""

import asyncio
import logging
import sys
import os

# Add ai_assistant to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_assistant'))

from services.cms_integration import CMSIntegrationService

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def reinitialize_cms():
    """Reinitialize the CMS persistent session"""
    
    logger.info("=" * 60)
    logger.info("🔄 REINITIALIZING CMS PERSISTENT SESSION")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📋 IMPORTANT: When the browser opens:")
    logger.info("   1. A certificate popup will appear")
    logger.info("   2. Click 'CANCEL' to dismiss it")
    logger.info("   3. The script will then log in automatically")
    logger.info("")
    logger.info("Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    # Clean up any existing broken session first
    logger.info("\n🗑️ Cleaning up any existing session...")
    await CMSIntegrationService.cleanup_persistent_session()
    
    # Initialize new session
    logger.info("\n🚀 Initializing new persistent session...")
    success = await CMSIntegrationService.initialize_persistent_session()
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ CMS SESSION REINITIALIZED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("You can now:")
        logger.info("  - Process pending CMS notes")
        logger.info("  - Send new emails with automatic CMS integration")
        logger.info("")
        logger.info("The browser window will stay open for future operations.")
        return True
    else:
        logger.error("\n❌ Failed to reinitialize CMS session")
        logger.error("Please try again or check the logs for errors")
        return False

if __name__ == "__main__":
    success = asyncio.run(reinitialize_cms())
    sys.exit(0 if success else 1)