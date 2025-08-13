import pandas as pd
import random

# Load Excel file
excel_file = "cases2.xlsm"  # Replace with your file name
df = pd.read_excel(excel_file)

# Phrase banks
greetings = [
    "Hello Law Firm,", 
    "Good day Law Firm,", 
    "Greetings Law Firm,", 
    "Hi Law Firm,", 
    "Dear Law Firm,"
]

status_requests = [
    "Has this case settled or is it still pending?",
    "Can you let me know the current status of this case?",
    "Do you happen to have an update on this case?",
    "Is this matter still open or has it been resolved?",
    "Could you please confirm whether the case is resolved or still pending?"
]

followups = [
    "Let me know if you need bills or reports.",
    "If you need any reports or billing, just let me know.",
    "Feel free to reach out if any bills or documentation are needed.",
    "I’m happy to provide any necessary documents or reports you may need.",
    "We can send over any billing or medical records you might need."
]

unknown_doi_line = "\n\nCould you please provide the accurate date of loss for this case?"

output = []

# Filter for Active cases only
active_cases = df[df["Case Status"].str.upper() == "ACTIVE"]

for index, row in active_cases.iterrows():
    name_raw = str(row.get("PatientName", "") or "").strip()
    name = name_raw.title() if name_raw else "UNKNOWN"
    doi_raw = str(row.get("DOI", "") or "").strip()
    firm_email = str(row.get("Attny Email", "") or "").strip()
    reference = str(row.get("PID", "000000"))

    doi = doi_raw.split()[0] if doi_raw else ""
    greeting_line = random.choice(greetings)
    status_line = random.choice(status_requests)
    followup_line = random.choice(followups)

    # Subject and DOI logic
    if "2099" in doi or not doi:
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

File #: {reference}
"""
    output.append(body)

# Save to generated_emails.txt
with open("generated_emails2.txt", "w", encoding="utf-8") as f:
    for email in output:
        f.write(email)
        f.write("\n" + "-" * 60 + "\n\n")

print(f"✅ Generated {len(output)} emails from Active files.")
