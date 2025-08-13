"""
Improved Collections Tracker with better matching logic
"""
import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set
from services.email_cache_service import EmailCacheService

logger = logging.getLogger(__name__)

class ImprovedCollectionsTracker:
    """Collections tracker with improved email matching"""
    
    def __init__(self, email_cache_service: EmailCacheService):
        self.email_cache = email_cache_service
        self.tracking_file = "data/collections_tracking_improved.json"
        self.data = self._load_tracking_data()
        
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
            "analysis_version": "3.0"
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
        Generate multiple normalized versions of a name for matching
        Returns a set of possible name variations
        """
        if not name:
            return set()
        
        variations = set()
        name = name.strip()
        
        # Add original
        variations.add(name.lower())
        
        # Remove common suffixes
        clean_name = re.sub(r'\b(jr|sr|iii|ii|iv|esq|md|phd|dds)\b', '', name, flags=re.IGNORECASE).strip()
        variations.add(clean_name.lower())
        
        # Split into parts
        parts = clean_name.split()
        
        if len(parts) >= 2:
            # Add "First Last"
            variations.add(f"{parts[0]} {parts[-1]}".lower())
            # Add "Last, First"
            variations.add(f"{parts[-1]}, {parts[0]}".lower())
            # Add just last name
            variations.add(parts[-1].lower())
            # Add just first name (if long enough)
            if len(parts[0]) > 3:
                variations.add(parts[0].lower())
        
        # Handle hyphenated names
        for part in parts:
            if '-' in part:
                variations.add(part.lower())
                # Add each hyphenated part
                for subpart in part.split('-'):
                    if len(subpart) > 3:
                        variations.add(subpart.lower())
        
        return variations
    
    def _extract_pv_numbers(self, text: str) -> Set[str]:
        """
        Extract PV/File numbers from text
        Returns set of found PV numbers
        """
        if not text:
            return set()
        
        pv_numbers = set()
        text = text.lower()
        
        # Pattern 1: PV followed by numbers
        matches = re.findall(r'pv\s*#?\s*[:=]?\s*(\d{4,7})', text)
        pv_numbers.update(matches)
        
        # Pattern 2: File # followed by numbers
        matches = re.findall(r'file\s*#?\s*[:=]?\s*(\d{4,7})', text)
        pv_numbers.update(matches)
        
        # Pattern 3: Case # followed by numbers
        matches = re.findall(r'case\s*#?\s*[:=]?\s*(\d{4,7})', text)
        pv_numbers.update(matches)
        
        # Pattern 4: Just the PV number if it's 5-7 digits and stands alone
        matches = re.findall(r'\b(\d{5,7})\b', text)
        for match in matches:
            # Check if this looks like a PV (not a phone, date, etc.)
            if not match.startswith('20'):  # Not a year
                pv_numbers.add(match)
        
        return pv_numbers
    
    def _match_email_to_case(self, email: dict, case_pv: str, case_info: dict) -> bool:
        """
        Improved matching logic for email to case
        Returns True if email matches the case
        """
        # Get email text to search
        subject = (email.get('subject') or '').lower()
        snippet = (email.get('snippet') or '').lower()
        from_field = (email.get('from') or '').lower()
        to_field = (email.get('to') or '').lower()
        
        email_text = f"{subject} {snippet}"
        email_full = f"{subject} {snippet} {from_field} {to_field}"
        
        # 1. Check PV number (highest confidence)
        if case_pv:
            # Direct PV match
            if case_pv in email_text:
                return True
            
            # Extract PV numbers from email and check
            email_pvs = self._extract_pv_numbers(email_text)
            if case_pv in email_pvs:
                return True
        
        # 2. Check CMS number if available
        if case_info.get('cms'):
            cms_str = str(case_info['cms'])
            if len(cms_str) >= 4 and cms_str in email_text:
                return True
        
        # 3. Check patient name (with variations)
        if case_info.get('name'):
            name_variations = self._normalize_name(case_info['name'])
            
            for variation in name_variations:
                # Skip very short variations
                if len(variation) <= 3:
                    continue
                
                # Check if name appears in email
                if variation in email_full:
                    # Extra validation: make sure it's in a case context
                    # Look for case-related keywords nearby
                    if any(keyword in email_text for keyword in ['case', 'patient', 'doi', 'injury', 'billing', 'lien', 'settlement']):
                        return True
        
        # 4. Check attorney email match (for targeted emails)
        if case_info.get('attorney_email'):
            attorney_email = case_info['attorney_email'].lower()
            if attorney_email and (attorney_email in from_field or attorney_email in to_field):
                # If email is to/from the attorney, check if case identifiers are mentioned
                if case_pv and case_pv in email_text:
                    return True
                # Or check if patient name is mentioned
                if case_info.get('name'):
                    name_parts = case_info['name'].split()
                    # Check for last name at least
                    if len(name_parts) > 0 and len(name_parts[-1]) > 3:
                        if name_parts[-1].lower() in email_text:
                            return True
        
        return False
    
    def analyze_from_cache(self, case_manager):
        """
        Analyze all cases using improved matching logic
        """
        logger.info("Analyzing collections with improved matching...")
        
        # Ensure cache is populated
        if not self.email_cache.cache.get('emails'):
            logger.warning("Email cache is empty - need to run bootstrap first")
            return False
        
        cache_emails = self.email_cache.cache['emails']
        logger.info(f"Analyzing {len(cache_emails)} cached emails")
        
        # Reset tracking data for fresh analysis
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
        
        print(f"\n🔍 Processing {len(cache_emails)} emails...")
        
        for i, email in enumerate(cache_emails):
            emails_processed += 1
            
            # Progress indicator
            if emails_processed % 1000 == 0:
                print(f"   Processed {emails_processed}/{len(cache_emails)} emails, {total_matches} matches so far...")
            
            # Check if this is a sent or received email
            is_sent = self.email_cache._is_sent_email(email)
            
            # Try to match email to cases using improved logic
            for pv, case_data in all_cases.items():
                if self._match_email_to_case(email, pv, case_data):
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
                    
                    # Update last contact (most recent of sent or received)
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
        print("📊 IMPROVED COLLECTIONS ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total cases analyzed: {total_cases}")
        print(f"Cases with email activity: {cases_with_activity}")
        print(f"Cases with responses: {cases_with_responses}")
        print(f"NO RESPONSE cases (sent but no reply): {no_response_cases}")
        print(f"Never contacted: {never_contacted}")
        print("="*60)
        print("\n💡 Improved matching includes:")
        print("   • Name variations (First Last, Last First, etc.)")
        print("   • PV number extraction from text")
        print("   • Attorney email correlation")
        print("   • Fuzzy name matching")