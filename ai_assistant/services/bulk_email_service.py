"""
Bulk Email Management Service
Handles batch email processing with approval workflow and test mode
"""

import pandas as pd
import json
import os
import re
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pytz

logger = logging.getLogger(__name__)


class BulkEmailService:
    """Service for bulk email processing with approval workflow"""
    
    def __init__(self, gmail_service, case_manager, ai_service, collections_tracker=None, email_cache_service=None):
        self.gmail_service = gmail_service
        self.case_manager = case_manager
        self.ai_service = ai_service
        self.collections_tracker = collections_tracker
        self.email_cache = email_cache_service
        
        # Test mode configuration
        self.test_mode = False
        self.test_email = "deanh.transcon@gmail.com"
        
        # Initialize priority scoring
        self.firm_scores_file = "data/firm_intelligence.json"
        self.firm_scores = self.load_firm_scores()
        
        # Email generation templates
        self.greetings = [
            "Hello Law Firm,", "Good day Law Firm,", "Greetings Law Firm,",
            "Hi Law Firm,", "Dear Law Firm,"
        ]
        
        self.status_requests = [
            "Has this case settled or is it still pending?",
            "Can you let me know the current status of this case?",
            "Do you happen to have an update on this case?",
            "Is this matter still open or has it been resolved?",
            "Could you please confirm whether the case is resolved or still pending?"
        ]
        
        self.followups = [
            "Let me know if you need bills or reports.",
            "If you need any reports or billing, just let me know.",
            "Feel free to reach out if any bills or documentation are needed.",
            "I'm happy to provide any necessary documents or reports you may need.",
            "We can send over any billing or medical records you might need."
        ]
        
        # Track sent PIDs in this session
        self.session_sent_pids = set()
        self.load_sent_pids()
        
        # Email queue for batch processing
        self.email_queue = []
        self.categorized_cases = {}
        self.categorization_timestamp = None
        self.categorization_cache_duration = 300  # Cache for 5 minutes
    
    def load_sent_pids(self):
        """Load already sent PIDs from log file"""
        self.sent_pids = set()
        log_file = "logs/sent_emails.log"
        
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        # Extract PID from log entries
                        match = re.search(r"PV:\s*(\d+)", line)
                        if match:
                            self.sent_pids.add(match.group(1))
                logger.info(f"Loaded {len(self.sent_pids)} sent PIDs from log")
            except Exception as e:
                logger.error(f"Error loading sent PIDs: {e}")
    
    def load_firm_scores(self):
        """Load historical firm performance data for priority scoring"""
        if os.path.exists(self.firm_scores_file):
            try:
                with open(self.firm_scores_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def calculate_case_priority(self, case_data: Dict) -> int:
        """
        Calculate priority score (0-100) for a case based on collection likelihood
        
        Scoring factors:
        - Firm responsiveness history (0-40 points)
        - Case age sweet spot (0-30 points)
        - Days since last contact (0-20 points)
        - Case value if available (0-10 points)
        """
        score = 0
        
        # 1. Firm responsiveness (0-40 points)
        firm_email = case_data.get('attorney_email', '').lower()
        if firm_email and firm_email in self.firm_scores:
            firm_data = self.firm_scores[firm_email]
            response_rate = firm_data.get('response_rate', 0.5)
            score += int(response_rate * 40)
        else:
            score += 20  # Default middle score for unknown firms
        
        # 2. Case age sweet spot (0-30 points) - Best: 6-18 months old
        doi_raw = case_data.get('doi')
        if doi_raw and str(doi_raw) != "nan" and str(doi_raw) != "NaT":
            try:
                if hasattr(doi_raw, 'date'):
                    doi_date = doi_raw
                else:
                    doi_date = pd.to_datetime(str(doi_raw))
                
                months_old = (datetime.now() - doi_date).days / 30
                
                if 6 <= months_old <= 18:
                    score += 30  # Perfect age
                elif 3 <= months_old < 6:
                    score += 20  # Good but young
                elif 18 < months_old <= 24:
                    score += 20  # Good but aging
                elif 24 < months_old <= 36:
                    score += 10  # Getting old
                # Too young (<3 months) or too old (>36 months) get 0
            except:
                score += 15  # Default for problematic dates
        
        # 3. Days since last contact (0-20 points)
        # Use collections tracker if available
        if self.collections_tracker:
            try:
                activity = self.collections_tracker.get_case_activity(case_data.get('pv'))
                if activity:
                    days_since = activity.get('days_since_last_contact')
                    if days_since:
                        if 20 <= days_since <= 40:
                            score += 20  # Perfect follow-up window
                        elif 40 < days_since <= 60:
                            score += 15  # Good follow-up window
                        elif 60 < days_since <= 90:
                            score += 10  # Needs attention
                        elif days_since > 90:
                            score += 5   # Long overdue
                        # Too recent (<20 days) gets 0 - don't pester
                    else:
                        score += 20  # Never contacted - high priority
            except:
                score += 10  # Default if tracker fails
        else:
            score += 10  # Default without tracker
        
        # 4. Case value (0-10 points) - if available
        # Could be added if billing amount is in the spreadsheet
        
        return min(score, 100)  # Cap at 100
    
    def update_firm_score(self, firm_email: str, responded: bool = False, paid: bool = False):
        """Update firm intelligence based on interactions"""
        firm_email = firm_email.lower()
        
        if firm_email not in self.firm_scores:
            self.firm_scores[firm_email] = {
                'emails_sent': 0,
                'responses': 0,
                'payments': 0,
                'response_rate': 0,
                'payment_rate': 0,
                'last_updated': datetime.now().isoformat()
            }
        
        firm_data = self.firm_scores[firm_email]
        firm_data['emails_sent'] += 1
        
        if responded:
            firm_data['responses'] += 1
        if paid:
            firm_data['payments'] += 1
        
        # Update rates
        if firm_data['emails_sent'] > 0:
            firm_data['response_rate'] = firm_data['responses'] / firm_data['emails_sent']
            firm_data['payment_rate'] = firm_data['payments'] / firm_data['emails_sent']
        
        firm_data['last_updated'] = datetime.now().isoformat()
        
        # Save updated scores
        os.makedirs(os.path.dirname(self.firm_scores_file), exist_ok=True)
        with open(self.firm_scores_file, 'w') as f:
            json.dump(self.firm_scores, f, indent=2)
    
    def set_test_mode(self, enabled: bool, test_email: str = None):
        """Enable or disable test mode"""
        self.test_mode = enabled
        if test_email:
            self.test_email = test_email
        
        status = "ENABLED" if enabled else "DISABLED"
        logger.info(f"Test mode {status}")
        if enabled:
            logger.info(f"Test emails will be sent to: {self.test_email}")
        
        return f"Test mode {status.lower()}. " + (f"Emails will go to: {self.test_email}" if enabled else "")
    
    def needs_recategorization(self) -> bool:
        """Check if we need to recategorize cases"""
        if not self.categorized_cases or not self.categorization_timestamp:
            return True
        
        # Check if cache has expired
        time_since_cache = time.time() - self.categorization_timestamp
        if time_since_cache > self.categorization_cache_duration:
            return True
        
        return False
    
    def force_recategorization(self):
        """Force recategorization on next call"""
        self.categorization_timestamp = None
        self.categorized_cases = {}
        logger.info("Categorization cache cleared - will recategorize on next request")
    
    def set_cache_duration(self, seconds: int):
        """Set cache duration in seconds"""
        self.categorization_cache_duration = seconds
        logger.info(f"Cache duration set to {seconds} seconds")
    
    def get_active_cases(self) -> List[Dict]:
        """Get all active cases with full information including balance"""
        try:
            df = self.case_manager.df
            active_cases = []
            
            for _, row in df.iterrows():
                case_info = self.case_manager.format_case(row)
                
                # Skip non-active cases
                if case_info.get("Status", "").lower() != "active":
                    continue
                
                # Format case data with all needed fields
                # DOI will come through properly from case_manager which reads column E
                case_data = {
                    "pv": case_info.get("PV", ""),
                    "cms": case_info.get("CMS", ""),
                    "name": case_info.get("Name", ""),
                    "doi": case_info.get("DOI", ""),  # This comes from column E (index 4)
                    "attorney_email": case_info.get("Attorney Email", ""),
                    "law_firm": case_info.get("Law Firm", ""),
                    "status": case_info.get("Status", ""),
                    "Balance": case_info.get("Balance", 0.0),
                    "full_case": case_info
                }
                
                active_cases.append(case_data)
            
            # Sort by balance descending
            active_cases.sort(key=lambda x: x.get("Balance", 0.0), reverse=True)
            
            return active_cases
            
        except Exception as e:
            logger.error(f"Error getting active cases: {e}")
            return []
    
    def categorize_cases(self, active_only: bool = True, force_refresh: bool = False, check_ccp_335_1: bool = False, progress_callback=None, progress=None) -> Dict:
        """Categorize cases for bulk processing with caching
        
        Args:
            active_only: Whether to only include active cases
            force_refresh: Force refresh of categorization
            check_ccp_335_1: Whether to check for CCP 335.1 eligibility (slow operation)
            progress_callback: Optional callback function for progress updates (message, percentage)
            progress: Optional ProgressManager for UI updates
        """
        # Check if we can use cached results
        if not force_refresh and not self.needs_recategorization():
            logger.info("Using cached case categorization")
            return self.categorized_cases
        
        logger.info("Starting case categorization...")
        start_time = time.time()
        
        # Import acknowledgment service to filter out acknowledged cases
        from services.case_acknowledgment_service import CaseAcknowledgmentService
        ack_service = CaseAcknowledgmentService()
        
        try:
            df = self.case_manager.df
            total_cases = len(df)
            
            if progress:
                progress.set_message("Initializing categories...")
                progress.update(0)
                progress.log("📂 Analyzing case data...")
            elif progress_callback:
                progress_callback("Initializing categories...", 0)
            
            categories = {
                "critical": [],  # 90+ days no response
                "high_priority": [],  # 60+ days no response
                "needs_follow_up": [],  # 30+ days no response
                "no_response": [],  # Sent but no response (under 30 days)
                "never_contacted": [],  # Never sent any emails
                "missing_doi": [],  # Cases with missing DOI
                "ccp_335_1": [],  # Cases needing CCP 335.1 statute inquiry
                "by_firm": {},  # Organized by law firm
                "high_value": [],  # Cases with high balance
                "ready_to_close": []  # Cases that might be ready for settlement
            }
            
            for idx, row in df.iterrows():
                # Update progress
                if progress and idx % 10 == 0:  # Update every 10 cases
                    percentage = int((idx / total_cases) * 100)
                    progress.update(percentage, f"Processing case {idx+1} of {total_cases}")
                    progress.log(f"Analyzing PV {row.get('pv', 'Unknown')}...")
                    progress.process_events()  # Keep UI responsive
                elif progress_callback and idx % 10 == 0:  # Update every 10 cases
                    percentage = int((idx / total_cases) * 100)
                    progress_callback(f"Processing case {idx}/{total_cases}...", percentage)
                
                case_info = self.case_manager.format_case(row)
                
                # Skip if not active (if filtering)
                if active_only:
                    status = str(case_info.get("Status", "")).lower()
                    if status != "active":
                        continue
                
                pv = str(case_info.get("PV", ""))
                
                # Skip already sent cases
                if pv in self.sent_pids or pv in self.session_sent_pids:
                    continue
                
                # Skip acknowledged cases - they should only appear in Acknowledged tab
                if ack_service.is_acknowledged(pv):
                    logger.debug(f"Skipping acknowledged case {pv} from categorization")
                    continue
                
                # Create case data object
                case_data = {
                    "pv": pv,
                    "name": case_info.get("Name", ""),
                    "doi": case_info.get("DOI", ""),
                    "cms": case_info.get("CMS", ""),
                    "attorney_email": case_info.get("Attorney Email", ""),
                    "law_firm": case_info.get("Law Firm", ""),
                    "status": case_info.get("Status", ""),
                    "full_case": case_info
                }
                
                # Categorize by missing DOI - ONLY 2099 dates should be considered missing
                doi_raw = case_data["doi"]
                doi_str = str(doi_raw).strip() if doi_raw else ""
                
                # Only consider 2099 dates as truly missing DOI
                if "2099" in doi_str:
                    categories["missing_doi"].append(case_data)
                # Empty or invalid dates go to a different category if needed
                elif not doi_raw or doi_str in ["nan", "NaT", ""]:
                    # These have blank DOI fields but aren't the 2099 placeholder
                    # Still add to missing_doi but could be separated if needed
                    pass  # Don't add to missing_doi unless it's specifically 2099
                
                # Categorize by firm NAME (not email)
                firm_name = case_data["law_firm"]
                if firm_name and firm_name.strip():
                    if firm_name not in categories["by_firm"]:
                        categories["by_firm"][firm_name] = []
                    categories["by_firm"][firm_name].append(case_data)
                
                # Check for old cases (>2 years) and CCP 335.1 eligibility
                if doi_raw and doi_str != "2099" and doi_str != "nan" and doi_str != "NaT":
                    try:
                        # Handle datetime object or string
                        if hasattr(doi_raw, 'year'):
                            # It's already a datetime object
                            doi_date = doi_raw
                        else:
                            # Parse string to datetime
                            doi_str_clean = doi_str.split()[0] if ' ' in doi_str else doi_str
                            doi_date = pd.to_datetime(doi_str_clean)
                        
                        years_old = (datetime.now() - doi_date).days / 365
                        if years_old > 2:
                            categories["old_cases"].append(case_data)
                            
                            # Only check CCP 335.1 eligibility if explicitly requested
                            # This is a slow operation that checks email cache
                            if check_ccp_335_1:
                                # Check CCP 335.1 eligibility
                                # CCP 335.1: DOI > 2 years old AND no pending litigation
                                status = str(case_data.get("status", "")).lower()
                                
                                # Check for litigation keywords that would EXCLUDE from CCP 335.1
                                litigation_keywords = ['pending', 'litigation', 'prelitigation', 'pre-litigation', 
                                                     'settled', 'settlement', 'litigating', 'suit', 'lawsuit']
                                has_litigation_keyword = any(keyword in status for keyword in litigation_keywords)
                                
                                # Check if we have NOT heard from firm (would need collections tracker data)
                                # For now, just check DOI age and status keywords
                                if not has_litigation_keyword:
                                    categories["ccp_335_1"].append(case_data)
                                    logger.debug(f"Case {pv} added to CCP 335.1 category - DOI: {years_old:.1f} years old")
                    except Exception as e:
                        logger.debug(f"Error processing DOI for case {pv}: {e}")
                
                # Note: Time-based categories (critical, high_priority, needs_follow_up, no_response)
                # are handled by the collections tracker and pulled in prepare_batch()
            
            # Cache the results
            self.categorized_cases = categories
            self.categorization_timestamp = time.time()
            
            # Log category statistics
            elapsed_time = time.time() - start_time
            logger.info(f"Case categorization complete in {elapsed_time:.2f} seconds:")
            logger.info(f"  ⚖️ CCP 335.1 (>2yr statute): {len(categories['ccp_335_1'])}")
            logger.info(f"  ❓ Missing DOI: {len(categories['missing_doi'])}")
            logger.info(f"  💰 High value cases: {len(categories['high_value'])}")
            logger.info(f"  Unique firms: {len(categories['by_firm'])}")
            
            return categories
            
        except Exception as e:
            logger.error(f"Error categorizing cases: {e}")
            raise
    
    def generate_email_content(self, case_data: Dict, email_type: str = "standard") -> Dict:
        """Generate email content for a case"""
        try:
            # Check if this is a CCP 335.1 email
            if email_type == "ccp_335_1":
                # Generate CCP 335.1 statute of limitations inquiry
                # Convert name to title case for proper capitalization
                name_title_case = ' '.join(word.capitalize() for word in str(case_data.get('name', 'Patient')).split())
                subject = f"CCP 335.1 Statute of Limitations Inquiry - {name_title_case} (PV: {case_data.get('pv', '')})"
                
                doi = case_data.get('doi', '')
                body = f"""Dear Counsel,

I am writing to inquire about the current status of the above-referenced case.

Our records indicate that the date of injury for this matter was {doi}, which is now over two years ago. Under California Code of Civil Procedure Section 335.1, the statute of limitations for personal injury claims is generally two years from the date of injury.

Could you please provide an update on:
1. Whether litigation has been filed in this matter
2. The current status of any settlement negotiations
3. Whether there are any tolling agreements or other factors that would extend the statute of limitations

We need this information to properly manage our lien and determine next steps. If the statute of limitations has expired without litigation being filed, please advise how you intend to proceed with this matter.

Please respond at your earliest convenience so we can update our records accordingly.

Thank you for your attention to this matter.
"""
                
                # Modify for test mode
                original_to = case_data["attorney_email"]
                to_email = self.test_email if self.test_mode else original_to
                if self.test_mode:
                    subject = f"[TEST MODE - Original To: {original_to}] {subject}"
                
                return {
                    "pv": case_data["pv"],
                    "to": to_email,
                    "original_to": original_to,
                    "subject": subject,
                    "body": body,
                    "name": case_data["name"],
                    "doi": case_data["doi"],
                    "case_data": case_data,
                    "email_type": "ccp_335_1"
                }
            
            # Standard email generation
            name = case_data["name"].title() if case_data["name"] else "UNKNOWN"
            
            # Handle DOI as either string or datetime object
            doi_raw = case_data.get("doi")
            doi = ""
            is_unknown_doi = False
            
            if doi_raw:
                doi_str = str(doi_raw).strip()
                
                # Check if it's specifically the 2099 placeholder date
                if "2099" in doi_str:
                    is_unknown_doi = True
                    doi = ""
                elif doi_str and doi_str not in ["nan", "NaT", ""]:
                    # Valid date - format it properly
                    if hasattr(doi_raw, 'strftime'):
                        # It's a datetime object
                        doi = doi_raw.strftime("%m/%d/%Y")
                    else:
                        # It's a string - try to parse and format it
                        try:
                            # Remove time component if present
                            date_part = doi_str.split()[0] if ' ' in doi_str else doi_str
                            # Try to parse and reformat
                            import pandas as pd
                            parsed_date = pd.to_datetime(date_part)
                            doi = parsed_date.strftime("%m/%d/%Y")
                        except:
                            # If parsing fails, use the original string
                            doi = date_part
            
            pv = case_data["pv"]
            attorney_email = case_data["attorney_email"]
            
            # Random selection for variety
            greeting = random.choice(self.greetings)
            status_line = random.choice(self.status_requests)
            followup_line = random.choice(self.followups)
            
            # Subject line based on DOI availability
            # ONLY mark as UNKNOWN if it's specifically a 2099 date
            if is_unknown_doi:
                subject = f"{name} UNKNOWN DOI // Prohealth Advanced Imaging"
                extra_line = "\n\nCould you please provide the accurate date of loss for this case?"
            elif doi:
                subject = f"{name} DOI {doi} // Prohealth Advanced Imaging"
                extra_line = ""
            else:
                # If we truly don't have a DOI (empty field), still include it but don't mark as UNKNOWN
                subject = f"{name} // Prohealth Advanced Imaging"
                extra_line = "\n\nCould you please provide the date of loss for this case?"
            
            # Modify for test mode
            original_to = attorney_email
            if self.test_mode:
                attorney_email = self.test_email
                subject = f"[TEST MODE - Original To: {original_to}] {subject}"
            
            # Email body
            body = f"""{greeting}

In regards to Prohealth Advanced Imaging billing and liens for {name}.

{status_line} {followup_line}{extra_line}

Thank you.

Reference #: {pv}"""
            
            return {
                "pv": pv,
                "to": attorney_email,
                "original_to": original_to if self.test_mode else attorney_email,
                "subject": subject,
                "body": body,
                "name": name,
                "doi": doi,
                "case_data": case_data
            }
            
        except Exception as e:
            logger.error(f"Error generating email for case {case_data.get('pv')}: {e}")
            raise
    
    def prepare_batch(self, category: str, subcategory: str = None, limit: int = None) -> List[Dict]:
        """Prepare a batch of emails for review and approval"""
        try:
            emails = []
            
            # If CCP 335.1 category is requested, ensure we run the check
            if category == "ccp_335_1":
                # Force recategorization with CCP 335.1 check enabled
                logger.info("CCP 335.1 category requested - running eligibility checks...")
                self.categorize_cases(force_refresh=True, check_ccp_335_1=True)
            
            # Check if this is a stale case category (from collections tracker)
            stale_categories = ["critical", "high_priority", "no_response", "recently_sent", "never_contacted", "missing_doi"]
            
            # CCP 335.1 can come from either collections tracker or bulk email categorization
            if category == "ccp_335_1":
                # Try to get from collections tracker first
                if self.collections_tracker:
                    logger.info(f"Getting CCP 335.1 cases from collections tracker...")
                    stale_data = self.collections_tracker.get_stale_cases_by_category(
                        self.case_manager, "ccp_335_1", limit=limit or 100
                    )
                    cases = stale_data.get("cases", [])
                    
                    # Format cases from collections tracker
                    if cases:
                        from services.case_acknowledgment_service import CaseAcknowledgmentService
                        ack_service = CaseAcknowledgmentService()
                        
                        formatted_cases = []
                        for stale_case in cases:
                            pv = stale_case.get("pv")
                            
                            # Skip acknowledged cases
                            if ack_service.is_acknowledged(pv):
                                logger.info(f"Skipping acknowledged CCP 335.1 case {pv}")
                                continue
                            
                            formatted_case = {
                                "pv": pv,
                                "name": stale_case.get("name"),
                                "doi": stale_case.get("doi", ""),
                                "cms": "",  # Will be fetched from case manager
                                "attorney_email": stale_case.get("attorney_email"),
                                "law_firm": stale_case.get("law_firm"),
                                "status": stale_case.get("status", ""),
                                "days_since_sent": stale_case.get("days_since_sent"),
                                "response_count": stale_case.get("response_count", 0)
                            }
                            
                            # Fetch full case details from case manager
                            try:
                                df = self.case_manager.df
                                case_row = df[df[1].astype(str) == str(pv)]
                                if not case_row.empty:
                                    full_case = self.case_manager.format_case(case_row.iloc[0])
                                    formatted_case["doi"] = full_case.get("DOI", "")
                                    formatted_case["cms"] = full_case.get("CMS", "")
                                    formatted_case["full_case"] = full_case
                            except:
                                pass
                            
                            formatted_cases.append(formatted_case)
                        
                        cases = formatted_cases
                    
                # If no cases from tracker, use bulk email categorization
                if not cases:
                    logger.info("No CCP 335.1 cases from tracker, using bulk email categorization...")
                    cases = self.categorized_cases.get("ccp_335_1", [])
                
                logger.info(f"Found {len(cases)} CCP 335.1 cases")
            elif category in stale_categories:
                # Get stale cases from collections tracker
                if self.collections_tracker:
                    logger.info(f"Getting {category} cases from collections tracker...")
                    stale_data = self.collections_tracker.get_stale_cases_by_category(
                        self.case_manager, category, limit=limit or 100
                    )
                    cases = stale_data.get("cases", [])
                    logger.info(f"Found {len(cases)} cases in {category} category")
                    
                    # Convert stale case format to standard format and filter acknowledged
                    from services.case_acknowledgment_service import CaseAcknowledgmentService
                    ack_service = CaseAcknowledgmentService()
                    
                    formatted_cases = []
                    for stale_case in cases:
                        pv = stale_case.get("pv")
                        
                        # Skip acknowledged cases
                        if ack_service.is_acknowledged(pv):
                            logger.info(f"Skipping acknowledged case {pv}")
                            continue
                        
                        formatted_case = {
                            "pv": pv,
                            "name": stale_case.get("name"),
                            "doi": "",  # Will be fetched from case manager
                            "cms": "",  # Will be fetched from case manager
                            "attorney_email": stale_case.get("attorney_email"),
                            "law_firm": stale_case.get("law_firm"),
                            "status": "",
                            "days_since_contact": stale_case.get("days_since_contact"),
                            "response_count": stale_case.get("response_count", 0)
                        }
                        
                        # Fetch full case details from case manager
                        try:
                            pv = stale_case.get("pv")
                            df = self.case_manager.df
                            case_row = df[df[1].astype(str) == str(pv)]
                            if not case_row.empty:
                                full_case = self.case_manager.format_case(case_row.iloc[0])
                                formatted_case["doi"] = full_case.get("DOI", "")
                                formatted_case["cms"] = full_case.get("CMS", "")
                                formatted_case["full_case"] = full_case
                        except:
                            pass
                        
                        formatted_cases.append(formatted_case)
                    
                    cases = formatted_cases
                else:
                    logger.warning("Collections tracker not available for stale case categories")
                    cases = []
            elif category == "by_firm" and subcategory:
                # Get cases for specific firm
                cases = self.categorized_cases.get("by_firm", {}).get(subcategory, [])
            else:
                # Get cases for category
                cases = self.categorized_cases.get(category, [])
            
            # Filter out acknowledged cases for non-stale categories
            if category not in stale_categories:
                from services.case_acknowledgment_service import CaseAcknowledgmentService
                ack_service = CaseAcknowledgmentService()
                
                filtered_cases = []
                for case in cases:
                    pv = case.get("pv")
                    if ack_service.is_acknowledged(pv):
                        logger.info(f"Skipping acknowledged case {pv}")
                        continue
                    filtered_cases.append(case)
                cases = filtered_cases
            
            # Apply limit if specified
            if limit:
                cases = cases[:limit]
            
            # Generate email content for each case
            for case in cases:
                try:
                    # Check if this is CCP 335.1 category
                    if category == "ccp_335_1":
                        email = self.generate_email_content(case, email_type="ccp_335_1")
                    else:
                        email = self.generate_email_content(case)
                    emails.append(email)
                except Exception as e:
                    logger.error(f"Error generating email for case {case.get('pv')}: {e}")
                    continue
            
            self.email_queue = emails
            return emails
            
        except Exception as e:
            logger.error(f"Error preparing batch: {e}")
            raise
    
    def display_batch_preview(self, emails: List[Dict]) -> str:
        """Display preview of email batch"""
        output = []
        output.append(f"\n📧 BATCH PREVIEW - {len(emails)} emails")
        output.append("=" * 60)
        
        if self.test_mode:
            output.append(f"⚠️  TEST MODE: All emails will be sent to {self.test_email}")
            output.append("")
        
        for i, email in enumerate(emails[:10], 1):  # Show first 10
            output.append(f"[{i}] PV: {email['pv']} - {email['name']}")
            output.append(f"    To: {email['to']}")
            if self.test_mode:
                output.append(f"    (Original: {email['original_to']})")
            output.append(f"    Subject: {email['subject'][:50]}...")
            output.append(f"    DOI: {email['doi'] or 'UNKNOWN'}")
            output.append("")
        
        if len(emails) > 10:
            output.append(f"... and {len(emails) - 10} more emails")
        
        return "\n".join(output)
    
    def get_approval_for_batch(self, emails: List[Dict]) -> Tuple[List[Dict], str]:
        """Interactive approval process for email batch"""
        approved = []
        action = ""
        
        print(self.display_batch_preview(emails))
        
        print("\n" + "=" * 60)
        print("BATCH APPROVAL OPTIONS:")
        print("  [A] Approve ALL and send")
        print("  [S] Select specific emails to send (by number)")
        print("  [R] Review individual emails in detail")
        print("  [E] Edit email template and regenerate")
        print("  [X] Skip this entire batch")
        print("=" * 60)
        
        choice = input("\nYour choice: ").strip().upper()
        
        if choice == "A":
            approved = emails
            action = "approved_all"
            
        elif choice == "S":
            print("\nEnter email numbers to send (e.g., 1,3,5-8,10):")
            selection = input("Selection: ").strip()
            
            selected_indices = []
            for part in selection.split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    selected_indices.extend(range(start-1, end))
                else:
                    selected_indices.append(int(part)-1)
            
            approved = [emails[i] for i in selected_indices if 0 <= i < len(emails)]
            action = "selected"
            
        elif choice == "R":
            # Individual review
            for i, email in enumerate(emails, 1):
                print(f"\n[{i}/{len(emails)}] Review Email:")
                print("-" * 40)
                print(f"To: {email['to']}")
                print(f"Subject: {email['subject']}")
                print(f"\n{email['body']}")
                print("-" * 40)
                
                approve = input("Send this email? (Y/n/skip remaining): ").strip().lower()
                if approve == "y" or approve == "":
                    approved.append(email)
                elif approve == "skip":
                    break
            
            action = "reviewed"
            
        else:
            action = "skipped"
        
        return approved, action
    
    def send_batch(self, emails: List[Dict], add_cms_notes: bool = True) -> Dict:
        """Send approved batch of emails"""
        results = {
            "sent": [],
            "failed": [],
            "total": len(emails)
        }
        
        try:
            print(f"\n🚀 Sending {len(emails)} emails...")
            if self.test_mode:
                print(f"⚠️  TEST MODE: All emails going to {self.test_email}")
            
            for i, email in enumerate(emails, 1):
                try:
                    # Send email using Gmail service
                    msg_id = self.gmail_service.send_email(
                        email["to"],
                        email["subject"],
                        email["body"]
                    )
                    
                    if self.test_mode:
                        print(f"✅ [{i}/{len(emails)}] TEST SENT to {email['to']} (PV: {email['pv']})")
                        print(f"    (Original recipient: {email.get('original_to', 'N/A')})")
                    else:
                        print(f"✅ [{i}/{len(emails)}] Sent to {email['to']} (PV: {email['pv']})")
                    
                    # Only update tracking if NOT in test mode
                    if not self.test_mode:
                        # Log success to permanent logs
                        self.log_sent_email(email, msg_id)
                        
                        # Track in session
                        self.session_sent_pids.add(email['pv'])
                        
                        # Update collections tracker IMMEDIATELY
                        if self.collections_tracker and hasattr(self.collections_tracker, 'mark_case_as_contacted'):
                            try:
                                pv = email['pv']
                                # This updates last_sent date and moves case to appropriate category
                                self.collections_tracker.mark_case_as_contacted(pv, is_sent=True, is_response=False)
                                logger.info(f"Collections tracker updated immediately for PV {pv}")
                            except Exception as e:
                                logger.warning(f"Failed to update collections tracker for PV {pv}: {e}")
                        
                        # Add CMS note for production
                        if add_cms_notes:
                            try:
                                self.add_cms_note(email["case_data"], "bulk_status_request", email["to"])
                            except Exception as e:
                                logger.error(f"Failed to add CMS note for PV {email['pv']}: {e}")
                    else:
                        # In test mode, log to test log (doesn't affect tracking)
                        self.log_test_email(email, msg_id)
                        
                        # Add CMS note for test mode (marked as TEST)
                        if add_cms_notes:
                            try:
                                # Add test CMS note with special marker
                                # Pass the original recipient, not the test email
                                original_recipient = email.get("original_to", email["to"])
                                self.add_cms_test_note(email["case_data"], original_recipient)
                            except Exception as e:
                                logger.error(f"Failed to add TEST CMS note for PV {email['pv']}: {e}")
                    
                    # Add to results (for both test and production)
                    results["sent"].append({
                        "pv": email["pv"],
                        "to": email["to"],
                        "msg_id": msg_id,
                        "test_mode": self.test_mode
                    })
                    
                    # Brief delay between sends
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"❌ [{i}/{len(emails)}] Failed PV {email['pv']}: {e}")
                    logger.error(f"Failed to send email for PV {email['pv']}: {e}")
                    results["failed"].append({
                        "pv": email["pv"],
                        "error": str(e)
                    })
            
            # Summary
            print(f"\n📊 Batch Complete:")
            if self.test_mode:
                print(f"   🧪 TEST MODE - Categories preserved")
                print(f"   📝 TEST CMS notes queued for processing")
            print(f"   ✅ Sent: {len(results['sent'])}")
            print(f"   ❌ Failed: {len(results['failed'])}")
            
            # Remind about CMS notes if any were added
            if len(results['sent']) > 0 and add_cms_notes:
                print("\n⚠️  REMINDER: CMS notes are queued for batch processing")
                print("   Run 'add session cms notes' command to add them to CMS")
            
            # Only invalidate stale cache if NOT in test mode
            # This preserves categories for test runs
            if self.collections_tracker and len(results["sent"]) > 0 and not self.test_mode:
                self.collections_tracker.invalidate_stale_case_cache()
                print("🔄 Case categories refreshed")
            
            return results
            
        except Exception as e:
            logger.error(f"Error sending batch: {e}")
            raise
    
    def log_sent_email(self, email: Dict, msg_id: str):
        """Log sent email to file (production only)"""
        try:
            from utils.logging_config import log_sent_email
            
            # Use existing logging function
            log_sent_email(
                email["pv"],
                email["to"],
                email["subject"],
                msg_id
            )
                
        except Exception as e:
            logger.error(f"Error logging sent email: {e}")
    
    def log_test_email(self, email: Dict, msg_id: str):
        """Log test email to separate test log file"""
        try:
            test_log_file = "logs/test_emails.log"
            os.makedirs(os.path.dirname(test_log_file), exist_ok=True)
            
            log_entry = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"TEST MODE | PV: {email['pv']} | "
                f"Test To: {email['to']} | "
                f"Original To: {email.get('original_to', 'N/A')} | "
                f"Subject: {email['subject']} | "
                f"Gmail ID: {msg_id}\n"
            )
            
            with open(test_log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            
            logger.info(f"TEST MODE: Email for PV {email['pv']} logged to test log")
            
        except Exception as e:
            logger.error(f"Error logging test email: {e}")
    
    def add_cms_note(self, case: Dict, note_type: str, recipient: str):
        """Add CMS note for sent email"""
        try:
            from services.cms_integration import add_cms_note_for_email
            import asyncio
            
            # Run async CMS note addition
            success = asyncio.run(add_cms_note_for_email(case, note_type, recipient))
            
            if success:
                logger.info(f"CMS note added for PV {case.get('PV')}")
            else:
                logger.warning(f"Failed to add CMS note for PV {case.get('PV')}")
                
        except Exception as e:
            logger.error(f"Error adding CMS note: {e}")
    
    def add_cms_test_note(self, case: Dict, original_recipient: str):
        """Add CMS note for test email (marked as TEST)"""
        try:
            from services.cms_integration import add_cms_note_for_email
            import asyncio
            
            # Need to make sure we have the right case structure
            # The case might have lowercase keys from bulk processing
            test_case = {
                "CMS": case.get("cms") or case.get("CMS") or case.get("pv") or case.get("PV"),
                "PV": case.get("pv") or case.get("PV"),
                "Name": case.get("name") or case.get("Name"),
                "DOI": case.get("doi") or case.get("DOI")
            }
            
            # Create detailed test mode description
            test_description = f"TEST MODE - Email sent to {self.test_email} (intended for {original_recipient})"
            
            # Add TEST marker to the note type
            success = asyncio.run(add_cms_note_for_email(
                test_case, 
                "test_bulk_status_request",  # Special test note type
                test_description
            ))
            
            if success:
                logger.info(f"TEST CMS note queued for PV {test_case.get('PV')}")
                print(f"📝 TEST CMS note queued for PV {test_case.get('PV')}")
            else:
                logger.warning(f"Failed to queue TEST CMS note for PV {test_case.get('PV')}")
                print(f"⚠️  TEST CMS note queue failed for PV {test_case.get('PV')}")
                
        except Exception as e:
            logger.error(f"Error adding TEST CMS note: {e}")
            print(f"❌ TEST CMS note error: {e}")
    
    def get_statistics(self) -> Dict:
        """Get current bulk processing statistics"""
        # Count test emails sent
        test_email_count = 0
        if os.path.exists("logs/test_emails.log"):
            try:
                with open("logs/test_emails.log", "r", encoding="utf-8") as f:
                    test_email_count = len(f.readlines())
            except:
                pass
        
        stats = {
            "test_mode": self.test_mode,
            "test_email": self.test_email if self.test_mode else None,
            "session_sent_production": len(self.session_sent_pids),
            "total_sent_production": len(self.sent_pids) + len(self.session_sent_pids),
            "test_emails_sent": test_email_count,
            "categories": {}
        }
        
        if self.categorized_cases:
            for category, cases in self.categorized_cases.items():
                if category == "by_firm":
                    stats["categories"][category] = {
                        "firms": len(cases),
                        "total_cases": sum(len(firm_cases) for firm_cases in cases.values())
                    }
                else:
                    stats["categories"][category] = len(cases)
        
        return stats
    
    def prepare_batch_from_numbers(self, numbers: List[str]) -> List[Dict]:
        """Prepare batch of emails from a list of PV or CMS numbers"""
        try:
            emails = []
            not_found = []
            already_sent = []
            
            df = self.case_manager.df
            
            for num in numbers:
                num = num.strip()
                if not num:
                    continue
                
                # Search for matching case by PV or CMS
                case_found = False
                
                # Try PV match first
                pv_match = df[df[1].astype(str) == num]
                if not pv_match.empty:
                    case_found = True
                    row = pv_match.iloc[0]
                else:
                    # Try CMS match
                    cms_match = df[df['CMS'].astype(str) == num]
                    if not cms_match.empty:
                        case_found = True
                        row = cms_match.iloc[0]
                
                if case_found:
                    case_info = self.case_manager.format_case(row)
                    pv = str(case_info.get("PV", ""))
                    
                    # Check if already sent
                    if pv in self.sent_pids or pv in self.session_sent_pids:
                        already_sent.append(f"{num} (PV: {pv})")
                        continue
                    
                    # Create case data object
                    case_data = {
                        "pv": pv,
                        "name": case_info.get("Name", ""),
                        "doi": case_info.get("DOI", ""),
                        "cms": case_info.get("CMS", ""),
                        "attorney_email": case_info.get("Attorney Email", ""),
                        "law_firm": case_info.get("Law Firm", ""),
                        "status": case_info.get("Status", ""),
                        "full_case": case_info
                    }
                    
                    # Calculate priority score
                    priority_score = self.calculate_case_priority(case_data)
                    case_data["priority_score"] = priority_score
                    
                    # Generate email content
                    try:
                        email = self.generate_email_content(case_data)
                        emails.append(email)
                    except Exception as e:
                        logger.error(f"Error generating email for {num}: {e}")
                        not_found.append(f"{num} (error generating email)")
                else:
                    not_found.append(num)
            
            # Sort emails by priority score
            emails.sort(key=lambda x: x.get("case_data", {}).get("priority_score", 0), reverse=True)
            
            # Report results
            print(f"\n📊 Batch preparation results:")
            print(f"   ✅ Found and prepared: {len(emails)} emails")
            if already_sent:
                print(f"   ⏭️  Already sent (skipped): {len(already_sent)}")
                for item in already_sent[:5]:  # Show first 5
                    print(f"      - {item}")
                if len(already_sent) > 5:
                    print(f"      ... and {len(already_sent) - 5} more")
            if not_found:
                print(f"   ❌ Not found: {len(not_found)}")
                for item in not_found[:5]:  # Show first 5
                    print(f"      - {item}")
                if len(not_found) > 5:
                    print(f"      ... and {len(not_found) - 5} more")
            
            self.email_queue = emails
            return emails
            
        except Exception as e:
            logger.error(f"Error preparing batch from numbers: {e}")
            raise
    
    def export_batch_for_review(self, emails: List[Dict], filepath: str = None) -> str:
        """Export batch to file for external review"""
        try:
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"data/bulk_batch_{timestamp}.json"
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "test_mode": self.test_mode,
                "count": len(emails),
                "emails": [
                    {
                        "pv": e["pv"],
                        "name": e["name"],
                        "to": e["to"],
                        "subject": e["subject"],
                        "body": e["body"],
                        "doi": e["doi"],
                        "priority_score": e.get("case_data", {}).get("priority_score", 0)
                    }
                    for e in emails
                ]
            }
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported {len(emails)} emails to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting batch: {e}")
            raise