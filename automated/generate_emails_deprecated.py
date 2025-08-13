import pandas as pd

# Load your Excel file
excel_file = "cases.xlsx"  # Replace with your actual filename
df = pd.read_excel(excel_file)

output = []

for index, row in df.iterrows():
    name_raw = str(row.get("PatientName", "") or "").strip()
    name = name_raw.title() if name_raw else "UNKNOWN"

    doi_raw = str(row.get("DOI", "") or "").strip()
    firm_email = str(row.get("att_email", "") or "").strip()
    attorney_name = str(row.get("att_name", "") or "Attorney").title()
    firm_name = str(row.get("provider", "") or "Law Firm").title()
    reference = str(row.get("PID", "000000"))

    doi = doi_raw.split()[0] if doi_raw else ""
    greeting_name = firm_name if firm_name not in ["", "N/A"] else attorney_name

    if "2099" in doi:
        subject = f"{name} UNKNOWN DOI // Prohealth"
        extra_line = "\n\nCould you please provide the accurate date of loss for this case?"
    else:
        subject = f"{name} DOI {doi} // Prohealth"
        extra_line = ""

    body = f"""To: {firm_email}
Subject: {subject}

Hello {greeting_name},

In regards to Prohealth Advanced Imaging billing and liens for {name}.

Has this case settled or is it still pending? Please get back to me when you can and let me know if you need any bills or reports, as I show a signed lien on file from your firm.{extra_line}

Thank you.

Reference #: {reference}
"""

    output.append(body)

# Save to file
with open("generated_emails.txt", "w", encoding="utf-8") as f:
    for email in output:
        f.write(email)
        f.write("\n" + "-" * 60 + "\n\n")
