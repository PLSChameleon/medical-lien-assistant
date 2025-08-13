from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import time
import re
import os

# Your credentials
USERNAME = "Dean"
PASSWORD = "Dean3825"
LOGIN_URL = "https://cms.transconfinancialinc.com/CMS"

# Note config
NOTE_TYPE_VALUE = "COR"
NEXT_CONTACT_DATE = (datetime.today() + timedelta(days=30)).strftime("%m/%d/%Y")

# Load from log file
def load_pid_email_map(log_path):
    pid_email_map = {}
    pattern = r"PID:\s*(\d+)\s*\|\s*Sent to:\s*([^\|]+)"

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip bad entries
            if line.startswith("SKIPPED") or "UNKNOWN" in line.upper():
                continue

            match = re.search(pattern, line)
            if match:
                pid = match.group(1).strip()
                email = match.group(2).strip()
                pid_email_map[pid] = email

    return pid_email_map

# Load the correct log file
log_file = os.path.join(os.path.dirname(__file__), "sent_emails2.log")
pid_email_map = load_pid_email_map(log_file)

# Run automation
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--ignore-ssl-errors", 
            "--ignore-certificate-errors-spki-list",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-client-side-phishing-detection"
        ]
    )
    context = browser.new_context(
        ignore_https_errors=True,
        accept_downloads=True,
        # Handle client certificate requests automatically
        extra_http_headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    )
    page = context.new_page()
    
    # Dismiss any certificate dialogs automatically
    page.on("dialog", lambda dialog: dialog.dismiss())

    # Log into CMS
    page.goto(LOGIN_URL)
    page.fill('input[name="UserName"]', USERNAME)
    page.fill('input[name="Password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    print("✅ Logged in.")

    # Go to Collectors screen
    page.click("text=View")
    page.click("text=Collectors")
    page.wait_for_url("**/CMS/Collecter/AddCollecter")
    print("✅ Collectors page loaded.")

    # Loop through each PID/email
    for pid, email in pid_email_map.items():
        print(f"📁 Processing PID {pid}...")

        try:
            # Search for the PID
            page.fill('input#txtSearch', pid)
            page.keyboard.press('Enter')
            time.sleep(2)

            # Click "Add" button
            page.click("button:has-text('Add')")
            time.sleep(1)

            # Fill form
            page.select_option("#NoteType", NOTE_TYPE_VALUE)
            note = f"(TEST) AUTOMATED STATUS REQUEST SENT TO {email.upper()}"
            page.fill("#AddNote", note)
            page.fill("#NextCntDate", NEXT_CONTACT_DATE)

            # Submit note and update case
            page.click("#btnAddNote")
            time.sleep(1)
            page.click("#btnUpdateCase")

            print(f"✅ Note added and case updated for PID {pid}")

        except Exception as e:
            print(f"❌ Failed for PID {pid}: {e}")

    input("✅ All done! Press Enter to close browser...")
    browser.close()
