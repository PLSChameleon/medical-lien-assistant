import pandas as pd
import smtplib
from email.message import EmailMessage
import json
import os
from datetime import datetime
import random
import re
import time

class BulkEmailManager:
    def __init__(self, test_mode=False, test_email="deanh.transcon@gmail.com"):
        self.test_mode = test_mode
        self.test_email = test_email
        self.gmail_address = "deanh.transcon@gmail.com"
        self.gmail_app_password = "zijc lday ypae jojw"
        
        self.sent_pids = self.load_sent_pids()
        self.email_queue = []
        self.categories = {}
        
        self.greetings = [
            "Hello Law Firm,", "Good day Law Firm,", "Greetings Law Firm,",
            "Hi Law Firm,", "Dear Law Firm,"
        ]
        
        self.status_requests = [
            "Has this case settled or is it still pending?",
            "Can you let me know the current status of this case?",
            "Do you happen to have an update on this case?",
            "Is this matter still open or has it been resolved?",
            "Could you please confirm whether the case is resolved or still pending?"
        ]
        
        self.followups = [
            "Let me know if you need bills or reports.",
            "If you need any reports or billing, just let me know.",
            "Feel free to reach out if any bills or documentation are needed.",
            "I'm happy to provide any necessary documents or reports you may need.",
            "We can send over any billing or medical records you might need."
        ]
    
    def load_sent_pids(self):
        sent_pids = set()
        if os.path.exists("sent_emails.log"):
            with open("sent_emails.log", "r", encoding="utf-8") as f:
                for line in f:
                    match = re.search(r"PID: (\d+)", line)
                    if match:
                        sent_pids.add(match.group(1))
        return sent_pids
    
    def load_cases(self, excel_file="cases.xlsx"):
        df = pd.read_excel(excel_file)
        return df
    
    def categorize_cases(self, df):
        categories = {
            "active_no_recent_contact": [],
            "active_recent_settlement": [],
            "active_by_firm": {},
            "active_missing_doi": [],
            "active_old_cases": []
        }
        
        for index, row in df.iterrows():
            if str(row.get("Case Status", "")).upper() != "ACTIVE":
                continue
                
            pid = str(row.get("PID", ""))
            if pid in self.sent_pids:
                continue
            
            firm_email = str(row.get("Attny Email", "") or "").strip()
            doi = str(row.get("DOI", "") or "").strip()
            
            case_data = {
                "index": index,
                "pid": pid,
                "name": str(row.get("PatientName", "") or "").strip(),
                "doi": doi,
                "firm_email": firm_email,
                "firm_name": str(row.get("Attny Name", "") or "").strip(),
                "last_contact": row.get("Last Contact", None),
                "case_status": str(row.get("Case Status", "")),
                "row": row
            }
            
            if "2099" in doi or not doi:
                categories["active_missing_doi"].append(case_data)
            
            if firm_email:
                if firm_email not in categories["active_by_firm"]:
                    categories["active_by_firm"][firm_email] = []
                categories["active_by_firm"][firm_email].append(case_data)
            
            if case_data.get("last_contact"):
                try:
                    last_contact = pd.to_datetime(case_data["last_contact"])
                    days_since = (datetime.now() - last_contact).days
                    if days_since > 60:
                        categories["active_no_recent_contact"].append(case_data)
                except:
                    pass
            
            if doi and doi != "2099":
                try:
                    doi_date = pd.to_datetime(doi.split()[0])
                    years_old = (datetime.now() - doi_date).days / 365
                    if years_old > 2:
                        categories["active_old_cases"].append(case_data)
                except:
                    pass
        
        self.categories = categories
        return categories
    
    def generate_consolidated_email(self, firm_email, cases):
        """Generate a single email containing multiple cases for a firm"""
        firm_name = cases[0]["firm_name"] if cases and cases[0].get("firm_name") else "Law Firm"
        
        greeting = random.choice(self.greetings)
        
        # Build case list
        case_lines = []
        missing_doi_cases = []
        normal_cases = []
        
        for case in cases:
            name = case["name"].title() if case["name"] else "UNKNOWN"
            doi = case["doi"].split()[0] if case["doi"] and case["doi"] != "2099" else ""
            pid = case["pid"]
            
            if "2099" in str(case["doi"]) or not case["doi"]:
                missing_doi_cases.append(f"• {name} - File #: {pid} (DOI: UNKNOWN)")
            else:
                normal_cases.append(f"• {name} - DOI: {doi} - File #: {pid}")
        
        # Build email body
        all_cases = normal_cases + missing_doi_cases
        cases_text = "\n".join(all_cases)
        
        status_line = random.choice(self.status_requests)
        followup_line = random.choice(self.followups)
        
        if missing_doi_cases:
            doi_request = "\n\nFor the cases marked with UNKNOWN DOI, could you please provide the accurate dates of loss?"
        else:
            doi_request = ""
        
        subject = f"ProHealth Advanced Imaging - {len(cases)} Case Status Inquiries"
        
        if self.test_mode:
            original_to = firm_email
            firm_email = self.test_email
            subject = f"[TEST MODE - Original To: {original_to}] {subject}"
        
        body = f"""To: {firm_email}
Subject: {subject}

{greeting}

In regards to ProHealth Advanced Imaging billing and liens for the following cases:

{cases_text}

{status_line} {followup_line}{doi_request}

Thank you."""
        
        # Create consolidated PID list for logging
        pid_list = ", ".join([case["pid"] for case in cases])
        
        return {
            "pid": pid_list,  # All PIDs for logging
            "to": firm_email,
            "subject": subject,
            "body": body,
            "name": f"{len(cases)} cases",
            "doi": "Multiple",
            "original_to": firm_name if self.test_mode else firm_email,
            "is_consolidated": True,
            "case_count": len(cases)
        }
    
    def generate_email(self, case_data):
        name = case_data["name"].title() if case_data["name"] else "UNKNOWN"
        doi = case_data["doi"].split()[0] if case_data["doi"] else ""
        firm_email = case_data["firm_email"]
        pid = case_data["pid"]
        
        greeting = random.choice(self.greetings)
        status_line = random.choice(self.status_requests)
        followup_line = random.choice(self.followups)
        
        if "2099" in doi or not doi:
            subject = f"{name} UNKNOWN DOI // Prohealth"
            extra_line = "\n\nCould you please provide the accurate date of loss for this case?"
        else:
            subject = f"{name} DOI {doi} // Prohealth"
            extra_line = ""
        
        if self.test_mode:
            original_to = firm_email
            firm_email = self.test_email
            subject = f"[TEST MODE - Original To: {original_to}] {subject}"
        
        body = f"""To: {firm_email}
Subject: {subject}

{greeting}

In regards to Prohealth Advanced Imaging billing and liens.

{status_line} {followup_line}{extra_line}

Thank you.

File #: {pid}
"""
        
        return {
            "pid": pid,
            "to": firm_email,
            "subject": subject,
            "body": body,
            "name": name,
            "doi": doi,
            "original_to": case_data["firm_email"] if self.test_mode else firm_email
        }
    
    def preview_category(self, category_name, limit=None):
        if category_name == "by_firm":
            print("\n📁 Firms with cases:")
            for firm_email, cases in self.categories["active_by_firm"].items():
                print(f"  • {firm_email}: {len(cases)} cases")
            return
        
        category_map = {
            "no_contact": "active_no_recent_contact",
            "missing_doi": "active_missing_doi",
            "old_cases": "active_old_cases",
            "recent_settlement": "active_recent_settlement"
        }
        
        category_key = category_map.get(category_name, category_name)
        cases = self.categories.get(category_key, [])
        
        if not cases:
            print(f"No cases found in category: {category_name}")
            return []
        
        if limit:
            cases = cases[:limit]
        
        emails = []
        for case in cases:
            email = self.generate_email(case)
            emails.append(email)
        
        return emails
    
    def preview_firm_cases(self, firm_email, limit=None):
        cases = self.categories["active_by_firm"].get(firm_email, [])
        
        if not cases:
            print(f"No cases found for firm: {firm_email}")
            return []
        
        if limit:
            cases = cases[:limit]
        
        emails = []
        for case in cases:
            email = self.generate_email(case)
            emails.append(email)
        
        return emails
    
    def display_email_batch(self, emails):
        print(f"\n📧 Generated {len(emails)} emails:")
        print("-" * 60)
        
        for i, email in enumerate(emails, 1):
            print(f"\n[{i}] PID: {email['pid']}")
            print(f"    To: {email['to']}")
            if self.test_mode and email.get('original_to'):
                print(f"    (Original: {email['original_to']})")
            print(f"    Subject: {email['subject']}")
            print(f"    Name: {email['name']}")
            print(f"    DOI: {email['doi'] or 'UNKNOWN'}")
        
        return emails
    
    def approve_batch(self, emails):
        print("\n" + "=" * 60)
        print("BATCH APPROVAL OPTIONS:")
        print("  [A] Approve ALL and send")
        print("  [S] Select specific emails to send")
        print("  [R] Review individual emails")
        print("  [X] Skip this entire batch")
        print("=" * 60)
        
        choice = input("\nYour choice: ").strip().upper()
        
        if choice == "A":
            return emails
        
        elif choice == "S":
            print("\nEnter PIDs to send (comma-separated) or ranges (e.g., 1-5,7,9):")
            selection = input("Selection: ").strip()
            
            selected_indices = []
            for part in selection.split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    selected_indices.extend(range(start-1, end))
                else:
                    selected_indices.append(int(part)-1)
            
            return [emails[i] for i in selected_indices if 0 <= i < len(emails)]
        
        elif choice == "R":
            approved = []
            for i, email in enumerate(emails, 1):
                print(f"\n[{i}/{len(emails)}] Review Email:")
                print("-" * 40)
                print(email['body'])
                print("-" * 40)
                
                approve = input("Send this email? (Y/n/skip remaining): ").strip().lower()
                if approve == "y" or approve == "":
                    approved.append(email)
                elif approve == "skip":
                    break
            
            return approved
        
        else:
            return []
    
    def send_batch(self, emails):
        if not emails:
            print("No emails to send.")
            return
        
        print(f"\n🚀 Sending {len(emails)} emails...")
        if self.test_mode:
            print(f"⚠️  TEST MODE: All emails will be sent to {self.test_email}")
        
        success_count = 0
        fail_count = 0
        
        for email in emails:
            try:
                msg = EmailMessage()
                msg["From"] = self.gmail_address
                msg["To"] = email["to"]
                msg["Subject"] = email["subject"]
                
                body_lines = email["body"].split("\n")
                clean_body = "\n".join(body_lines[2:])
                msg.set_content(clean_body)
                
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                    smtp.login(self.gmail_address, self.gmail_app_password)
                    smtp.send_message(msg)
                
                print(f"✅ Sent to {email['to']} (PID: {email['pid']})")
                self.log_success(email)
                success_count += 1
                
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Failed PID {email['pid']}: {e}")
                self.log_failure(email, str(e))
                fail_count += 1
        
        print(f"\n📊 Results: {success_count} sent, {fail_count} failed")
    
    def log_success(self, email):
        if email.get('is_consolidated'):
            # For consolidated emails, log all PIDs
            pids = email['pid'].split(", ")
            log_line = f"CONSOLIDATED EMAIL | PIDs: {email['pid']} | Sent to: {email['to']} | Subject: {email['subject']}"
            if self.test_mode:
                log_line += f" | TEST MODE - Original: {email.get('original_to', 'N/A')}"
            log_line += "\n"
            
            for logfile in ["sent_emails.log", "sent_emails_log.txt"]:
                with open(logfile, "a", encoding="utf-8") as log:
                    log.write(log_line)
            
            # Add all PIDs to sent list
            for pid in pids:
                self.sent_pids.add(pid.strip())
        else:
            # Individual email logging (existing code)
            log_line = f"PID: {email['pid']} | Sent to: {email['to']} | Subject: {email['subject']}"
            if self.test_mode:
                log_line += f" | TEST MODE - Original: {email.get('original_to', 'N/A')}"
            log_line += "\n"
            
            for logfile in ["sent_emails.log", "sent_emails_log.txt"]:
                with open(logfile, "a", encoding="utf-8") as log:
                    log.write(log_line)
            
            self.sent_pids.add(email['pid'])
    
    def log_failure(self, email, error):
        with open("failed_emails.log", "a", encoding="utf-8") as log:
            log.write(f"FAILED: {email['to']} | PID: {email['pid']} | Error: {error}\n")
    
    def log_cms_note(self, email):
        cms_note = {
            "pid": email['pid'],
            "timestamp": datetime.now().isoformat(),
            "action": "status_request_sent",
            "recipient": email.get('original_to', email['to']),
            "test_mode": self.test_mode
        }
        
        log_file = "cms_notes.json"
        notes = []
        
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                notes = json.load(f)
        
        notes.append(cms_note)
        
        with open(log_file, "w") as f:
            json.dump(notes, f, indent=2)
        
        print(f"📝 CMS note logged for PID {email['pid']}")
    
    def run_interactive(self):
        print("\n🚀 BULK EMAIL MANAGER")
        print("=" * 60)
        
        if self.test_mode:
            print(f"⚠️  TEST MODE ACTIVE - Emails will go to: {self.test_email}")
        else:
            print("⚡ PRODUCTION MODE - Emails will go to actual recipients")
        
        df = self.load_cases()
        self.categorize_cases(df)
        
        print(f"\n📊 Case Statistics:")
        print(f"  • Total active cases: {len(df[df['Case Status'].str.upper() == 'ACTIVE'])}")
        print(f"  • Already sent: {len(self.sent_pids)}")
        print(f"  • No recent contact: {len(self.categories['active_no_recent_contact'])}")
        print(f"  • Missing DOI: {len(self.categories['active_missing_doi'])}")
        print(f"  • Old cases (>2 years): {len(self.categories['active_old_cases'])}")
        print(f"  • Unique firms: {len(self.categories['active_by_firm'])}")
        
        while True:
            print("\n" + "=" * 60)
            print("SELECT PROCESSING MODE:")
            print("  [1] Process by category")
            print("  [2] Process by firm")
            print("  [3] Process custom selection")
            print("  [4] Toggle test mode")
            print("  [5] View statistics")
            print("  [Q] Quit")
            print("=" * 60)
            
            choice = input("\nYour choice: ").strip().upper()
            
            if choice == "1":
                print("\nCategories:")
                print("  [1] No recent contact (>60 days)")
                print("  [2] Missing DOI")
                print("  [3] Old cases (>2 years)")
                
                cat_choice = input("Select category: ").strip()
                category_map = {
                    "1": "no_contact",
                    "2": "missing_doi", 
                    "3": "old_cases"
                }
                
                if cat_choice in category_map:
                    limit = input("How many to process? (Enter for all): ").strip()
                    limit = int(limit) if limit else None
                    
                    emails = self.preview_category(category_map[cat_choice], limit)
                    if emails:
                        self.display_email_batch(emails)
                        approved = self.approve_batch(emails)
                        if approved:
                            self.send_batch(approved)
                            for email in approved:
                                self.log_cms_note(email)
            
            elif choice == "2":
                self.preview_category("by_firm")
                firm_email = input("\nEnter firm email to process: ").strip()
                
                if firm_email:
                    limit = input("How many to process? (Enter for all): ").strip()
                    limit = int(limit) if limit else None
                    
                    # Ask for email mode
                    print("\n" + "="*40)
                    print("EMAIL MODE:")
                    print("  [1] Individual emails (one per case)")
                    print("  [2] Consolidated email (all cases in one)")
                    print("="*40)
                    email_mode = input("Select mode (1 or 2): ").strip()
                    
                    if email_mode == "2":
                        # Consolidated email mode
                        cases = self.categories["active_by_firm"].get(firm_email, [])
                        if limit:
                            cases = cases[:limit]
                        
                        if cases:
                            consolidated_email = self.generate_consolidated_email(firm_email, cases)
                            print("\n" + "="*60)
                            print("CONSOLIDATED EMAIL PREVIEW:")
                            print("="*60)
                            print(f"To: {consolidated_email['to']}")
                            print(f"Subject: {consolidated_email['subject']}")
                            print("-"*40)
                            print(consolidated_email['body'])
                            print("-"*40)
                            
                            approve = input("\nSend this consolidated email? (Y/n): ").strip().lower()
                            if approve == "y" or approve == "":
                                self.send_batch([consolidated_email])
                                # Log each case
                                for case in cases:
                                    self.log_cms_note({"pid": case['pid'], "to": firm_email})
                    else:
                        # Individual emails mode (default)
                        emails = self.preview_firm_cases(firm_email, limit)
                        if emails:
                            self.display_email_batch(emails)
                            approved = self.approve_batch(emails)
                            if approved:
                                self.send_batch(approved)
                                for email in approved:
                                    self.log_cms_note(email)
            
            elif choice == "4":
                self.test_mode = not self.test_mode
                if self.test_mode:
                    test_email = input(f"Enter test email (Enter for {self.test_email}): ").strip()
                    if test_email:
                        self.test_email = test_email
                print(f"Test mode: {'ON' if self.test_mode else 'OFF'}")
            
            elif choice == "Q":
                break
            
            elif choice == "5":
                df = self.load_cases()
                self.categorize_cases(df)
                print(f"\n📊 Updated Statistics:")
                print(f"  • Remaining to process: {len(df[df['Case Status'].str.upper() == 'ACTIVE']) - len(self.sent_pids)}")
                print(f"  • Sent this session: {len(self.sent_pids)}")

if __name__ == "__main__":
    print("\n🔧 BULK EMAIL MANAGER SETUP")
    print("-" * 40)
    
    test_mode = input("Enable TEST MODE? (Y/n): ").strip().lower()
    test_mode = test_mode != 'n'
    
    test_email = None
    if test_mode:
        test_email = input("Test email address (Enter for default): ").strip()
        if not test_email:
            test_email = "deanh.transcon@gmail.com"
    
    manager = BulkEmailManager(test_mode=test_mode, test_email=test_email)
    manager.run_interactive()