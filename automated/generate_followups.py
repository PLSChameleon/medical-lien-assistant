import pandas as pd

# Load your manually edited Excel file
excel_file = "followups.xlsx"  # Update with your actual filename if needed
df = pd.read_excel(excel_file)

# Phrase to use in follow-up email body
followup_body = """Hello again,

I am following up on my previous email requesting the status of this case. Please get back to me when you can.

Thank you for your time."""

output = []

# Filter as needed (optional)
# Example: Only include rows where Case Status == "Active" or some custom filter
filtered_df = df[df["Case Status"].str.upper() == "ACTIVE"]

for _, row in filtered_df.iterrows():
    name = str(row.get("PatientName", "") or "").title().strip()
    doi_raw = str(row.get("DOI", "") or "").strip()
    email = str(row.get("Attny Email", "") or "").strip()
    pid = str(row.get("PID", "") or "").strip()

    doi = doi_raw.split()[0] if doi_raw else "UNKNOWN DOI"

    subject = f"{name} DOI {doi} // Prohealth" if "2099" not in doi else f"{name} UNKNOWN DOI // Prohealth"

    full_email = f"""To: {email}
Subject: Follow-Up on {subject}

{followup_body}

File #: {pid}
"""
    output.append(full_email)

# Write to output file
with open("generated_followups.txt", "w", encoding="utf-8") as f:
    for email in output:
        f.write(email)
        f.write("\n" + "-" * 60 + "\n\n")

print(f"✅ Generated {len(output)} follow-up emails in 'generated_followups.txt'")
