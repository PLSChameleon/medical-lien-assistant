import pandas as pd

df = pd.read_excel("refreshed_may_list.xlsx", header=None)

def get_file_info(pv=None):
    if pv is None:
        return None

    # Column B (index 1) = PV#
    matches = df[df[1].astype(str) == str(pv)]

    if matches.empty:
        return None

    row = matches.iloc[0]

    return {
        "CMS": str(row[0]),              # Column A
        "PV #": str(row[1]),             # Column B
        "Name": str(row[3]),             # Column D
        "Date of Injury": str(row[4])    # Column E
    }
