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
        # Add tracking_data property for compatibility with worker
        self.tracking_data = self.data.get('cases', {})
        
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
    
    def save_tracking_data(self):
        """Public method to save tracking data (for compatibility with worker)"""
        # Sync tracking_data back to main data structure
        if hasattr(self, 'tracking_data'):
            self.data['cases'] = self.tracking_data
        self._save_tracking_data()
    
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
        
        # Reset tracking data for fresh analysis - IMPORTANT: This clears old cases
        self.data['cases'] = {}
        logger.info("Cleared old tracking data for fresh analysis")
        
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
                "activities": [],
                "ccp_335_1_eligible": False,  # Track CCP 335.1 eligibility
                "has_litigation_keywords": False  # Track if we've received litigation keywords
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
            
            # Try to match email to cases - prioritize NAME matching
            email_text = f"{subject} {snippet} {from_field} {to_field}"
            matched_cases = []
            
            for pv, case_data in all_cases.items():
                # PRIMARY: Match by patient name
                if case_data['name']:
                    name = case_data['name'].lower()
                    name_matched = False
                    
                    # Check full name
                    if name in email_text:
                        name_matched = True
                    else:
                        # Handle "LAST, FIRST" format
                        if ',' in name:
                            parts = [p.strip() for p in name.split(',')]
                            # Check "first last" format
                            if len(parts) == 2:
                                alt_name = f"{parts[1]} {parts[0]}"
                                if alt_name in email_text:
                                    name_matched = True
                                # Also check if both parts are present
                                elif parts[0] in email_text and parts[1] in email_text:
                                    name_matched = True
                        else:
                            # Check if all name parts are present
                            name_parts = name.split()
                            if len(name_parts) > 1 and all(part in email_text for part in name_parts):
                                name_matched = True
                    
                    if name_matched:
                        matched_cases.append((pv, case_data))
                        continue
                
                # SECONDARY: Check CMS number if no name match
                if case_data['cms']:
                    cms_str = str(case_data['cms']).lower()
                    if cms_str in email_text:
                        matched_cases.append((pv, case_data))
                        continue
                
                # TERTIARY: Check PV only as last resort
                if pv:
                    pv_lower = pv.lower()
                    # Check for common PV formats
                    pv_patterns = [
                        f"pv {pv_lower}",
                        f"pv#{pv_lower}", 
                        f"pv: {pv_lower}",
                        f"pv{pv_lower}",
                        f"file {pv_lower}",
                        f"file#{pv_lower}"
                    ]
                    if any(pattern in email_text for pattern in pv_patterns):
                        matched_cases.append((pv, case_data))
            
            # Handle multiple matches (duplicate names)
            if len(matched_cases) > 1:
                # Try to disambiguate using DOI
                doi_matched = None
                for pv, case_data in matched_cases:
                    if case_data.get('doi'):
                        # Format DOI for matching (remove time component if present)
                        doi_str = str(case_data['doi']).split()[0] if case_data['doi'] else ""
                        if doi_str and doi_str in email_text:
                            doi_matched = (pv, case_data)
                            break
                
                # If DOI helped disambiguate, use that match
                if doi_matched:
                    matched_cases = [doi_matched]
                # Otherwise, log warning about duplicate and match all
                else:
                    case_names = [case[1]['name'] for case in matched_cases]
                    logger.debug(f"Multiple cases matched for email: {case_names[:3]}")
            
            # Process matches
            for pv, case_data in matched_cases:
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
                    
                    # Check for litigation keywords in received emails
                    if not case_tracking['has_litigation_keywords']:
                        litigation_keywords = [
                            'litigation', 'lawsuit', 'filed', 'case number', 'venue',
                            'settled', 'settlement', 'resolved', 'dismissed', 'pending',
                            'court', 'trial', 'verdict', 'judgment', 'complaint',
                            'docket', 'superior court', 'federal court', 'arbitration',
                            'pre-litigation', 'prelitigation', 'prelit', 'pre litigation',
                            'pre-lit', 'in litigation', 'litigating', 'litigated', 'case settled',
                            'matter settled', 'pending litigation', 'pending settlement'
                        ]
                        
                        email_content = f"{email.get('subject', '')} {email.get('body', '')} {email.get('snippet', '')}".lower()
                        
                        for keyword in litigation_keywords:
                            if keyword in email_content:
                                case_tracking['has_litigation_keywords'] = True
                                logger.debug(f"Case {pv} has litigation keyword: {keyword}")
                                break
                    
                    # Update last received date
                    if email_datetime:
                        if not case_tracking['last_received'] or email_datetime > datetime.fromisoformat(case_tracking['last_received']):
                            case_tracking['last_received'] = email_datetime.isoformat()
                
                # Update last contact (most recent of sent or received)
                if email_datetime:
                    if not case_tracking['last_contact'] or email_datetime > datetime.fromisoformat(case_tracking['last_contact']):
                        case_tracking['last_contact'] = email_datetime.isoformat()
        
        # After processing all emails, check CCP 335.1 eligibility for each case
        logger.info("Checking CCP 335.1 eligibility for all cases...")
        ccp_335_1_count = 0
        
        for pv, case_tracking in self.data['cases'].items():
            case_info = case_tracking['case_info']
            doi_raw = case_info.get('doi')
            
            # Check if DOI is over 2 years old and we haven't received litigation keywords
            if doi_raw and str(doi_raw) not in ['nan', 'NaT', '2099', 'UNKNOWN', '', 'None']:
                try:
                    import pandas as pd
                    
                    # Convert DOI to datetime
                    if hasattr(doi_raw, 'year'):
                        doi_date = doi_raw
                    else:
                        doi_str = str(doi_raw).split()[0]
                        doi_date = pd.to_datetime(doi_str, errors='coerce')
                        if pd.isna(doi_date):
                            continue
                    
                    # Check if over 2 years old
                    years_old = (datetime.now() - doi_date).days / 365
                    if years_old > 2 and not case_tracking['has_litigation_keywords']:
                        case_tracking['ccp_335_1_eligible'] = True
                        ccp_335_1_count += 1
                        logger.info(f"Case {pv} marked as CCP 335.1 eligible - DOI: {doi_str}, {years_old:.1f} years old, no litigation keywords")
                    
                except Exception as e:
                    logger.debug(f"Error checking CCP 335.1 eligibility for {pv}: {e}")
        
        logger.info(f"CCP 335.1 eligibility check complete: {ccp_335_1_count} eligible cases found")
        
        # Save results
        self.data['last_analysis'] = datetime.now().isoformat()
        self._save_tracking_data()
        
        logger.info(f"Analysis complete: {emails_processed} emails processed, {matches_found} matches found, {ccp_335_1_count} CCP 335.1 eligible")
        
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
        ccp_335_1_eligible = 0
        
        for pv, case_data in self.data['cases'].items():
            if case_data['sent_count'] > 0 or case_data['response_count'] > 0:
                cases_with_activity += 1
            
            if case_data['response_count'] > 0:
                cases_with_responses += 1
            
            if case_data['sent_count'] > 0 and case_data['response_count'] == 0:
                no_response_cases += 1
            
            if case_data['sent_count'] == 0 and case_data['response_count'] == 0:
                never_contacted += 1
            
            if case_data.get('ccp_335_1_eligible', False):
                ccp_335_1_eligible += 1
        
        print("\n" + "="*60)
        print("📊 COLLECTIONS ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total cases analyzed: {total_cases}")
        print(f"Cases with email activity: {cases_with_activity}")
        print(f"Cases with responses: {cases_with_responses}")
        print(f"NO RESPONSE cases (sent but no reply): {no_response_cases}")
        print(f"Never contacted: {never_contacted}")
        print(f"CCP 335.1 eligible (>2yr, no litigation): {ccp_335_1_eligible}")
        print("="*60)
    
    def get_stale_cases(self, days_threshold=30):
        """Get cases that haven't been contacted recently"""
        stale_cases = {
            "critical": [],        # Sent email, no response for 90+ days
            "high_priority": [],   # Sent email, no response for 60-89 days
            "no_response": [],     # Sent email, no response for 30-59 days
            "recently_sent": [],   # Sent email within last 30 days (new category)
            "never_contacted": [], # No activity at all
            "missing_doi": [],     # Cases without DOI
            "ccp_335_1": []        # Cases over 2 years old without litigation status
        }
        
        import pytz
        # Use timezone-aware datetime for proper comparison
        now = datetime.now(pytz.UTC)
        
        # Import acknowledgment service to filter out acknowledged cases
        from services.case_acknowledgment_service import CaseAcknowledgmentService
        ack_service = CaseAcknowledgmentService()
        
        for pv, case_data in self.data['cases'].items():
            # Skip if case_info is empty (case not in spreadsheet)
            if not case_data.get('case_info') or not case_data['case_info'].get('name'):
                continue
            
            # SKIP ACKNOWLEDGED CASES - they should only appear in Acknowledged tab
            if ack_service.is_acknowledged(str(pv)):
                logger.debug(f"Skipping acknowledged case {pv} from stale analysis")
                continue
            
            # Calculate days since last SENT email (not last contact)
            days_since_sent = None
            if case_data['last_sent']:
                try:
                    from email.utils import parsedate_to_datetime
                    last_sent_date = datetime.fromisoformat(case_data['last_sent'])
                    # Ensure last_sent_date is timezone-aware
                    if last_sent_date.tzinfo is None:
                        import pytz
                        last_sent_date = pytz.UTC.localize(last_sent_date)
                    days_since_sent = (now - last_sent_date).days
                except Exception as e:
                    logger.debug(f"Error calculating days for PV {pv}: {e}")
                    pass
            
            case_summary = {
                "pv": pv,
                "name": case_data['case_info']['name'],
                "law_firm": case_data['case_info']['law_firm'],
                "attorney_email": case_data['case_info']['attorney_email'],
                "doi": case_data['case_info'].get('doi', ''),
                "days_since_sent": days_since_sent,
                "last_sent": case_data['last_sent'],
                "last_contact": case_data['last_contact'],
                "sent_count": case_data['sent_count'],
                "response_count": case_data['response_count']
            }
            
            # Check for missing DOI - specifically look for 2099 placeholder dates
            doi_value = case_data['case_info'].get('doi', '')
            doi_str = str(doi_value).strip() if doi_value else ''
            
            # Only add to missing_doi if it contains '2099' (placeholder date)
            if '2099' in doi_str:
                stale_cases['missing_doi'].append(case_summary)
            
            # Categorize based on email activity
            if case_data['sent_count'] == 0:
                # Never contacted
                stale_cases['never_contacted'].append(case_summary)
            elif case_data['response_count'] == 0:
                # Sent emails but no responses - categorize by time
                if days_since_sent is not None:
                    if days_since_sent >= 90:
                        stale_cases['critical'].append(case_summary)
                    elif days_since_sent >= 60:
                        stale_cases['high_priority'].append(case_summary)
                    elif days_since_sent >= 30:
                        # No response for 30-59 days
                        stale_cases['no_response'].append(case_summary)
                    else:
                        # Sent within last 30 days - new category
                        stale_cases['recently_sent'].append(case_summary)
                else:
                    # No date info, put in recently_sent as it might be new
                    stale_cases['recently_sent'].append(case_summary)
            
            # Check for CCP 335.1 eligibility (use cached result from analyze_from_cache)
            if case_data.get('ccp_335_1_eligible', False):
                # Don't add if already in another category
                already_categorized = any(
                    any(c['pv'] == pv for c in cases)
                    for cat, cases in stale_cases.items()
                    if cat != 'ccp_335_1'
                )
                if not already_categorized:
                    stale_cases['ccp_335_1'].append(case_summary)
                    logger.debug(f"Case {pv} added to CCP 335.1 category from cached analysis")
        
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
    
    def get_comprehensive_stale_cases(self, case_manager, progress_callback=None):
        """Get comprehensive stale case analysis with categories"""
        if progress_callback:
            progress_callback("Loading bootstrap data...", 10)
        
        # Reload tracking data from disk to get latest analysis results
        self.data = self._load_tracking_data()
        
        # Get all stale cases categorized
        stale_categories = self.get_stale_cases()
        
        if progress_callback:
            progress_callback("Processing case categories...", 50)
        
        # Add balance information from case manager
        for category, cases in stale_categories.items():
            for case in cases:
                # Get case details from case manager
                try:
                    # Use column index 1 for PV (second column)
                    case_df = case_manager.df[case_manager.df[1].astype(str) == str(case['pv'])]
                    
                    if not case_df.empty:
                        case_row = case_df.iloc[0]
                        # Column 27 is Balance (AB column)
                        balance_raw = case_row[27] if len(case_row) > 27 else 0
                        if balance_raw:
                            try:
                                balance_str = str(balance_raw).replace('$', '').replace(',', '').strip()
                                if balance_str and balance_str != 'nan' and balance_str != '':
                                    case['balance'] = float(balance_str)
                                else:
                                    case['balance'] = 0
                            except (ValueError, TypeError):
                                case['balance'] = 0
                        else:
                            case['balance'] = 0
                        
                        # Column 2 is Case Status
                        case['status'] = case_row[2] if len(case_row) > 2 else 'Unknown'
                except Exception as e:
                    logger.warning(f"Error getting case details for PV {case.get('pv', 'unknown')}: {e}")
                    case['balance'] = 0
                    case['status'] = 'Unknown'
        
        if progress_callback:
            progress_callback("Analysis complete", 100)
        
        # Log summary
        total_critical = len(stale_categories.get('critical', []))
        total_high = len(stale_categories.get('high_priority', []))
        total_followup = len(stale_categories.get('needs_follow_up', []))
        total_never = len(stale_categories.get('never_contacted', []))
        total_no_response = len(stale_categories.get('no_response', []))
        total_ccp_335_1 = len(stale_categories.get('ccp_335_1', []))
        
        logger.info(f"Stale case analysis complete - Critical: {total_critical}, High: {total_high}, Follow-up: {total_followup}, Never contacted: {total_never}, No response: {total_no_response}, CCP 335.1: {total_ccp_335_1}")
        
        return stale_categories
    
    def clear_stale_cache(self):
        """Clear any cached stale case data to force refresh"""
        # Since we don't have a separate cache, just log
        logger.info("Stale cache cleared (will refresh on next analysis)")
        pass
    
    def mark_case_as_contacted(self, pv, is_sent=False, is_response=False):
        """Immediately update a case's contact status when email is sent or received
        
        Args:
            pv: Case PV number
            is_sent: True if we sent an email
            is_response: True if we received a response
        """
        try:
            pv = str(pv)
            
            # Make sure case exists in tracking data
            if pv not in self.data['cases']:
                logger.warning(f"Case {pv} not found in tracking data")
                return False
            
            case_data = self.data['cases'][pv]
            now = datetime.now().isoformat()
            
            if is_sent:
                # Update sent tracking
                case_data['last_sent'] = now
                case_data['sent_count'] = case_data.get('sent_count', 0) + 1
                case_data['last_contact'] = now
                logger.info(f"Case {pv} marked as contacted (sent email) at {now}")
            
            if is_response:
                # Update response tracking
                case_data['last_response'] = now
                case_data['response_count'] = case_data.get('response_count', 0) + 1
                case_data['last_contact'] = now
                logger.info(f"Case {pv} marked as contacted (received response) at {now}")
            
            # Save updated tracking data immediately
            self._save_tracking_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking case {pv} as contacted: {e}")
            return False
    
    def get_stale_cases_by_category(self, case_manager, category, limit=100):
        """Get specific stale case category for bulk email processing"""
        stale_categories = self.get_comprehensive_stale_cases(case_manager)
        
        if category not in stale_categories:
            return {"cases": [], "total": 0, "category": category}
        
        cases = stale_categories[category]
        
        return {
            "cases": cases[:limit] if limit else cases,
            "total": len(cases),
            "category": category,
            "remaining": max(0, len(cases) - limit) if limit else 0
        }
    
    def get_collections_dashboard(self):
        """Get dashboard summary of collections status"""
        total_cases = len(self.data.get("cases", {}))
        
        # Case status breakdown
        status_counts = {}
        stale_30_days = 0
        stale_60_days = 0
        stale_90_days = 0
        
        for case_pv, case_data in self.data.get("cases", {}).items():
            # Get current status
            status = case_data.get("current_status", "unknown")
            if not status:
                status = "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Check staleness based on last email sent
            last_sent = case_data.get("last_email_sent")
            if last_sent:
                try:
                    # Parse the date - it might be in different formats
                    if isinstance(last_sent, str):
                        # Try ISO format first
                        try:
                            last_sent_date = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                        except:
                            # Try other common formats
                            last_sent_date = datetime.strptime(last_sent[:10], "%Y-%m-%d")
                    else:
                        last_sent_date = last_sent
                    
                    days_since = (datetime.now() - last_sent_date).days
                    
                    if days_since >= 30:
                        stale_30_days += 1
                    if days_since >= 60:
                        stale_60_days += 1
                    if days_since >= 90:
                        stale_90_days += 1
                except Exception as e:
                    logger.debug(f"Error parsing date for case {case_pv}: {e}")
        
        # Get firm statistics (top responsive firms)
        firm_stats = {}
        for case_pv, case_data in self.data.get("cases", {}).items():
            firm = case_data.get("case_info", {}).get("law_firm", "Unknown")
            if firm and firm != "Unknown":
                if firm not in firm_stats:
                    firm_stats[firm] = {
                        "total_cases": 0,
                        "responded_cases": 0,
                        "total_emails": 0,
                        "total_responses": 0
                    }
                
                firm_stats[firm]["total_cases"] += 1
                firm_stats[firm]["total_emails"] += case_data.get("total_emails_sent", 0)
                firm_stats[firm]["total_responses"] += case_data.get("total_responses", 0)
                
                if case_data.get("total_responses", 0) > 0:
                    firm_stats[firm]["responded_cases"] += 1
        
        # Calculate top responsive firms
        top_firms = []
        for firm, stats in firm_stats.items():
            if stats["total_emails"] > 0:
                response_rate = (stats["total_responses"] / stats["total_emails"]) * 100
                top_firms.append((firm, response_rate))
        
        top_firms.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "total_cases": total_cases,
            "status_breakdown": status_counts,
            "stale_cases": {
                "30_days": stale_30_days,
                "60_days": stale_60_days,
                "90_days": stale_90_days
            },
            "top_responsive_firms": top_firms[:5]
        }