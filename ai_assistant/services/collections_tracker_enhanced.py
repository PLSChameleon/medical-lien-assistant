"""
Enhanced Collections Tracker that uses the bootstrap cache
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from services.email_cache_service import EmailCacheService

logger = logging.getLogger(__name__)

class EnhancedCollectionsTracker:
    """Collections tracker that analyzes emails from the bootstrap cache"""
    
    def __init__(self, email_cache_service: EmailCacheService):
        self.email_cache = email_cache_service
        self.tracking_file = "data/collections_tracking_enhanced.json"
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
            "analysis_version": "2.0"
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
    
    def analyze_from_cache(self, case_manager):
        """
        Analyze all cases using the email cache instead of live API calls
        This is MUCH faster and uses consistent data
        """
        logger.info("Analyzing collections from bootstrap cache...")
        
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
        matches_found = 0
        
        for email in cache_emails:
            emails_processed += 1
            
            # Extract email details
            subject = (email.get('subject') or '').lower()
            snippet = (email.get('snippet') or '').lower()
            from_field = (email.get('from') or '').lower()
            to_field = (email.get('to') or '').lower()
            email_date = email.get('date')
            
            # Check if this is a sent or received email
            is_sent = self.email_cache._is_sent_email(email)
            
            # Try to match email to cases
            for pv, case_data in all_cases.items():
                # Build search terms for this case
                search_terms = []
                
                # Add PV number with variations
                if pv:
                    pv_lower = pv.lower()
                    search_terms.append(pv_lower)
                    # Also search for common PV formats
                    search_terms.append(f"pv {pv_lower}")
                    search_terms.append(f"pv#{pv_lower}")
                    search_terms.append(f"pv: {pv_lower}")
                    search_terms.append(f"pv{pv_lower}")
                
                # Add patient name - handle different formats
                if case_data['name']:
                    name = case_data['name'].lower()
                    search_terms.append(name)
                    
                    # Also add name parts for better matching
                    # Handle "LAST, FIRST" format
                    if ',' in name:
                        parts = [p.strip() for p in name.split(',')]
                        search_terms.extend(parts)
                        # Also add "first last" format
                        if len(parts) == 2:
                            search_terms.append(f"{parts[1]} {parts[0]}")
                    else:
                        # Add individual name parts
                        search_terms.extend(name.split())
                
                # Add CMS number
                if case_data['cms']:
                    search_terms.append(str(case_data['cms']).lower())
                
                # Check if any search term matches the email
                email_text = f"{subject} {snippet} {from_field} {to_field}"
                
                matched = False
                for term in search_terms:
                    if term and term in email_text:
                        matched = True
                        break
                
                if matched:
                    matches_found += 1
                    
                    # Parse email date
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
                        "snippet": email.get('snippet'),
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
        
        logger.info(f"Analysis complete: {emails_processed} emails processed, {matches_found} matches found")
        
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
        print("📊 COLLECTIONS ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total cases analyzed: {total_cases}")
        print(f"Cases with email activity: {cases_with_activity}")
        print(f"Cases with responses: {cases_with_responses}")
        print(f"NO RESPONSE cases (sent but no reply): {no_response_cases}")
        print(f"Never contacted: {never_contacted}")
        print("="*60)
    
    def get_stale_cases(self, days_threshold=30):
        """Get cases that haven't been contacted recently"""
        stale_cases = {
            "critical": [],        # 90+ days
            "high_priority": [],   # 60+ days
            "needs_follow_up": [], # 30+ days
            "no_response": [],     # Sent emails but no responses
            "never_contacted": []  # No activity at all
        }
        
        now = datetime.now()
        
        for pv, case_data in self.data['cases'].items():
            # Calculate days since last contact
            days_since = None
            if case_data['last_contact']:
                try:
                    last_contact_date = datetime.fromisoformat(case_data['last_contact'])
                    days_since = (now - last_contact_date).days
                except:
                    pass
            
            case_summary = {
                "pv": pv,
                "name": case_data['case_info']['name'],
                "law_firm": case_data['case_info']['law_firm'],
                "attorney_email": case_data['case_info']['attorney_email'],
                "days_since_contact": days_since,
                "last_contact": case_data['last_contact'],
                "sent_count": case_data['sent_count'],
                "response_count": case_data['response_count']
            }
            
            # Categorize
            if case_data['sent_count'] == 0 and case_data['response_count'] == 0:
                stale_cases['never_contacted'].append(case_summary)
            elif case_data['sent_count'] > 0 and case_data['response_count'] == 0:
                stale_cases['no_response'].append(case_summary)
            elif days_since:
                if days_since >= 90:
                    stale_cases['critical'].append(case_summary)
                elif days_since >= 60:
                    stale_cases['high_priority'].append(case_summary)
                elif days_since >= 30:
                    stale_cases['needs_follow_up'].append(case_summary)
        
        return stale_cases
    
    def get_case_history(self, pv):
        """Get complete email history for a case"""
        if pv not in self.data['cases']:
            return None
        
        case_data = self.data['cases'][pv]
        
        # Sort activities by date
        activities = sorted(
            case_data['activities'],
            key=lambda x: x.get('date') or '',
            reverse=True
        )
        
        return {
            "case_info": case_data['case_info'],
            "summary": {
                "sent_count": case_data['sent_count'],
                "response_count": case_data['response_count'],
                "last_contact": case_data['last_contact'],
                "last_sent": case_data['last_sent'],
                "last_received": case_data['last_received']
            },
            "activities": activities
        }