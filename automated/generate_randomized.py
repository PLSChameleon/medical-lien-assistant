import pandas as pd
import random
import re

# Load the Excel file
excel_file = "automated_cases.xlsx"  # Replace with your actual filename
df = pd.read_excel(excel_file)

# Phrase banks
greetings = ["Hello", "Hi", "Greetings", "Good day", "Dear"]
status_requests = [
    "Has this case settled or is it still pending?",
    "Can you let me know the current status of this case?",
    "Do you happen to have an update on this case?",
    "Is this matter still open or has it been resolved?",
]
followups = [
    "Let me know if you need bills or reports.",
    "If you need any reports or billing, just let me know.",
    "Feel free to reach out if any bills or documentation are needed.",
    "I’m happy to provide any necessary documents or reports you may need.",
]

unknown_doi_line = "\n\nCould you please provide the accurate date of loss for this case?"

output = []

def extract_greeting(attorney_name, email):
    if "law" in email.lower():
        # Try to get firm name before "law"
        match = re.search(r'([a-zA-Z0-9]+)(?=law)', email.lower())
        if match:
            firm = match.group(1).capitalize()
            return f"Hello {firm} Law,"
    if attorney_name:
        name_parts = attorney_name.strip().split()
        last_name = name_parts[-1]
        return f"Hello Attorney {last_name},"
    return "Hello Law Firm,"

for index, row in df.iterrows():
    name_raw = str(row.get("PatientName", "") or "").strip()
    name = name_raw.title() if name_raw else "UNKNOWN"
    doi_raw = str(row.get("DOI", "") or "").strip()
    firm_email = str(row.get("att_email", "") or "").strip()
    attorney_name = str(row.get("att_name", "") or "").title()
    reference = str(row.get("PID", "000000"))

    doi = doi_raw.split()[0] if doi_raw else ""
    greeting = random.choice(greetings)
    status_line = random.choice(status_requests)
    followup_line = random.choice(followups)

    # Greeting line (formal + contextual)
    greeting_line = extract_greeting(attorney_name, firm_email)

    # Subject and DOI logic
    if "2099" in doi:
        subject = f"{name} UNKNOWN DOI // Prohealth"
        extra_line = unknown_doi_line
    else:
        subject = f"{name} DOI {doi} // Prohealth"
        extra_line = ""

    body = f"""To: {firm_email}
Subject: {subject}

{greeting_line}

In regards to Prohealth Advanced Imaging billing and liens.

{status_line} {followup_line}{extra_line}

Thank you.

Reference #: {reference}
"""
    output.append(body)

# Save to text file
with open("generated_emails.txt", "w", encoding="utf-8") as f:
    for email in output:
        f.write(email)
        f.write("\n" + "-" * 60 + "\n\n")

print("✅ Emails generated and saved to generated_emails.txt")
