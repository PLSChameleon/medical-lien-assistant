"""
Name-based Collections Tracker with DOI disambiguation
Focuses on name matching, uses DOI to distinguish duplicate names
"""
import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from services.email_cache_service import EmailCacheService

logger = logging.getLogger(__name__)

class NameBasedCollectionsTracker:
    """Collections tracker using name-first matching with DOI disambiguation"""
    
    def __init__(self, email_cache_service: EmailCacheService):
        self.email_cache = email_cache_service
        self.tracking_file = "data/collections_tracking_name_based.json"
        self.data = self._load_tracking_data()
        self.duplicate_names = {}  # Track cases with same names
        
    def _load_tracking_data(self):
        """Load existing tracking data"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading tracking data: {e}")
        
        return {
            "cases": {},
            "last_analysis": None,
            "analysis_version": "4.0-name-based"
        }
    
    def _save_tracking_data(self):
        """Save tracking data to file"""
        try:
            os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
            with open(self.tracking_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
            logger.info("Tracking data saved")
        except Exception as e:
            logger.error(f"Error saving tracking data: {e}")
    
    def _normalize_name(self, name: str) -> Set[str]:
        """
        Generate normalized versions of a name for matching
        Returns a set of possible name variations
        """
        if not name:
            return set()
        
        variations = set()
        name = name.strip()
        
        # Clean the name
        # Remove common suffixes and punctuation
        clean_name = re.sub(r'\b(jr|sr|iii|ii|iv|esq|md|phd|dds|pa|rn|np)\b', '', name, flags=re.IGNORECASE)
        clean_name = re.sub(r'[,.\-\'"]', ' ', clean_name)
        clean_name = ' '.join(clean_name.split())  # Normalize whitespace
        
        if not clean_name:
            return variations
        
        # Add full cleaned name
        variations.add(clean_name.lower())
        
        # Split into parts
        parts = clean_name.split()
        
        if len(parts) >= 2:
            # First Last
            first_last = f"{parts[0]} {parts[-1]}"
            variations.add(first_last.lower())
            
            # Last, First
            last_first = f"{parts[-1]} {parts[0]}"
            variations.add(last_first.lower())
            
            # Just last name (if distinctive enough)
            if len(parts[-1]) >= 4:
                variations.add(parts[-1].lower())
            
            # First + Middle initial + Last (if 3 parts)
            if len(parts) == 3:
                variations.add(f"{parts[0]} {parts[1][0]} {parts[2]}".lower())
                variations.add(f"{parts[0]} {parts[2]}".lower())  # Without middle
        
        # Handle hyphenated last names
        for part in parts:
            if '-' in part and len(part) > 5:
                variations.add(part.lower())
                # Also add the non-hyphenated version
                variations.add(part.replace('-', ' ').lower())
                variations.add(part.replace('-', '').lower())
        
        return variations
    
    def _extract_dates(self, text: str) -> Set[str]:
        """
        Extract dates that could be DOI from text
        Returns set of date strings in various formats
        """
        if not text:
            return set()
        
        dates = set()
        
        # Pattern 1: MM/DD/YYYY or MM-DD-YYYY
        matches = re.findall(r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b', text)
        dates.update(matches)
        
        # Pattern 2: YYYY-MM-DD
        matches = re.findall(r'\b(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b', text)
        dates.update(matches)
        
        # Pattern 3: Month DD, YYYY (e.g., "January 15, 2023")
        matches = re.findall(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b', text, re.IGNORECASE)
        dates.update(matches)
        
        # Pattern 4: DD Month YYYY
        matches = re.findall(r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b', text, re.IGNORECASE)
        dates.update(matches)
        
        return dates
    
    def _normalize_doi(self, doi) -> Set[str]:
        """
        Convert DOI to multiple format variations for matching
        """
        if not doi:
            return set()
        
        variations = set()
        
        # Handle datetime objects
        if hasattr(doi, 'strftime'):
            # Add multiple date formats
            variations.add(doi.strftime('%m/%d/%Y'))
            variations.add(doi.strftime('%m-%d-%Y'))
            variations.add(doi.strftime('%Y-%m-%d'))
            variations.add(doi.strftime('%B %d, %Y'))
            variations.add(doi.strftime('%b %d, %Y'))
            variations.add(doi.strftime('%d %B %Y'))
            # Without leading zeros
            variations.add(doi.strftime('%-m/%-d/%Y') if hasattr(doi, 'strftime') else None)
        else:
            # It's a string, try to parse it
            doi_str = str(doi)
            variations.add(doi_str)
            
            # Try to parse and reformat
            try:
                from dateutil import parser
                parsed = parser.parse(doi_str)
                variations.update(self._normalize_doi(parsed))
            except:
                # Just add the string as-is
                pass
        
        # Remove None values
        return {v for v in variations if v}
    
    def _identify_duplicate_names(self, all_cases: Dict):
        """
        Identify cases with duplicate patient names
        """
        name_to_pvs = {}
        
        for pv, case_info in all_cases.items():
            if case_info.get('name'):
                # Use a normalized version for grouping
                name_key = ' '.join(case_info['name'].upper().split())
                if name_key not in name_to_pvs:
                    name_to_pvs[name_key] = []
                name_to_pvs[name_key].append(pv)
        
        # Find duplicates
        self.duplicate_names = {
            name: pvs for name, pvs in name_to_pvs.items() 
            if len(pvs) > 1
        }
        
        if self.duplicate_names:
            print(f"\n⚠️  Found {len(self.duplicate_names)} duplicate patient names")
            for name, pvs in list(self.duplicate_names.items())[:5]:
                print(f"   {name}: {len(pvs)} cases (PVs: {', '.join(pvs[:3])}...)")
    
    def _match_email_to_case(self, email: dict, pv: str, case_info: dict, all_cases: Dict) -> bool:
        """
        Match email to case primarily by name, with DOI for disambiguation
        """
        # Get email text
        subject = (email.get('subject') or '').lower()
        snippet = (email.get('snippet') or '').lower()
        email_text = f"{subject} {snippet}"
        
        # Step 1: Check if patient name is mentioned
        name_matched = False
        if case_info.get('name'):
            name_variations = self._normalize_name(case_info['name'])
            
            for variation in name_variations:
                if len(variation) >= 4 and variation in email_text:
                    name_matched = True
                    break
        
        if not name_matched:
            # Also check PV if it's explicitly mentioned (high confidence)
            if pv and f"pv {pv}" in email_text:
                return True
            if pv and f"pv{pv}" in email_text:
                return True
            # Check CMS if explicitly mentioned
            if case_info.get('cms'):
                cms_str = str(case_info['cms'])
                if len(cms_str) >= 5 and f"cms {cms_str}" in email_text:
                    return True
            return False
        
        # Step 2: If name matched, check if it's a duplicate name
        name_key = ' '.join(case_info['name'].upper().split()) if case_info.get('name') else ''
        
        if name_key in self.duplicate_names:
            # This name has duplicates, need DOI to disambiguate
            duplicate_pvs = self.duplicate_names[name_key]
            
            # Extract dates from email
            email_dates = self._extract_dates(email_text)
            
            if email_dates and case_info.get('doi'):
                # Check if this case's DOI matches any date in email
                doi_variations = self._normalize_doi(case_info['doi'])
                
                for email_date in email_dates:
                    for doi_var in doi_variations:
                        if doi_var and doi_var.lower() in email_date.lower():
                            return True
                
                # If DOI doesn't match, check other duplicate cases
                # to make sure this email doesn't belong to them
                for other_pv in duplicate_pvs:
                    if other_pv != pv:
                        other_case = all_cases.get(other_pv, {})
                        if other_case.get('doi'):
                            other_doi_vars = self._normalize_doi(other_case['doi'])
                            for email_date in email_dates:
                                for doi_var in other_doi_vars:
                                    if doi_var and doi_var.lower() in email_date.lower():
                                        # This email belongs to the other case
                                        return False
            
            # If we can't disambiguate by DOI, check for PV number as tiebreaker
            if pv and pv in email_text:
                return True
            
            # Can't definitively match to this specific duplicate
            # Be conservative and don't match
            return False
        
        # Step 3: Name matched and it's unique, that's enough
        return True
    
    def analyze_from_cache(self, case_manager):
        """
        Analyze all cases using name-based matching
        """
        logger.info("Analyzing collections with name-based matching...")
        
        # Ensure cache is populated
        if not self.email_cache.cache.get('emails'):
            logger.warning("Email cache is empty - need to run bootstrap first")
            return False
        
        cache_emails = self.email_cache.cache['emails']
        logger.info(f"Analyzing {len(cache_emails)} cached emails")
        
        # Reset tracking data
        self.data['cases'] = {}
        
        # Get all cases from spreadsheet
        try:
            cases_df = case_manager.df
            all_cases = {}
            
            for _, row in cases_df.iterrows():
                case_info = case_manager.format_case(row)
                pv = str(case_info.get("PV", "")).strip()
                if pv:
                    all_cases[pv] = {
                        "name": case_info.get("Name", ""),
                        "attorney_email": case_info.get("Attorney Email", ""),
                        "law_firm": case_info.get("Law Firm", ""),
                        "cms": case_info.get("CMS", ""),
                        "doi": case_info.get("DOI", ""),
                        "status": case_info.get("Status", "")
                    }
        except Exception as e:
            logger.error(f"Error loading cases: {e}")
            return False
        
        logger.info(f"Found {len(all_cases)} cases in spreadsheet")
        
        # Identify duplicate names
        self._identify_duplicate_names(all_cases)
        
        # Initialize case tracking
        for pv, case_info in all_cases.items():
            self.data['cases'][pv] = {
                "case_info": case_info,
                "sent_emails": [],
                "received_emails": [],
                "last_contact": None,
                "last_sent": None,
                "last_received": None,
                "response_count": 0,
                "sent_count": 0,
                "activities": []
            }
        
        # Process each cached email
        emails_processed = 0
        total_matches = 0
        
        print(f"\n🔍 Processing {len(cache_emails)} emails with name-based matching...")
        
        for i, email in enumerate(cache_emails):
            emails_processed += 1
            
            # Progress indicator
            if emails_processed % 1000 == 0:
                print(f"   Processed {emails_processed}/{len(cache_emails)} emails, {total_matches} matches so far...")
            
            # Check if this is a sent or received email
            is_sent = self.email_cache._is_sent_email(email)
            
            # Try to match email to cases
            for pv, case_data in all_cases.items():
                if self._match_email_to_case(email, pv, case_data, all_cases):
                    total_matches += 1
                    
                    # Parse email date
                    email_date = email.get('date')
                    try:
                        from email.utils import parsedate_to_datetime
                        email_datetime = parsedate_to_datetime(email_date) if email_date else None
                    except:
                        email_datetime = None
                    
                    # Record the activity
                    activity = {
                        "date": email_datetime.isoformat() if email_datetime else email_date,
                        "type": "sent" if is_sent else "received",
                        "subject": email.get('subject'),
                        "snippet": email.get('snippet')[:100] if email.get('snippet') else None,
                        "from": email.get('from'),
                        "to": email.get('to'),
                        "id": email.get('id')
                    }
                    
                    case_tracking = self.data['cases'][pv]
                    case_tracking['activities'].append(activity)
                    
                    if is_sent:
                        case_tracking['sent_emails'].append(activity)
                        case_tracking['sent_count'] += 1
                        
                        # Update last sent date
                        if email_datetime:
                            if not case_tracking['last_sent'] or email_datetime > datetime.fromisoformat(case_tracking['last_sent']):
                                case_tracking['last_sent'] = email_datetime.isoformat()
                    else:
                        case_tracking['received_emails'].append(activity)
                        case_tracking['response_count'] += 1
                        
                        # Update last received date
                        if email_datetime:
                            if not case_tracking['last_received'] or email_datetime > datetime.fromisoformat(case_tracking['last_received']):
                                case_tracking['last_received'] = email_datetime.isoformat()
                    
                    # Update last contact
                    if email_datetime:
                        if not case_tracking['last_contact'] or email_datetime > datetime.fromisoformat(case_tracking['last_contact']):
                            case_tracking['last_contact'] = email_datetime.isoformat()
        
        # Save results
        self.data['last_analysis'] = datetime.now().isoformat()
        self._save_tracking_data()
        
        logger.info(f"Analysis complete: {emails_processed} emails processed, {total_matches} total matches")
        
        # Generate summary
        self._print_analysis_summary()
        
        return True
    
    def _print_analysis_summary(self):
        """Print summary of the analysis"""
        total_cases = len(self.data['cases'])
        cases_with_activity = 0
        cases_with_responses = 0
        no_response_cases = 0
        never_contacted = 0
        
        for pv, case_data in self.data['cases'].items():
            if case_data['sent_count'] > 0 or case_data['response_count'] > 0:
                cases_with_activity += 1
            
            if case_data['response_count'] > 0:
                cases_with_responses += 1
            
            if case_data['sent_count'] > 0 and case_data['response_count'] == 0:
                no_response_cases += 1
            
            if case_data['sent_count'] == 0 and case_data['response_count'] == 0:
                never_contacted += 1
        
        print("\n" + "="*60)
        print("📊 NAME-BASED COLLECTIONS ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total cases analyzed: {total_cases}")
        print(f"Cases with email activity: {cases_with_activity}")
        print(f"Cases with responses: {cases_with_responses}")
        print(f"NO RESPONSE cases (sent but no reply): {no_response_cases}")
        print(f"Never contacted: {never_contacted}")
        print("="*60)
        
        if self.duplicate_names:
            print(f"\n⚠️  {len(self.duplicate_names)} duplicate names found")
            print("   Using DOI to distinguish between them")