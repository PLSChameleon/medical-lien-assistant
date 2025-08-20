import pandas as pd
import os

# Try the user-specific spreadsheet
spreadsheet_path = "ai_assistant/data/user_spreadsheets/deanh.transcon@gmail.com_july_runthrough (1).xlsx"

if os.path.exists(spreadsheet_path):
    df = pd.read_excel(spreadsheet_path, header=None)
    print(f"Total columns: {len(df.columns)}")
    print(f"Total rows: {len(df)}")
    print("\nFirst case data (columns 0-10):")
    for i in range(min(11, len(df.columns))):
        val = df.iloc[0][i] if not df.empty else 'empty'
        print(f"Column {i}: {val}")
    
    print("\nLooking for date columns...")
    # Check columns 4-10 for dates
    for i in range(4, min(11, len(df.columns))):
        col_data = df.iloc[0:5][i]  # Check first 5 rows
        print(f"\nColumn {i} samples:")
        for j, val in enumerate(col_data):
            print(f"  Row {j}: {val}")
            
    # Also check if there's a DOA column (Date of Accident)
    print("\nChecking if column 5 might be DOA...")
    if len(df.columns) > 5:
        for i in range(min(5, len(df))):
            print(f"Row {i}, Col 5: {df.iloc[i][5]}")
else:
    print(f"File not found: {spreadsheet_path}")