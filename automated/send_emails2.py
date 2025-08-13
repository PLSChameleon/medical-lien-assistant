import smtplib
from email.message import EmailMessage
import time
import re
import os

# Gmail credentials
GMAIL_ADDRESS = "deanh.transcon@gmail.com"
GMAIL_APP_PASSWORD = "zijc lday ypae jojw"

# Load blacklist
blacklist = set()
if os.path.exists("blacklist.txt"):
    with open("blacklist.txt", "r", encoding="utf-8") as f:
        blacklist = {line.strip().lower() for line in f if line.strip()}

# Validate email format
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Log failed emails
def log_failure(to_email, subject, error_msg):
    with open("failed_emails.log", "a", encoding="utf-8") as log:
        log.write(f"FAILED: {to_email} | Subject: {subject}\nReason: {error_msg}\n\n")

# Log blacklisted skips
def log_blacklist_skip(pid):
    with open("skipped_blacklist.log", "a", encoding="utf-8") as log:
        log.write(f"PID: {pid} | Email not Sent because attorney on blacklist\n")

# Log success to both main and backup files
def log_success(pid, to_email, subject):
    if not pid:
        print(f"⚠️  Cannot log success — PID missing for {to_email}")
        return

    log_line = f"PID: {pid} | Sent to: {to_email} | Subject: {subject}\n"

    for log_file in ["sent_emails.log", "sent_emails_backup.txt"]:
        try:
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(log_line)
                log.flush()
                os.fsync(log.fileno())
            print(f"📝 Logged to {log_file}: PID {pid}")
        except Exception as e:
            print(f"❌ Failed to write to {log_file} for PID {pid}: {e}")

# Load sent PIDs from log
sent_pids = set()
logged_pids = set()

if os.path.exists("sent_emails.log"):
    with open("sent_emails.log", "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(r"PID: (\d+)", line)
            if match:
                pid = match.group(1)
                sent_pids.add(pid)
                logged_pids.add(pid)

# Load generated emails
with open("generated_emails.txt", "r", encoding="utf-8") as f:
    all_emails = f.read().split("\n" + "-" * 60 + "\n\n")

# Process emails
for email_block in all_emails:
    if not email_block.strip():
        continue

    lines = email_block.strip().splitlines()
    to_line = next((line for line in lines if line.lower().startswith("to: ")), "")
    subject_line = next((line for line in lines if line.lower().startswith("subject: ")), "")

    to_email = to_line.replace("To:", "").strip()
    subject = subject_line.replace("Subject:", "").strip()
    body = "\n".join(lines[2:]).strip()

    # Extract PID using regex
    reference = ""
    for line in lines:
        match = re.search(r"reference\s*#[:\s]*([0-9]+)", line, re.IGNORECASE)
        if match:
            reference = match.group(1)
            break

    if not reference:
        print(f"⚠️  No PID found for email to {to_email} — skipping")
        continue

    if "unknown doi" in subject.lower():
        print(f"⚠️  Skipping PID {reference} due to UNKNOWN DOI")
        continue

    if to_email.lower() in blacklist:
        print(f"⛔ Skipping PID {reference} — blacklisted attorney ({to_email})")
        log_blacklist_skip(reference)
        continue

    if reference in sent_pids:
        print(f"⏭️  Skipping PID {reference} (already sent)")
        continue

    if not to_email or not is_valid_email(to_email):
        print(f"❌ Invalid or missing email: {to_email}")
        log_failure(to_email, subject, "Invalid or missing email address")
        continue

    # Prepare and send email
    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
            print(f"✅ Sent to {to_email}")
            log_success(reference, to_email, subject)
            sent_pids.add(reference)
    except Exception as e:
        print(f"❌ Failed to send to {to_email}: {e}")
        log_failure(to_email, subject, str(e))
        continue

    time.sleep(2)

# Final pass to backfill anything missed
for pid in sent_pids:
    if pid not in logged_pids:
        log_success(pid, "UNKNOWN", "Backfilled at end of script")
