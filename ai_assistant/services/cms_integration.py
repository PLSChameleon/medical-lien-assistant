#!/usr/bin/env python3
"""
CMS Integration Service - Adds notes to CMS system when emails are sent
"""

import logging
import os
import time
import re
from datetime import datetime, timedelta
import asyncio
from playwright.async_api import async_playwright
from config import Config

logger = logging.getLogger(__name__)

# Session logging paths - these persist across program restarts
SESSION_EMAILS_PENDING_LOG = "session_emails_pending.log"  # Emails waiting for CMS notes
SESSION_EMAILS_PROCESSED_LOG = "session_emails_processed.log"  # Emails with CMS notes added
SESSION_CMS_NOTES_LOG = "session_cms_notes.log"  # All CMS notes added

def log_session_email(pid, recipient_email, email_type="FOLLOW-UP"):
    """Log email sent - goes to PENDING queue until CMS note is added"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] PID: {pid} | Email Type: {email_type} | Sent to: {recipient_email}\n"
        
        # Add to pending queue (these need CMS notes)
        with open(SESSION_EMAILS_PENDING_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.flush()  # Force write to disk
        
        logger.info(f"📧 Email logged to pending queue: PID {pid} → {recipient_email}")
        
        # Verify it was written
        if os.path.exists(SESSION_EMAILS_PENDING_LOG):
            size = os.path.getsize(SESSION_EMAILS_PENDING_LOG)
            logger.info(f"[DEBUG] Pending log file size after write: {size} bytes")
        
    except Exception as e:
        logger.error(f"❌ Failed to log session email: {e}")
        import traceback
        traceback.print_exc()

def log_acknowledgment_note(pid, note_text):
    """Log acknowledgment note - goes to PENDING queue until CMS note is added"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Store acknowledgment notes with special type and the note text as the recipient field
        log_entry = f"[{timestamp}] PID: {pid} | Email Type: ACKNOWLEDGMENT | Sent to: {note_text}\n"
        
        # Add to pending queue (these need CMS notes)
        with open(SESSION_EMAILS_PENDING_LOG, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.flush()  # Force write to disk
        
        logger.info(f"✅ Acknowledgment note logged to pending queue: PID {pid}")
        
        # Verify it was written
        if os.path.exists(SESSION_EMAILS_PENDING_LOG):
            size = os.path.getsize(SESSION_EMAILS_PENDING_LOG)
            logger.info(f"[DEBUG] Pending log file size after write: {size} bytes")
        
    except Exception as e:
        logger.error(f"❌ Failed to log acknowledgment note: {e}")
        import traceback
        traceback.print_exc()

def log_cms_note_added(pid, recipient_email, email_type="FOLLOW-UP"):
    """Log CMS note added and move email from pending to processed"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add to CMS notes log
    cms_log_entry = f"[{timestamp}] CMS NOTE ADDED - PID: {pid} | Email Type: {email_type} | Sent to: {recipient_email}\n"
    with open(SESSION_CMS_NOTES_LOG, "a", encoding="utf-8") as f:
        f.write(cms_log_entry)
    
    # Move from pending to processed
    move_email_to_processed(pid, recipient_email, email_type, timestamp)
    
    logger.info(f"✅ CMS note added and email moved to processed: PID {pid} → {recipient_email}")

def move_email_to_processed(pid, recipient_email, email_type, timestamp):
    """Move an email from pending to processed queue"""
    # Read all pending emails
    pending_emails = []
    if os.path.exists(SESSION_EMAILS_PENDING_LOG):
        with open(SESSION_EMAILS_PENDING_LOG, "r", encoding="utf-8") as f:
            pending_emails = f.readlines()
    
    # Find and remove the processed email from pending
    remaining_emails = []
    processed_entry = None
    
    for line in pending_emails:
        if f"PID: {pid}" in line and recipient_email in line:
            # Found the email to move - save it for processed log
            processed_entry = f"[{timestamp}] PROCESSED - PID: {pid} | Email Type: {email_type} | Sent to: {recipient_email}\n"
        else:
            # Keep this email in pending
            remaining_emails.append(line)
    
    # Rewrite pending log without the processed email
    with open(SESSION_EMAILS_PENDING_LOG, "w", encoding="utf-8") as f:
        f.writelines(remaining_emails)
    
    # Add to processed log
    if processed_entry:
        with open(SESSION_EMAILS_PROCESSED_LOG, "a", encoding="utf-8") as f:
            f.write(processed_entry)

def load_pending_emails():
    """Load emails that still need CMS notes added"""
    if not os.path.exists(SESSION_EMAILS_PENDING_LOG):
        return {}
    
    pid_email_map = {}
    pattern = r"PID:\s*(\d+)\s*\|\s*Email Type:\s*([^|]+)\s*\|\s*Sent to:\s*(.+)"
    
    with open(SESSION_EMAILS_PENDING_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            match = re.search(pattern, line)
            if match:
                pid = match.group(1).strip()
                email_type = match.group(2).strip()
                email = match.group(3).strip()
                pid_email_map[pid] = {
                    'email': email,
                    'email_type': email_type
                }
    
    return pid_email_map

def get_session_stats():
    """Get statistics about emails and CMS notes"""
    pending_count = 0
    processed_count = 0
    notes_added_count = 0
    
    # Count pending emails
    if os.path.exists(SESSION_EMAILS_PENDING_LOG):
        with open(SESSION_EMAILS_PENDING_LOG, "r", encoding="utf-8") as f:
            pending_count = len([line for line in f if "PID:" in line])
    
    # Count processed emails  
    if os.path.exists(SESSION_EMAILS_PROCESSED_LOG):
        with open(SESSION_EMAILS_PROCESSED_LOG, "r", encoding="utf-8") as f:
            processed_count = len([line for line in f if "PROCESSED" in line])
    
    # Count CMS notes added
    if os.path.exists(SESSION_CMS_NOTES_LOG):
        with open(SESSION_CMS_NOTES_LOG, "r", encoding="utf-8") as f:
            notes_added_count = len([line for line in f if "CMS NOTE ADDED" in line])
    
    total_emails = pending_count + processed_count
    
    # Return a dictionary instead of tuple for GUI compatibility
    return {
        'pending_count': pending_count,
        'processed_count': processed_count,
        'total_emails': total_emails,
        'notes_added_count': notes_added_count
    }

def clear_session_logs():
    """Clear all session logs - use with caution!"""
    for log_file in [SESSION_EMAILS_PENDING_LOG, SESSION_EMAILS_PROCESSED_LOG, SESSION_CMS_NOTES_LOG]:
        if os.path.exists(log_file):
            os.remove(log_file)
    logger.info("🗑️ All session logs cleared")

class CMSIntegrationService:
    """Service to add notes to CMS system when emails are sent"""
    
    # Class-level persistent browser session (shared across all instances)
    _persistent_browser = None
    _persistent_context = None  
    _persistent_page = None
    _persistent_logged_in = False
    _persistent_playwright = None
    
    def __init__(self, use_persistent_session=True):
        # CMS credentials - should be in config.env
        self.username = os.getenv("CMS_USERNAME")
        self.password = os.getenv("CMS_PASSWORD")
        self.login_url = "https://cms.transconfinancialinc.com/CMS"
        
        # Note configuration - default to COR for emails, but can be overridden
        self.default_note_type = "COR"  # Correspondence for emails
        self.next_contact_date = (datetime.today() + timedelta(days=30)).strftime("%m/%d/%Y")
        
        # Session management
        self.use_persistent_session = use_persistent_session
        
        # Browser and page objects (for non-persistent sessions)
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False
    
    async def _handle_certificate_popup(self):
        """Comprehensive certificate popup handling with multiple approaches"""
        logger.info("Starting comprehensive certificate popup handling...")
        
        # Wait for page to fully load
        await asyncio.sleep(3)
        
        # Approach 1: Multiple keyboard combinations
        logger.info("Approach 1: Keyboard combinations...")
        try:
            # Try different key combinations
            key_combinations = [
                'Escape', 'Escape', 'Escape',  # Multiple escapes
                'Tab', 'Tab', 'Enter',        # Tab to Cancel button, then Enter
                'Alt+F4',                     # Close dialog
                'Control+w',                  # Close tab
                'Enter',                      # Confirm/OK
                'Space',                      # Spacebar
            ]
            
            for key in key_combinations:
                try:
                    await self.page.keyboard.press(key)
                    await asyncio.sleep(0.2)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Keyboard approach failed: {e}")
        
        # Approach 2: Look for Cancel/OK buttons and click them
        logger.info("Approach 2: Looking for dialog buttons...")
        try:
            # Common button selectors for certificate dialogs
            button_selectors = [
                'button:has-text("Cancel")',
                'button:has-text("OK")', 
                'button:has-text("Close")',
                'input[value="Cancel"]',
                'input[value="OK"]',
                '[data-testid="cancel"]',
                '[data-testid="ok"]',
                '.modal-footer button',
                '.dialog-buttons button',
                'button[type="button"]'
            ]
            
            for selector in button_selectors:
                try:
                    # Try to find and click the button
                    button = self.page.locator(selector).first
                    if await button.is_visible(timeout=1000):
                        logger.info(f"Found button with selector: {selector}")
                        await button.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Button clicking approach failed: {e}")
            
        # Approach 3: Try to interact with any visible modal/dialog
        logger.info("Approach 3: Generic modal interaction...")
        try:
            # Look for common modal/dialog containers
            modal_selectors = [
                '.modal', '.dialog', '.popup', '.overlay',
                '[role="dialog"]', '[role="alertdialog"]',
                '.certificate-dialog', '.cert-dialog'
            ]
            
            for selector in modal_selectors:
                try:
                    modal = self.page.locator(selector).first
                    if await modal.is_visible(timeout=1000):
                        logger.info(f"Found modal with selector: {selector}")
                        # Try clicking outside the modal to dismiss
                        await self.page.click('body', position={'x': 10, 'y': 10})
                        await asyncio.sleep(0.5)
                        # Also try pressing Escape on the modal
                        await modal.press('Escape')
                        await asyncio.sleep(0.5)
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Modal interaction failed: {e}")
        
        # Approach 4: Check if login form is now accessible
        logger.info("Approach 4: Checking login form accessibility...")
        try:
            username_field = self.page.locator('input[name="UserName"]')
            await username_field.wait_for(timeout=5000)
            logger.info("✅ Username field is accessible - certificate popup handled successfully!")
            return True
            
        except Exception as e:
            logger.warning("❌ Username field still not accessible")
            
        # Approach 5: Manual intervention fallback
        logger.info("Approach 5: Manual intervention fallback...")
        logger.warning("⚠️  CERTIFICATE POPUP MAY STILL BE PRESENT")
        logger.info("👤 Please manually:")
        logger.info("   1. Look for a certificate selection popup")
        logger.info("   2. Click 'Cancel' or press 'Escape'")
        logger.info("   3. Script will continue in 10 seconds...")
        
        # Give user time to manually dismiss popup
        for i in range(10, 0, -1):
            logger.info(f"   Continuing in {i} seconds...")
            await asyncio.sleep(1)
            
            # Check every second if username field becomes available
            try:
                username_field = self.page.locator('input[name="UserName"]')
                if await username_field.is_visible(timeout=100):
                    logger.info("✅ Username field accessible - popup dismissed!")
                    return True
            except:
                pass
        
        logger.info("Proceeding with login attempt...")
        return False
    
    async def _handle_client_certificate_dialog(self):
        """Handle browser-native client certificate selection dialog during navigation"""
        logger.info("🔐 Monitoring for certificate dialog during navigation...")
        
        # Monitor for certificate dialog during navigation period
        max_wait_time = 20  # seconds to monitor
        check_interval = 0.5  # check every 500ms
        
        for attempt in range(int(max_wait_time / check_interval)):
            # Check if page has loaded (no dialog)
            try:
                username_field = self.page.locator('input[name="UserName"]')
                if await username_field.is_visible(timeout=100):
                    logger.info("✅ No certificate dialog - login form loaded successfully")
                    return True
            except:
                pass  # Page not loaded yet, continue monitoring
            
            # If we've been waiting a while, assume dialog appeared
            if attempt > 4:  # After 2 seconds, assume dialog is present
                logger.info("🔒 Certificate dialog likely present - attempting dismissal...")
                break
                
            await asyncio.sleep(check_interval)
        
        # This is a browser-native dialog, try specific keyboard sequences
        keyboard_sequences = [
            # Sequence 1: Tab to Cancel button, then Enter
            {
                'name': 'Tab to Cancel + Enter',
                'keys': ['Tab', 'Tab', 'Enter'],
                'delays': [0.3, 0.3, 0.2]
            },
            # Sequence 2: Just Escape
            {
                'name': 'Escape key',
                'keys': ['Escape'],
                'delays': [0.5]
            },
            # Sequence 3: Multiple Escapes
            {
                'name': 'Multiple Escapes', 
                'keys': ['Escape', 'Escape', 'Escape'],
                'delays': [0.2, 0.2, 0.2]
            },
            # Sequence 4: Alt+F4 to close dialog
            {
                'name': 'Alt+F4 close',
                'keys': ['Alt+F4'],
                'delays': [0.5]
            }
        ]
        
        # Try keyboard sequences more aggressively during navigation
        for i, sequence in enumerate(keyboard_sequences, 1):
            logger.info(f"🎹 Attempt {i}: {sequence['name']}")
            try:
                # Send keyboard sequence
                for key, delay in zip(sequence['keys'], sequence['delays']):
                    await self.page.keyboard.press(key)
                    await asyncio.sleep(delay)
                
                # Check multiple times if dialog was dismissed (navigation may be slow)
                for check in range(3):
                    await asyncio.sleep(0.5)
                    try:
                        username_field = self.page.locator('input[name="UserName"]')
                        if await username_field.is_visible(timeout=500):
                            logger.info(f"✅ Certificate dialog dismissed with {sequence['name']}!")
                            return True
                    except:
                        continue
                        
                logger.info(f"❌ {sequence['name']} didn't work")
                    
            except Exception as e:
                logger.debug(f"Sequence {i} failed: {e}")
        
        # Additional aggressive monitoring period
        logger.info("🔄 Additional monitoring for dialog dismissal...")
        for extra_attempt in range(10):  # 5 more seconds
            try:
                username_field = self.page.locator('input[name="UserName"]')
                if await username_field.is_visible(timeout=100):
                    logger.info("✅ Certificate dialog dismissed during extended monitoring!")
                    return True
            except:
                pass
            await asyncio.sleep(0.5)
        
        # Manual intervention with specific instructions for this dialog
        logger.warning("🚨 CLIENT CERTIFICATE DIALOG STILL PRESENT")
        logger.info("👆 PLEASE CLICK THE 'CANCEL' BUTTON")
        logger.info("   (It's the white button on the right side of the dialog)")
        logger.info("   Or press Escape key")
        logger.info("")
        
        # Wait with countdown, checking every second
        for countdown in range(15, 0, -1):
            logger.info(f"⏳ Waiting for manual action... {countdown} seconds left")
            await asyncio.sleep(1)
            
            # Check if dialog dismissed
            try:
                username_field = self.page.locator('input[name="UserName"]')
                if await username_field.is_visible(timeout=300):
                    logger.info("✅ Certificate dialog dismissed manually!")
                    return True
            except:
                continue
        
        logger.warning("⚠️ Continuing despite certificate dialog presence")
        return False
    
    @classmethod
    async def initialize_persistent_session(cls):
        """Initialize a persistent browser session that stays open between operations"""
        if cls._persistent_browser is not None:
            logger.info("♻️ Persistent CMS session already exists")
            return True
            
        try:
            logger.info("🚀 Initializing persistent CMS browser session...")
            logger.info("📋 Please manually dismiss the certificate popup when it appears!")
            
            cls._persistent_playwright = await async_playwright().start()
            cls._persistent_browser = await cls._persistent_playwright.chromium.launch(
                headless=False,  # Must be visible for manual certificate dismissal
                args=[
                    # Certificate and SSL handling
                    "--ignore-certificate-errors",
                    "--ignore-certificate-errors-spki-list",
                    "--ignore-ssl-errors",
                    "--ignore-certificate-errors-policy-installed",
                    "--disable-client-certificates", 
                    "--disable-client-side-phishing-detection",
                    "--allow-running-insecure-content",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    # Security and popup handling
                    "--disable-popup-blocking",
                    "--disable-default-apps", 
                    "--disable-extensions",
                    "--no-default-browser-check",
                    "--disable-translate",
                    # Performance and background features
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    # Additional certificate prevention flags
                    "--disable-features=AutofillEnableAccountWalletStorage",
                    "--disable-features=CertificateTransparencyComponentUpdater",
                    "--auto-select-desktop-capture-source=Entire screen"
                ]
            )
            
            cls._persistent_context = await cls._persistent_browser.new_context(
                ignore_https_errors=True,
                accept_downloads=True,
                extra_http_headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                # Client certificate handling - try to avoid the dialog
                bypass_csp=True,
                java_script_enabled=True
            )
            
            cls._persistent_page = await cls._persistent_context.new_page()
            
            # Dismiss any certificate dialogs automatically
            cls._persistent_page.on("dialog", lambda dialog: dialog.dismiss())
            
            # Navigate to CMS login page
            logger.info("🌐 Navigating to CMS login page...")
            logger.warning("⚠️  CERTIFICATE POPUP WILL APPEAR - PLEASE CLICK 'CANCEL' MANUALLY")
            logger.info("    (This is a one-time setup - popup won't appear again)")
            
            await cls._persistent_page.goto("https://cms.transconfinancialinc.com/CMS", timeout=120000)
            
            # Wait for user to manually dismiss certificate popup and login form to appear
            logger.info("⏳ Waiting for certificate popup dismissal and login form...")
            username_field = cls._persistent_page.locator('input[name="UserName"]')
            await username_field.wait_for(timeout=120000)  # 2 minutes for user action
            
            # Perform login
            logger.info("🔐 Logging into CMS...")
            cms_username = os.getenv("CMS_USERNAME")
            cms_password = os.getenv("CMS_PASSWORD")
            
            if not cms_username or not cms_password:
                logger.error("CMS credentials not configured. Please set CMS_USERNAME and CMS_PASSWORD in config.env")
                raise ValueError("CMS credentials not configured")
            
            await cls._persistent_page.fill('input[name="UserName"]', cms_username)
            await cls._persistent_page.fill('input[name="Password"]', cms_password)
            await cls._persistent_page.click('button[type="submit"]')
            await cls._persistent_page.wait_for_load_state("networkidle", timeout=60000)
            
            # Navigate to Collectors screen
            await cls._persistent_page.click("text=View")
            await cls._persistent_page.click("text=Collectors")
            await cls._persistent_page.wait_for_url("**/CMS/Collecter/AddCollecter", timeout=60000)
            
            cls._persistent_logged_in = True
            logger.info("✅ Persistent CMS session initialized and logged in!")
            logger.info("🎉 Browser will stay open - no more certificate popups!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize persistent session: {e}")
            await cls.cleanup_persistent_session()
            return False
    
    @classmethod
    async def cleanup_persistent_session(cls):
        """Clean up the persistent browser session"""
        try:
            if cls._persistent_browser:
                await cls._persistent_browser.close()
                logger.info("🗑️ Persistent CMS browser session closed")
        except Exception as e:
            logger.error(f"Error closing persistent session: {e}")
        finally:
            cls._persistent_browser = None
            cls._persistent_context = None
            cls._persistent_page = None
            cls._persistent_logged_in = False
            if cls._persistent_playwright:
                try:
                    await cls._persistent_playwright.stop()
                except:
                    pass
            cls._persistent_playwright = None
    
    @classmethod
    async def is_persistent_session_healthy(cls):
        """Simplified check: can we use the search field?"""
        logger.info("🔍 Quick health check - testing search field...")
        
        try:
            # Do we have the basic objects?
            if not cls._persistent_page or not cls._persistent_logged_in:
                logger.warning("❌ No persistent session available")
                return False
            
            # Quick test: can we find and count the search field?
            try:
                search_field = cls._persistent_page.locator('input#txtSearch')
                element_count = await search_field.count()
                
                if element_count > 0:
                    logger.info("✅ Search field found - persistent session is healthy")
                    return True
                else:
                    logger.warning("❌ Search field not found - session unhealthy")
                    return False
                    
            except Exception as e:
                logger.warning(f"❌ Cannot access search field: {e}")
                
                # If connection is corrupted, clean up
                if "'NoneType' object has no attribute 'send'" in str(e):
                    logger.warning("   Browser connection corrupted - cleaning up session")
                    try:
                        await cls.cleanup_persistent_session()
                    except:
                        pass  # Ignore cleanup errors
                
                return False
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    async def start_session(self):
        """Start browser session and log into CMS (or use persistent session)"""
        try:
            # Check if we should use persistent session
            if self.use_persistent_session:
                # First check if persistent session exists and is healthy
                if self._persistent_page and self._persistent_logged_in:
                    # Perform health check to ensure connection is still valid
                    logger.info("🔍 Checking persistent CMS session health...")
                    is_healthy = await self.is_persistent_session_healthy()
                    
                    if is_healthy:
                        logger.info("✅ Using existing healthy persistent CMS session")
                        self.browser = self._persistent_browser
                        self.context = self._persistent_context
                        self.page = self._persistent_page
                        self.logged_in = self._persistent_logged_in
                        return
                    else:
                        logger.warning("❌ Persistent session is unhealthy - needs reinitialization")
                        logger.info("💡 Please run 'init cms' again to create a new session")
                        raise Exception("Persistent CMS session is corrupted - please reinitialize with 'init cms'")
                else:
                    logger.warning("❌ No persistent session available")
                    logger.info("💡 You need to run 'init cms' first")
                    raise Exception("No persistent CMS session - please run 'init cms' first")
            
            logger.info("Starting new CMS session...")
            
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=False,  # Set to True for production
                args=[
                    # Certificate and SSL handling
                    "--ignore-certificate-errors",
                    "--ignore-certificate-errors-spki-list",
                    "--ignore-ssl-errors",
                    "--ignore-certificate-errors-policy-installed",
                    "--disable-client-certificates", 
                    "--disable-client-side-phishing-detection",
                    "--allow-running-insecure-content",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    # Security and popup handling
                    "--disable-popup-blocking",
                    "--disable-default-apps", 
                    "--disable-extensions",
                    "--no-default-browser-check",
                    "--disable-translate",
                    # Performance and background features
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    # Additional certificate prevention flags
                    "--disable-features=AutofillEnableAccountWalletStorage",
                    "--disable-features=CertificateTransparencyComponentUpdater",
                    "--auto-select-desktop-capture-source=Entire screen"
                ]
            )
            
            self.context = await self.browser.new_context(
                ignore_https_errors=True,
                accept_downloads=True,
                extra_http_headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                # Client certificate handling - try to avoid the dialog
                bypass_csp=True,
                java_script_enabled=True
            )
            
            self.page = await self.context.new_page()
            
            # Dismiss any certificate dialogs automatically
            self.page.on("dialog", lambda dialog: dialog.dismiss())
            
            # Log into CMS with concurrent certificate dialog handling
            logger.info("Logging into CMS...")
            
            # Start page navigation and certificate dialog handling concurrently
            # Certificate dialog appears DURING navigation, not after
            async def navigate_to_cms():
                await self.page.goto(self.login_url, timeout=60000)
                
            async def handle_cert_dialog_during_navigation():
                # Wait a moment for navigation to start
                await asyncio.sleep(0.5)
                # Handle certificate dialog that appears during navigation
                await self._handle_client_certificate_dialog()
            
            # Run navigation and certificate handling concurrently
            logger.info("🚀 Starting concurrent navigation and certificate handling...")
            await asyncio.gather(
                navigate_to_cms(),
                handle_cert_dialog_during_navigation()
            )
                
            await self.page.fill('input[name="UserName"]', self.username)
            await self.page.fill('input[name="Password"]', self.password)
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_load_state("networkidle", timeout=60000)
            
            # Go to Collectors screen
            await self.page.click("text=View")
            await self.page.click("text=Collectors")
            await self.page.wait_for_url("**/CMS/Collecter/AddCollecter", timeout=60000)
            
            self.logged_in = True
            logger.info("✅ CMS session started and logged in")
            
        except Exception as e:
            logger.error(f"Error starting CMS session: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Close browser session"""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("CMS browser session closed")
        except Exception as e:
            logger.error(f"Error closing CMS session: {e}")
        finally:
            self.browser = None
            self.context = None  
            self.page = None
            self.logged_in = False
    
    async def add_note(self, cms_number, note_text, note_type=None):
        """Add a note to a specific case in CMS
        
        Args:
            cms_number: The CMS/PID number for the case
            note_text: The text of the note to add
            note_type: The note type code (e.g., "COR", "NA"). If None, uses default
        """
        if not self.logged_in:
            raise Exception("CMS session not started. Call start_session() first.")
        
        # Use provided note type or default
        note_type_value = note_type if note_type else self.default_note_type
        
        try:
            logger.info(f"Adding note to CMS case {cms_number}")
            
            # Check if page object is valid before using it
            logger.info(f"Page object exists: {self.page is not None}")
            if self.page is None:
                raise Exception("Page object is None - session corrupted")
            
            # Try to get URL to test if connection works
            try:
                current_url = self.page.url
                logger.info(f"Current URL: {current_url}")
            except Exception as url_error:
                logger.error(f"Cannot access page URL: {url_error}")
                raise Exception(f"Page connection broken: {url_error}")
            
            # Ensure we're on the correct page
            if "AddCollecter" not in current_url:
                logger.info("Navigating to Collectors page...")
                await self.page.goto("https://cms.transconfinancialinc.com/CMS/Collecter/AddCollecter", timeout=30000)
                await asyncio.sleep(2)
            
            # Search for the CMS number (PID) - try multiple methods
            logger.info(f"Attempting to fill search field with: {cms_number}")
            
            search_filled = False
            
            # Method 1: Try using fill() directly
            try:
                logger.info("Method 1: Using fill() on search field...")
                await self.page.fill('input#txtSearch', str(cms_number))
                await asyncio.sleep(0.5)
                search_filled = True
            except Exception as e1:
                logger.warning(f"Method 1 failed: {e1}")
                
                # Method 2: Try clicking then typing
                try:
                    logger.info("Method 2: Click and type...")
                    await self.page.click('input#txtSearch')
                    await asyncio.sleep(0.5)
                    await self.page.keyboard.press('Control+a')
                    await self.page.keyboard.type(str(cms_number))
                    await asyncio.sleep(0.5)
                    search_filled = True
                except Exception as e2:
                    logger.warning(f"Method 2 failed: {e2}")
                    
                    # Method 3: Try using locator
                    try:
                        logger.info("Method 3: Using locator...")
                        search_field = self.page.locator('input#txtSearch')
                        await search_field.fill(str(cms_number))
                        await asyncio.sleep(0.5)
                        search_filled = True
                    except Exception as e3:
                        logger.error(f"Method 3 failed: {e3}")
                        raise Exception(f"All search field methods failed. Last error: {e3}")
            
            logger.info("Search field filled, pressing Enter...")
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(2)
            
            # Click "Add" button to add note
            await self.page.click("button:has-text('Add')")
            await asyncio.sleep(1)
            
            # Fill the note form
            await self.page.select_option("#NoteType", note_type_value)
            await self.page.fill("#AddNote", note_text)
            await self.page.fill("#NextCntDate", self.next_contact_date)
            
            # Submit note and update case
            await self.page.click("#btnAddNote")
            await asyncio.sleep(1)
            await self.page.click("#btnUpdateCase")
            
            logger.info(f"✅ Note added to CMS case {cms_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding note to CMS case {cms_number}: {e}")
            return False
    
    async def add_follow_up_note(self, cms_number, recipient_email):
        """Add a follow-up email note"""
        note_text = f"FOLLOW UP EMAIL SENT TO {recipient_email.upper()}"
        return await self.add_note(cms_number, note_text, note_type="COR")
    
    async def add_status_request_note(self, cms_number, recipient_email):
        """Add a status request email note"""
        note_text = f"STATUS REQUEST SENT TO {recipient_email.upper()}"
        return await self.add_note(cms_number, note_text, note_type="COR")
    
    async def add_general_email_note(self, cms_number, recipient_email, email_type="EMAIL"):
        """Add a general email note"""
        note_text = f"{email_type.upper()} SENT TO {recipient_email.upper()}"
        return await self.add_note(cms_number, note_text, note_type="COR")
    
    async def add_acknowledgment_note(self, cms_number, note_text):
        """Add an acknowledgment note with 'None' note type"""
        # Use "NA" for None note type as per dropdown options
        return await self.add_note(cms_number, note_text, note_type="NA")
    
    async def add_test_email_note(self, cms_number, recipient_info, email_type="test_bulk_status_request"):
        """Add a test email note with clear TEST MODE indication"""
        # recipient_info contains the test mode details
        if "TEST MODE" in recipient_info:
            # Format: "TEST MODE - Email sent to test@email.com (intended for attorney@firm.com)"
            note_text = f"(TEST MODE) EMAIL SENT TO {recipient_info}"
        else:
            # Fallback format for test emails
            note_text = f"(TEST MODE) {email_type.replace('test_', '').replace('_', ' ').upper()} - {recipient_info.upper()}"
        
        return await self.add_note(cms_number, note_text)

# Convenience functions for one-off notes (now just logs for batch processing)
async def add_cms_note_for_email(case_info, email_type, recipient_email):
    """
    Log email for later batch CMS note processing
    
    Args:
        case_info (dict): Case information including CMS number (PID)
        email_type (str): 'follow_up', 'status_request', or 'general'
        recipient_email (str): Email address the email was sent to
    """
    # DEBUG: Log what we received
    logger.info(f"[DEBUG] add_cms_note_for_email called with case_info keys: {case_info.keys() if isinstance(case_info, dict) else 'Not a dict'}")
    if isinstance(case_info, dict):
        logger.info(f"[DEBUG] CMS field: {case_info.get('CMS')}, PV field: {case_info.get('PV')}")
    
    # Try both uppercase and lowercase versions since different parts of the code use different cases
    cms_number = case_info.get("CMS") or case_info.get("cms")
    if not cms_number:
        # Also check if PID is stored in different field names
        cms_number = case_info.get("PID") or case_info.get("pid")
    
    if not cms_number:
        # Only warn if we also can't find a PV number (might be a real issue)
        pv = case_info.get('PV') or case_info.get('pv')
        if pv:
            logger.warning(f"No CMS/PID number found for case PV {pv}")
        else:
            logger.warning(f"No CMS/PID number found for unknown case")
        return False
    
    # Log this email for batch processing later
    log_session_email(cms_number, recipient_email, email_type)
    
    logger.info(f"📧 Email logged for batch CMS processing: PID {cms_number}")
    logger.info(f"⚠️  REMINDER: Run 'add session cms notes' command before closing the program!")
    
    return True

# Batch function to process all session emails
async def process_session_cms_notes():
    """
    Process all PENDING session emails and add CMS notes
    Creates a new browser session in the same process for reliability
    Emails are automatically moved from pending to processed queue
    """
    pending_emails = load_pending_emails()
    
    if not pending_emails:
        logger.info("📭 No pending emails found to process")
        return True
    
    logger.info(f"🔄 Processing {len(pending_emails)} pending emails for CMS notes...")
    
    # Always use non-persistent session for reliability (creates new browser in same process)
    cms_service = CMSIntegrationService(use_persistent_session=False)
    success_count = 0
    fail_count = 0
    
    try:
        # Start a fresh browser session in this process
        logger.info("🌐 Starting new CMS browser session...")
        await cms_service.start_session()
        logger.info("✅ CMS session started successfully")
        
        for pid, email_info in pending_emails.items():
            email = email_info['email']
            email_type = email_info['email_type']
            
            logger.info(f"🔄 Processing PID {pid} → {email}")
            
            try:
                if email_type.lower() == "follow-up":
                    success = await cms_service.add_follow_up_note(pid, email)
                elif email_type.lower() == "status_request":
                    success = await cms_service.add_status_request_note(pid, email)
                elif email_type.lower() == "acknowledgment":
                    # For acknowledgments, the 'email' field contains the note text
                    success = await cms_service.add_acknowledgment_note(pid, email)
                elif "test_" in email_type.lower():
                    # Handle test emails specially
                    success = await cms_service.add_test_email_note(pid, email, email_type)
                else:
                    success = await cms_service.add_general_email_note(pid, email, email_type)
                
                if success:
                    log_cms_note_added(pid, email, email_type)
                    success_count += 1
                    logger.info(f"✅ CMS note added for PID {pid}")
                else:
                    fail_count += 1
                    logger.error(f"❌ Failed to add CMS note for PID {pid}")
                
                # Small delay between notes
                await asyncio.sleep(1)
                
            except Exception as e:
                fail_count += 1
                logger.error(f"❌ Error processing PID {pid}: {e}")
        
        logger.info(f"🎉 Batch processing complete: {success_count} success, {fail_count} failed")
        return fail_count == 0
        
    except Exception as e:
        logger.error(f"❌ Batch processing failed: {e}")
        return False
        
    finally:
        logger.info("🗑️ Cleaning up browser session...")
        await cms_service.cleanup()
        logger.info("✅ Browser session closed")

# Function to get session statistics
def show_session_status():
    """Show current session email and CMS note statistics with persistent state"""
    stats = get_session_stats()
    pending_count = stats['pending_count']
    processed_count = stats['processed_count']
    total_emails = stats['total_emails']
    notes_added_count = stats['notes_added_count']
    
    logger.info(f"📊 PERSISTENT SESSION STATUS:")
    logger.info(f"   📧 Total emails sent: {total_emails}")
    logger.info(f"   ⏳ Pending CMS notes: {pending_count}")
    logger.info(f"   ✅ Processed emails: {processed_count}")
    logger.info(f"   📝 Total CMS notes added: {notes_added_count}")
    
    if pending_count > 0:
        logger.info(f"   ⚠️  WARNING: {pending_count} emails still need CMS notes!")
        logger.info(f"   💡 Run 'add session cms notes' to process pending notes")
        logger.info(f"   🔄 These emails will persist even if program crashes")
    else:
        logger.info(f"   🎉 All emails have CMS notes added!")
    
    # Return the stats dictionary for consistency
    return stats