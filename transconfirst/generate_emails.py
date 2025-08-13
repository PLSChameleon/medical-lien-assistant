import pandas as pd
from datetime import datetime

# Load the Excel file
excel_file = 'cases.xlsx'  # Replace with your actual Excel file name
df = pd.read_excel(excel_file)

# Define the output text file
output_file = 'generated_emails.txt'

# Open the output file in write mode
with open(output_file, 'w', encoding='utf-8') as f:
    for index, row in df.iterrows():
        # Extract necessary fields
        pid = row.get('PID', '')
        patient_name = row.get('PatientName', '')
        doi_raw = row.get('DOI', '')
        attorney_name = row.get('att_name', '')
        attorney_email = row.get('att_email', '')

        # Format DOI
        try:
            doi = pd.to_datetime(doi_raw).strftime('%m/%d/%Y')
        except:
            doi = 'N/A'

        # Determine the greeting
        if 'attorney' in str(attorney_name).lower() or 'esq' in str(attorney_name).lower():
            greeting = f"Hello Attorney {attorney_name},"
        else:
            greeting = f"Hello {attorney_name},"

        # Construct the email components
        to_line = f"To: {attorney_email}"
        subject_line = f"Subject: {patient_name} DOI {doi} // Prohealth"
        body = (
            f"{greeting}\n\n"
            f"In regards to Prohealth Advanced Imaging billing and liens for {patient_name}.\n\n"
            "Has this case settled or is it still pending? Please get back to me when you can and let me know if you need any bills or reports, as I show a signed lien on file from your firm.\n\n"
            "Thank you.\n\n"
            f"Reference #: {pid}\n"
        )

        # Write to the output file
        f.write(f"{to_line}\n{subject_line}\n\n{body}\n{'-'*60}\n\n")

print(f"Emails have been generated and saved to '{output_file}'.")
