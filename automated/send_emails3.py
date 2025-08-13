import smtplib
from email.message import EmailMessage
import time
import re
import os

# Gmail credentials
GMAIL_ADDRESS = "deanh.transcon@gmail.com"
GMAIL_APP_PASSWORD = "zijc lday ypae jojw"

# Validate email format
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Log failed emails
def log_failure(to_email, subject, error_msg):
    for logfile in ["failed_emails.log"]:
        with open(logfile, "a", encoding="utf-8") as log:
            log.write(f"FAILED: {to_email} | Subject: {subject}\nReason: {error_msg}\n\n")
            log.flush()
            os.fsync(log.fileno())
        print(f"❌ Logged failure to {logfile}")

# Log successful sends to both logs
def log_success(pid, to_email, subject):
    if not pid:
        print(f"⚠️  Cannot log success — PID missing for {to_email}")
        return

    log_line = f"PID: {pid} | Sent to: {to_email} | Subject: {subject}\n"
    for logfile in ["sent_emails.log", "sent_emails_log.txt"]:
        try:
            with open(logfile, "a", encoding="utf-8") as log:
                log.write(log_line)
                log.flush()
                os.fsync(log.fileno())
            print(f"📝 Logged to {logfile}: PID {pid}")
        except Exception as e:
            print(f"❌ Failed to write to {logfile} for PID {pid}: {e}")

# Log skipped emails
def log_skipped(pid, to_email, reason):
    log_line = f"SKIPPED: PID {pid} | Email: {to_email} | Reason: {reason}\n"
    for logfile in ["sent_emails.log", "sent_emails_log.txt"]:
        try:
            with open(logfile, "a", encoding="utf-8") as log:
                log.write(log_line)
                log.flush()
                os.fsync(log.fileno())
            print(f"🚫 Logged skip to {logfile}: PID {pid}")
        except Exception as e:
            print(f"❌ Failed to write skipped log for PID {pid} in {logfile}: {e}")

# Load sent PIDs from sent_emails.log to prevent duplicates
sent_pids = set()
if os.path.exists("sent_emails.log"):
    with open("sent_emails.log", "r", encoding="utf-8") as f:
        for line in f:
            match = re.search(r"PID: (\d+)", line)
            if match:
                sent_pids.add(match.group(1))

# Load generated emails
with open("generated_emails.txt", "r", encoding="utf-8") as f:
    all_emails = f.read().split("\n" + "-" * 60 + "\n\n")

# Process each email block
for email_block in all_emails:
    if not email_block.strip():
        continue

    lines = email_block.strip().splitlines()
    to_line = next((line for line in lines if line.lower().startswith("to: ")), "")
    subject_line = next((line for line in lines if line.lower().startswith("subject: ")), "")

    to_email = to_line.replace("To:", "").strip()
    subject = subject_line.replace("Subject:", "").strip()
    body = "\n".join(lines[2:]).strip()

    # Extract PID (reference number)
    reference = ""
    for line in lines:
        match = re.search(r"reference\s*#[:\s]*([0-9]+)", line, re.IGNORECASE)
        if match:
            reference = match.group(1)
            break

    if not reference:
        print(f"⚠️  No PID found for email to {to_email} — skipping")
        continue

    if reference in sent_pids:
        print(f"⏭️  Skipping PID {reference} (already sent)")
        continue

    if "2099" in subject:
        print(f"⛔ Skipping PID {reference} due to 2099 DOI")
        log_skipped(reference, to_email, "Skipped due to 2099 DOI in subject")
        continue

    if "unknown doi" in subject.lower():
        print(f"⚠️  Skipping PID {reference} due to UNKNOWN DOI")
        log_skipped(reference, to_email, "Skipped due to UNKNOWN DOI")
        continue

    if not to_email or not is_valid_email(to_email):
        print(f"❌ Invalid or missing email: {to_email}")
        log_failure(to_email, subject, "Invalid or missing email address")
        continue

    # Prepare email
    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # Send email
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

# Final check to make sure all new ones get logged
for pid in sent_pids:
    # This only backfills any that somehow didn't make it into the logs
    with open("sent_emails.log", "r", encoding="utf-8") as f:
        if pid not in f.read():
            log_success(pid, "UNKNOWN", "Backfilled at end of script")
