import pandas as pd
import logging
from config import Config

logger = logging.getLogger(__name__)

class CaseManager:
    """Manages case data from Excel spreadsheet"""
    
    def __init__(self, filepath=None):
        self.filepath = filepath or Config.CASES_FILE_PATH
        self.df = self.load_cases()
        
    def load_cases(self):
        """Load cases from Excel file with proper error handling"""
        try:
            if not self.filepath:
                raise ValueError("Cases file path not specified")
                
            df = pd.read_excel(self.filepath, header=None)
            df.fillna("", inplace=True)
            logger.info(f"Successfully loaded {len(df)} cases from {self.filepath}")
            return df
            
        except FileNotFoundError:
            logger.error(f"Cases file not found: {self.filepath}")
            print(f"❌ Cases file not found: {self.filepath}")
            print("Please make sure the Excel file exists and the path is correct.")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error loading cases from {self.filepath}: {e}")
            print(f"❌ Error loading spreadsheet: {e}")
            return pd.DataFrame()

    def get_case_by_pv(self, pv):
        """Get case by PV number with duplicate detection"""
        try:
            if self.df.empty:
                logger.warning("No cases loaded - cannot search by PV")
                return None
                
            matches = self.df[self.df[1].astype(str) == str(pv)]
            if matches.empty:
                logger.info(f"No case found for PV: {pv}")
                return None

            row = matches.iloc[0]
            name = row[3] if len(row) > 3 else ""
            
            # Check for duplicates
            self._check_duplicates(name, pv)
            
            logger.info(f"Found case for PV {pv}: {name}")
            return self.format_case(row)
            
        except Exception as e:
            logger.error(f"Error searching for PV {pv}: {e}")
            print(f"❌ Error searching for case: {e}")
            return None

    def get_case_by_name(self, name):
        """Get case by patient name"""
        try:
            if self.df.empty:
                logger.warning("No cases loaded - cannot search by name")
                return None
                
            matches = self.df[self.df[3].str.lower() == name.lower()]
            if not matches.empty:
                logger.info(f"Found case for name: {name}")
                return self.format_case(matches.iloc[0])
            
            logger.info(f"No case found for name: {name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for name {name}: {e}")
            print(f"❌ Error searching for case: {e}")
            return None

    def list_open_cases(self):
        """Get list of active cases"""
        try:
            if self.df.empty:
                return pd.DataFrame()
                
            active_cases = self.df[self.df[2].str.lower() == "active"]
            logger.info(f"Found {len(active_cases)} active cases")
            return active_cases
            
        except Exception as e:
            logger.error(f"Error listing open cases: {e}")
            return pd.DataFrame()

    def _check_duplicates(self, name, pv):
        """Check for duplicate entries with same name"""
        try:
            if not name:
                return
                
            duplicates = self.df[
                (self.df[3].str.lower() == str(name).lower()) &
                (self.df[1].astype(str) != str(pv))
            ]

            if not duplicates.empty:
                print(f"\n⚠️ Duplicate name alert: multiple entries found for '{name}':")
                for _, dup in duplicates.iterrows():
                    print(f"• PV: {dup[1]} | DOI: {dup[4] if len(dup) > 4 else 'N/A'}")
                    
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")

    def format_case(self, row):
        """Format case data into dictionary with safe access"""
        try:
            return {
                "CMS": row[0] if len(row) > 0 else "",
                "PV": row[1] if len(row) > 1 else "",
                "Status": row[2] if len(row) > 2 else "",
                "Name": row[3] if len(row) > 3 else "",
                "DOI": row[4] if len(row) > 4 else "",
                "Attorney Email": row[18] if len(row) > 18 else "",
                "Attorney Phone": row[19] if len(row) > 19 else "",
                "Law Firm": row[12] if len(row) > 12 else "",
            }
        except Exception as e:
            logger.error(f"Error formatting case: {e}")
            return {
                "CMS": "", "PV": "", "Status": "", "Name": "", 
                "DOI": "", "Attorney Email": "", "Attorney Phone": "", "Law Firm": ""
            }
