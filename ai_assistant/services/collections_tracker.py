import json
import os
import logging
from datetime import datetime, timedelta
import re
from config import Config

logger = logging.getLogger(__name__)

def parse_sent_emails_log():
    """Parse the sent emails log file and return recent email data by PV"""
    sent_emails = {}
    sent_log_file = Config.get_file_path("logs/sent_emails.log")
    
    try:
        if not os.path.exists(sent_log_file):
            return sent_emails
            
        with open(sent_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or 'PV:' not in line:
                    continue
                    
                # Parse format: [2025-08-07 22:27:31] PV: 277922 | To: EMAIL | Subject: SUBJECT
                try:
                    # Extract timestamp
                    timestamp_match = re.search(r'\[([^\]]+)\]', line)
                    if not timestamp_match:
                        continue
                    timestamp_str = timestamp_match.group(1)
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Extract PV
                    pv_match = re.search(r'PV:\s*(\w+)', line)
                    if not pv_match:
                        continue
                    pv = pv_match.group(1)
                    
                    # Keep track of most recent email per PV
                    if pv not in sent_emails or timestamp > sent_emails[pv]['timestamp']:
                        sent_emails[pv] = {
                            'timestamp': timestamp,
                            'line': line
                        }
                        
                except Exception as e:
                    logger.debug(f"Failed to parse sent email log line '{line}': {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error reading sent emails log: {e}")
        
    return sent_emails

def parse_timezone_aware_date(date_string):
    """Parse timezone-aware ISO date string to naive datetime for comparison"""
    try:
        # Handle timezone offset formats like +00:00, -07:00, -08:00
        if '+' in date_string or date_string.count('-') > 2:
            # Remove timezone info to make it naive for comparison
            date_part = re.sub(r'[+-]\d{2}:\d{2}$', '', date_string)
            return datetime.fromisoformat(date_part)
        else:
            return datetime.fromisoformat(date_string)
    except Exception as e:
        logger.debug(f"Failed to parse date '{date_string}': {e}")
        return None

class CollectionsTracker:
    """Track case statuses, responses, and collections activities"""
    
    def __init__(self):
        self.tracker_file = Config.get_file_path("data/collections_tracking.json")
        self.data = self._load_tracking_data()
    
    def _load_tracking_data(self):
        """Load tracking data from file"""
        try:
            if os.path.exists(self.tracker_file):
                with open(self.tracker_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"cases": {}, "firm_stats": {}}
        except Exception as e:
            logger.error(f"Error loading tracking data: {e}")
            return {"cases": {}, "firm_stats": {}}
    
    def _save_tracking_data(self):
        """Save tracking data to file"""
        try:
            os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
            with open(self.tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving tracking data: {e}")
    
    def log_case_activity(self, case_pv, activity_type, details=None):
        """
        Log case activity
        
        Args:
            case_pv (str): Case PV number
            activity_type (str): 'email_sent', 'response_received', 'status_updated'
            details (dict): Additional details about the activity
        """
        if case_pv not in self.data["cases"]:
            self.data["cases"][case_pv] = {
                "activities": [],
                "current_status": "unknown",
                "last_contact": None,
                "response_count": 0,
                "firm_email": None
            }
        
        activity = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,
            "details": details or {}
        }
        
        self.data["cases"][case_pv]["activities"].append(activity)
        
        # Update case metadata based on activity
        if activity_type == "email_sent":
            # Use the actual email date if provided, otherwise use current time
            if details and details.get("sent_date"):
                self.data["cases"][case_pv]["last_contact"] = details["sent_date"]
            else:
                self.data["cases"][case_pv]["last_contact"] = datetime.now().isoformat()
                
            if details and details.get("recipient_email"):
                self.data["cases"][case_pv]["firm_email"] = details["recipient_email"]
        
        elif activity_type == "email_received":
            # Received emails also count as contact and increment response count
            if details and details.get("received_date"):
                # Update last_contact if this received email is more recent
                current_last = self.data["cases"][case_pv].get("last_contact")
                received_date = details["received_date"]
                if not current_last or received_date > current_last:
                    self.data["cases"][case_pv]["last_contact"] = received_date
            
            self.data["cases"][case_pv]["response_count"] += 1
            if details and details.get("sender_email"):
                self.data["cases"][case_pv]["firm_email"] = details["sender_email"]
        
        elif activity_type == "response_received":
            self.data["cases"][case_pv]["response_count"] += 1
            if details and details.get("status"):
                self.data["cases"][case_pv]["current_status"] = details["status"]
        
        self._save_tracking_data()
        logger.info(f"Logged {activity_type} for case {case_pv}")
    
    def get_case_status(self, case_pv):
        """Get current status and activity summary for a case"""
        if case_pv not in self.data["cases"]:
            return {
                "status": "unknown",
                "last_contact": None,
                "days_since_contact": None,
                "response_count": 0,
                "activities": []
            }
        
        case_data = self.data["cases"][case_pv]
        
        # Calculate days since last contact
        days_since_contact = None
        if case_data.get("last_contact"):
            try:
                last_contact = datetime.fromisoformat(case_data["last_contact"])
                days_since_contact = (datetime.now() - last_contact).days
            except:
                pass
        
        return {
            "status": case_data.get("current_status", "unknown"),
            "last_contact": case_data.get("last_contact"),
            "days_since_contact": days_since_contact,
            "response_count": case_data.get("response_count", 0),
            "activities": case_data.get("activities", [])[-5:],  # Last 5 activities
            "firm_email": case_data.get("firm_email")
        }
    
    def get_stale_cases(self, days_threshold=30):
        """Get cases that haven't been contacted in X days"""
        stale_cases = []
        
        for case_pv, case_data in self.data["cases"].items():
            if not case_data.get("last_contact"):
                continue
            
            try:
                last_contact = datetime.fromisoformat(case_data["last_contact"])
                days_since = (datetime.now() - last_contact).days
                
                if days_since >= days_threshold:
                    stale_cases.append({
                        "pv": case_pv,
                        "days_since_contact": days_since,
                        "status": case_data.get("current_status", "unknown"),
                        "firm_email": case_data.get("firm_email")
                    })
            except:
                continue
        
        # Sort by days since contact (most stale first, handle None values)
        stale_cases.sort(key=lambda x: x["days_since_contact"] or 0, reverse=True)
        return stale_cases
    
    def update_firm_stats(self, firm_email, response_time_days=None, response_type=None):
        """Update statistics for a law firm"""
        if firm_email not in self.data["firm_stats"]:
            self.data["firm_stats"][firm_email] = {
                "total_contacts": 0,
                "total_responses": 0,
                "avg_response_time": 0,
                "response_types": {},
                "last_response": None
            }
        
        firm_data = self.data["firm_stats"][firm_email]
        
        if response_type:
            firm_data["total_responses"] += 1
            firm_data["response_types"][response_type] = firm_data["response_types"].get(response_type, 0) + 1
            firm_data["last_response"] = datetime.now().isoformat()
            
            # Update average response time
            if response_time_days:
                current_avg = firm_data.get("avg_response_time", 0)
                total_responses = firm_data["total_responses"]
                firm_data["avg_response_time"] = ((current_avg * (total_responses - 1)) + response_time_days) / total_responses
        
        self._save_tracking_data()
    
    def get_firm_performance(self, firm_email):
        """Get performance stats for a firm"""
        if firm_email not in self.data["firm_stats"]:
            return {
                "response_rate": 0,
                "avg_response_time": 0,
                "common_responses": [],
                "total_contacts": 0
            }
        
        firm_data = self.data["firm_stats"][firm_email]
        
        response_rate = 0
        if firm_data["total_contacts"] > 0:
            response_rate = (firm_data["total_responses"] / firm_data["total_contacts"]) * 100
        
        # Get most common response types
        response_types = firm_data.get("response_types", {})
        common_responses = sorted(response_types.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "response_rate": round(response_rate, 1),
            "avg_response_time": round(firm_data.get("avg_response_time", 0), 1),
            "common_responses": common_responses[:3],  # Top 3
            "total_contacts": firm_data["total_contacts"]
        }
    
    def detect_lien_reduction_request(self, email_content):
        """Detect if an email contains a lien reduction request"""
        reduction_keywords = [
            "lien reduction", "reduce", "reduction", "lower the amount", 
            "decrease", "settlement amount", "compromise", "discount"
        ]
        
        email_lower = email_content.lower()
        
        for keyword in reduction_keywords:
            if keyword in email_lower:
                return True
        
        return False
    
    def get_collections_dashboard(self):
        """Get dashboard summary of collections status"""
        total_cases = len(self.data["cases"])
        
        # Case status breakdown
        status_counts = {}
        stale_30_days = 0
        stale_60_days = 0
        stale_90_days = 0
        
        for case_data in self.data["cases"].values():
            status = case_data.get("current_status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Check staleness
            if case_data.get("last_contact"):
                try:
                    last_contact = datetime.fromisoformat(case_data["last_contact"])
                    days_since = (datetime.now() - last_contact).days
                    
                    if days_since >= 30:
                        stale_30_days += 1
                    if days_since >= 60:
                        stale_60_days += 1
                    if days_since >= 90:
                        stale_90_days += 1
                except:
                    pass
        
        # Top performing firms
        top_firms = []
        for firm_email, stats in self.data["firm_stats"].items():
            if stats["total_contacts"] >= 3:  # Only firms with decent contact history
                response_rate = (stats["total_responses"] / stats["total_contacts"]) * 100
                top_firms.append((firm_email, response_rate))
        
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
    
    def bootstrap_from_email_cache(self, email_cache, case_manager):
        """
        Bootstrap collections tracking from existing email cache
        Analyzes sent emails to populate case activity history
        """
        if not email_cache or not email_cache.get("emails"):
            logger.warning("No email cache available for bootstrap")
            return
        
        logger.info("Bootstrapping collections tracker from email cache...")
        
        # Get all cases for matching
        case_data = {}
        try:
            cases_df = case_manager.df
            for _, row in cases_df.iterrows():
                case_info = case_manager.format_case(row)
                pv = str(case_info.get("PV", "")).strip()
                if pv:
                    case_data[pv] = {
                        "name": case_info.get("Name", ""),
                        "attorney_email": case_info.get("Attorney Email", ""),
                        "law_firm": case_info.get("Law Firm", "")
                    }
        except Exception as e:
            logger.error(f"Error loading cases for bootstrap: {e}")
            return
        
        processed_count = 0
        matched_count = 0
        
        # Analyze each sent email
        for email in email_cache["emails"]:
            try:
                # Skip if not collections-related
                subject = email.get("subject", "").lower()
                snippet = email.get("snippet", "").lower()
                
                if not self._is_collections_email(subject, snippet):
                    continue
                
                processed_count += 1
                
                # Extract PV numbers from email
                pv_numbers = self._extract_pv_numbers(subject + " " + snippet)
                
                if not pv_numbers:
                    # Try to match by patient name
                    patient_names = self._extract_patient_names(subject + " " + snippet, case_data)
                    if patient_names:
                        # Find PV for this patient
                        for pv, case_info in case_data.items():
                            if case_info["name"].lower() in patient_names:
                                pv_numbers.append(pv)
                                break
                
                # Log activity for matched cases
                for pv in pv_numbers:
                    if pv in case_data:
                        matched_count += 1
                        
                        # Parse email date
                        email_date = self._parse_email_date(email.get("date", ""))
                        
                        # Log the email activity
                        self.log_case_activity(
                            case_pv=pv,
                            activity_type="email_sent",
                            details={
                                "recipient_email": email.get("to", ""),
                                "subject": email.get("subject", ""),
                                "sent_date": email_date.isoformat() if email_date else None,
                                "is_follow_up": "follow" in snippet or "following up" in snippet,
                                "is_initial": "initial" in snippet or not ("follow" in snippet)
                            }
                        )
                        
                        # Update last contact date to email date (not current time)
                        if pv in self.data["cases"]:
                            self.data["cases"][pv]["last_contact"] = email_date.isoformat() if email_date else datetime.now().isoformat()
                        
                        # Set firm email if we have it
                        recipient = email.get("to", "")
                        if recipient and "@" in recipient:
                            if pv in self.data["cases"]:
                                self.data["cases"][pv]["firm_email"] = recipient
                
            except Exception as e:
                logger.error(f"Error processing email in bootstrap: {e}")
                continue
        
        # Save the populated data
        self._save_tracking_data()
        
        logger.info(f"Bootstrap complete: processed {processed_count} collections emails, matched {matched_count} to cases")
        print(f"✅ Collections tracker populated with {matched_count} historical activities from {processed_count} emails")
        
        return {
            "processed_emails": processed_count,
            "matched_activities": matched_count,
            "cases_tracked": len([pv for pv, case in self.data["cases"].items() if case["activities"]])
        }
    
    def _is_collections_email(self, subject, snippet):
        """Determine if an email is collections-related"""
        collections_keywords = [
            "prohealth", "lien", "billing", "status", "update", "case",
            "settled", "pending", "medical", "records", "report",
            "injury", "doi", "attorney", "law firm", "wildeboer", "gould"
        ]
        
        text = (subject + " " + snippet).lower()
        return any(keyword in text for keyword in collections_keywords)
    
    def _extract_pv_numbers(self, text):
        """Extract PV numbers from email text"""
        import re
        
        # Look for PV patterns like "PV 123456", "pv123456", "PV: 123456", etc.
        pv_patterns = [
            r'pv[:\s]*(\d{5,7})',  # PV: 123456 or PV 123456
            r'case[:\s]*(\d{5,7})',  # case: 123456
            r'patient[:\s]*(\d{5,7})',  # patient: 123456
            r'\b(\d{6})\b'  # standalone 6-digit numbers (common PV format)
        ]
        
        pv_numbers = []
        text_lower = text.lower()
        
        for pattern in pv_patterns:
            matches = re.findall(pattern, text_lower)
            pv_numbers.extend(matches)
        
        # Remove duplicates and return
        return list(set(pv_numbers))
    
    def _extract_patient_names(self, text, case_data):
        """Extract patient names that match cases in our database"""
        text_lower = text.lower()
        matched_names = []
        
        for pv, case_info in case_data.items():
            name = case_info["name"].lower()
            if name and len(name) > 3 and name in text_lower:  # Avoid matching very short names
                matched_names.append(name)
        
        return matched_names
    
    def _parse_email_date(self, date_string):
        """Parse email date string to datetime object"""
        try:
            from email.utils import parsedate_to_datetime
            parsed_date = parsedate_to_datetime(date_string)
            
            # Fix future date bug - if date is in future, assume it's previous year
            if parsed_date and parsed_date.date() > datetime.now().date():
                logger.warning(f"Future date detected: {parsed_date} - adjusting to previous year")
                parsed_date = parsed_date.replace(year=parsed_date.year - 1)
            
            return parsed_date
        except Exception as e:
            logger.error(f"Error parsing email date '{date_string}': {e}")
            return None
    
    def get_comprehensive_stale_cases(self, case_manager, exclude_acknowledged=True, progress_callback=None):
        """
        Get comprehensive stale case analysis using cached bootstrap data - FAST!
        
        Args:
            case_manager: CaseManager instance
            exclude_acknowledged: Whether to filter out acknowledged cases
            progress_callback: Optional callback for progress updates (message, percentage)
        """
        # Check if we have cached stale analysis and it's recent (less than 1 hour old)
        if (hasattr(self, '_cached_stale_results') and 
            hasattr(self, '_cache_timestamp') and 
            self._cached_stale_results and 
            self._cache_timestamp):
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < 3600:  # 1 hour cache
                logger.info("Using cached stale case analysis")
                
                # Filter acknowledged cases if requested
                if exclude_acknowledged:
                    return self._filter_acknowledged_cases(self._cached_stale_results)
                return self._cached_stale_results
        
        logger.info("Generating fresh stale case analysis from bootstrap data...")
        
        if progress_callback:
            progress_callback("Loading recent sent emails...", 10)
        
        # Parse recent sent emails to update contact dates
        logger.info("Loading recent sent emails...")
        sent_emails_data = parse_sent_emails_log()
        logger.info(f"Found {len(sent_emails_data)} cases with recent sent emails")
        
        stale_categories = {
            "critical": [],           # 90+ days, no contact
            "high_priority": [],      # 60+ days, no response
            "needs_follow_up": [],    # 30+ days since last contact  
            "no_contact": [],         # Cases with no tracked contact
            "no_response": [],        # Cases with emails sent but no responses received
            "missing_from_bootstrap": [],  # Cases bootstrap missed - need backfill
            # Additional categories for UI compatibility
            "never_contacted": [],    # Alias for no_contact
            "recently_sent": [],      # Sent within last 30 days
            "missing_doi": [],        # Cases missing DOI
            "ccp_335_1": []          # Cases over 2 years old eligible for CCP 335.1
        }
        
        # Track missing cases for backfill
        missing_cases = []
        
        # DEBUG: Check what data we actually have
        total_cases = len(self.data["cases"])
        cases_with_activities = len([pv for pv, data in self.data["cases"].items() if data.get("activities")])
        logger.info(f"Bootstrap data: {total_cases} total cases, {cases_with_activities} with activities")
        
        # FIXED APPROACH: Analyze ALL cases from Excel, check what bootstrap data exists
        try:
            cases_df = case_manager.df
            all_spreadsheet_cases = []
            
            for _, row in cases_df.iterrows():
                case_info = case_manager.format_case(row)
                pv = str(case_info.get("PV", "")).strip()
                if pv:
                    all_spreadsheet_cases.append(pv)
        except Exception as e:
            logger.error(f"Error loading cases from spreadsheet: {e}")
            return stale_categories
        
        logger.info(f"Analyzing {len(all_spreadsheet_cases)} cases from spreadsheet against bootstrap data...")
        
        if progress_callback:
            progress_callback("Analyzing cases...", 20)
        
        total_to_analyze = len(all_spreadsheet_cases)
        
        # Now check each case from spreadsheet against bootstrap data
        for idx, pv in enumerate(all_spreadsheet_cases):
            # Update progress
            if progress_callback and idx % 50 == 0:
                percentage = 20 + int((idx / total_to_analyze) * 70)  # Progress from 20% to 90%
                progress_callback(f"Analyzing case {idx}/{total_to_analyze}...", percentage)
            # Get case info from spreadsheet
            try:
                case_info = self._get_case_basic_info(case_manager, pv)
                if not case_info:
                    continue
            except:
                continue
            
            # Get bootstrap tracking data (if it exists)
            case_tracking = self.data["cases"].get(pv, {})
            
            
            # Calculate days since contact with fallback to activities
            last_contact = case_tracking.get("last_contact")
            days_since_contact = None
            contact_source = None
            
            if last_contact and last_contact.strip():
                try:
                    # Parse timezone-aware date to naive datetime for comparison
                    last_contact_dt = parse_timezone_aware_date(last_contact)
                    if last_contact_dt:
                        days_since_contact = (datetime.now() - last_contact_dt).days
                        contact_source = "bootstrap"
                    else:
                        raise ValueError(f"Could not parse date: {last_contact}")
                    
                    # Fix negative days (future dates) - should not happen with fixed parser but just in case
                    if days_since_contact < 0:
                        logger.warning(f"Negative days since contact for case {pv}: {days_since_contact} days")
                        days_since_contact = 0  # Treat as recent contact
                except Exception as e:
                    logger.warning(f"Failed to parse last_contact '{last_contact}' for case {pv}: {e}")
                    last_contact = None
            
            # Fallback: Use most recent activity if no valid last_contact
            if days_since_contact is None:
                activities = case_tracking.get("activities", [])
                if activities:
                    # Find most recent activity with a valid date
                    most_recent_activity = None
                    for activity in activities:
                        sent_date = activity.get("sent_date")
                        if sent_date:
                            try:
                                # Parse timezone-aware activity date
                                activity_dt = parse_timezone_aware_date(sent_date)
                                if activity_dt and (most_recent_activity is None or activity_dt > most_recent_activity):
                                    most_recent_activity = activity_dt
                            except:
                                continue
                    
                    if most_recent_activity:
                        days_since_contact = (datetime.now() - most_recent_activity).days
                        last_contact = most_recent_activity.isoformat()
                        contact_source = "activity_fallback"
                        
                        if days_since_contact < 0:
                            days_since_contact = 0
            
            # Final check: Use sent emails as most recent contact (highest priority)
            if pv in sent_emails_data:
                sent_email_timestamp = sent_emails_data[pv]['timestamp']
                sent_days_ago = (datetime.now() - sent_email_timestamp).days
                
                # If sent email is more recent than any other contact, use it
                if days_since_contact is None or sent_days_ago < days_since_contact:
                    days_since_contact = sent_days_ago
                    last_contact = sent_email_timestamp.isoformat()
                    contact_source = "sent_email_log"
                    
                    if days_since_contact < 0:
                        days_since_contact = 0
            
            # Build case data
            case_data = {
                "pv": pv,
                "name": case_info.get("Name", ""),
                "attorney_email": case_info.get("Attorney Email", ""),
                "law_firm": case_info.get("Law Firm", ""),
                "days_since_contact": days_since_contact,
                "last_contact": last_contact,
                "response_count": case_tracking.get("response_count", 0),
                "activity_count": len(case_tracking.get("activities", []))
            }
            
            # Add DOI and Status to case data
            case_data["doi"] = case_info.get("DOI", "")
            case_data["status"] = case_info.get("Status", "")
            
            # Improved categorization logic
            has_bootstrap_data = len(case_tracking) > 0
            has_activities = case_data["activity_count"] > 0
            has_valid_contact = days_since_contact is not None
            
            # DEBUG for case 295187
            if pv == "295187":
                logger.info(f"DEBUG Case 295187 categorization: has_bootstrap_data={has_bootstrap_data}, has_activities={has_activities}, has_valid_contact={has_valid_contact}")
            
            if has_valid_contact:
                # Categorize by urgency FIRST, then check for no response
                if days_since_contact >= 90:
                    stale_categories["critical"].append(case_data)
                elif days_since_contact >= 60:
                    # 60-89 days is high priority
                    stale_categories["high_priority"].append(case_data)
                elif days_since_contact >= 30:
                    # 30-59 days needs follow-up
                    stale_categories["needs_follow_up"].append(case_data)
                elif days_since_contact < 30:
                    # Recently sent (less than 30 days)
                    stale_categories["recently_sent"].append(case_data)
                    if case_data["response_count"] == 0:
                        # Also add to no_response if no responses
                        stale_categories["no_response"].append(case_data)
            elif has_bootstrap_data and has_activities:
                # This should rarely happen now with activity fallback
                logger.warning(f"Case {pv} has {has_activities} activities but no valid contact date - investigate data quality")
                stale_categories["no_contact"].append(case_data)
                stale_categories["never_contacted"].append(case_data)  # Add to never_contacted as well
            else:
                # No bootstrap data or activities - truly never contacted
                stale_categories["no_contact"].append(case_data)
                stale_categories["never_contacted"].append(case_data)  # Add to never_contacted as well
                # Also add to missing_from_bootstrap for tracking
                if not has_bootstrap_data:
                    stale_categories["missing_from_bootstrap"].append(case_data)
                    missing_cases.append(pv)
            
            # Check for missing DOI - check for all cases regardless of contact status
            doi_value = case_data.get("doi", "")
            if doi_value is None or str(doi_value).strip() == "" or str(doi_value).upper() == "NONE":
                stale_categories["missing_doi"].append(case_data)
            
            # Check for CCP 335.1 eligibility (DOI over 2 years old) - check all cases
            doi_value = case_data.get("doi")
            if doi_value and str(doi_value).strip() != "" and str(doi_value).upper() != "NONE":
                try:
                    # Parse DOI and check if over 2 years old
                    doi_str = str(doi_value).strip()
                    # Try different date formats
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%m-%Y"]:
                        try:
                            doi_date = datetime.strptime(doi_str, fmt)
                            years_since_injury = (datetime.now() - doi_date).days / 365.25
                            if years_since_injury >= 2:
                                stale_categories["ccp_335_1"].append(case_data)
                            break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Could not parse DOI for case {pv}: {e}")
        
        # Sort each category by priority (handle None values)
        for category in stale_categories.values():
            category.sort(key=lambda x: x.get("days_since_contact") or 0, reverse=True)
        
        # Log category counts for debugging
        logger.info("Category counts after analysis:")
        for cat_name, cat_cases in stale_categories.items():
            if len(cat_cases) > 0:
                logger.info(f"  {cat_name}: {len(cat_cases)} cases")
        
        # Save missing cases log for backfill
        if missing_cases:
            self._save_missing_cases_log(missing_cases)
            logger.info(f"Found {len(missing_cases)} cases missing from bootstrap - logged for backfill")
        
        # Cache the results (before filtering acknowledged)
        self._cached_stale_results = stale_categories
        self._cache_timestamp = datetime.now()
        
        # Filter acknowledged cases if requested
        if exclude_acknowledged:
            stale_categories = self._filter_acknowledged_cases(stale_categories)
        
        return stale_categories
    
    def invalidate_stale_case_cache(self):
        """Invalidate the stale case analysis cache to force refresh"""
        self._cached_stale_results = None
        self._cache_timestamp = None
        logger.info("Stale case analysis cache invalidated - will refresh on next request")
    
    def _save_missing_cases_log(self, missing_cases):
        """Save list of missing cases for backfill command"""
        try:
            missing_log_file = Config.get_file_path("data/missing_from_bootstrap.json")
            os.makedirs(os.path.dirname(missing_log_file), exist_ok=True)
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "missing_cases": missing_cases,
                "count": len(missing_cases)
            }
            
            with open(missing_log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2)
                
            logger.info(f"Saved {len(missing_cases)} missing cases to {missing_log_file}")
        except Exception as e:
            logger.error(f"Error saving missing cases log: {e}")
    
    def _filter_acknowledged_cases(self, stale_categories):
        """Filter out acknowledged cases from stale categories"""
        try:
            from services.case_acknowledgment_service import CaseAcknowledgmentService
            ack_service = CaseAcknowledgmentService()
            
            filtered_categories = {}
            total_filtered = 0
            
            for category, cases in stale_categories.items():
                filtered_cases = []
                for case in cases:
                    pv = case.get("pv")
                    if pv and not ack_service.is_acknowledged(pv):
                        filtered_cases.append(case)
                    else:
                        total_filtered += 1
                filtered_categories[category] = filtered_cases
            
            if total_filtered > 0:
                logger.info(f"Filtered out {total_filtered} acknowledged cases from stale analysis")
            
            return filtered_categories
        except ImportError:
            # If acknowledgment service not available, return unfiltered
            return stale_categories
        except Exception as e:
            logger.error(f"Error filtering acknowledged cases: {e}")
            return stale_categories
    
    def clear_stale_cache(self):
        """Clear the stale case analysis cache to force fresh analysis"""
        if hasattr(self, '_cached_stale_results'):
            delattr(self, '_cached_stale_results')
        if hasattr(self, '_cache_timestamp'):
            delattr(self, '_cache_timestamp')
        logger.info("Stale case cache cleared")
    
    def recalculate_response_counts(self):
        """Recalculate response counts excluding our own emails and bounces"""
        logger.info("Recalculating response counts...")
        
        for case_pv, case_data in self.data["cases"].items():
            response_count = 0
            activities = case_data.get("activities", [])
            
            for activity in activities:
                if activity.get("type") == "email_received":
                    details = activity.get("details", {})
                    sender = details.get("sender_email", "").lower()
                    
                    # Skip our own emails
                    if 'dean' in sender or 'prohealth' in sender or 'hyland' in sender:
                        continue
                    
                    # Skip daemon/bounce emails
                    daemon_indicators = ['mailer-daemon', 'postmaster', 'delivery', 'undeliverable', 
                                       'bounce', 'failure', 'failed', 'rejected', 'returned mail']
                    if any(indicator in sender for indicator in daemon_indicators):
                        continue
                    
                    # Skip auto-replies
                    subject = details.get("subject", "").lower()
                    auto_reply_indicators = ['out of office', 'auto-reply', 'automatic reply', 
                                           'away from office', 'on vacation', 'on leave']
                    if any(indicator in subject for indicator in auto_reply_indicators):
                        continue
                    
                    # This is a legitimate response
                    response_count += 1
            
            # Update the response count
            case_data["response_count"] = response_count
        
        # Save the updated data
        self._save_tracking_data()
        
        # Clear cache to force refresh
        self.clear_stale_cache()
        
        logger.info(f"Response counts recalculated for {len(self.data['cases'])} cases")
    
    def get_stale_cases_by_category(self, case_manager, category, limit=10):
        """
        Get specific stale case category quickly
        Categories: critical, high_priority, needs_follow_up, no_contact, no_response
        """
        all_stale = self.get_comprehensive_stale_cases(case_manager)
        
        if category not in all_stale:
            return {"cases": [], "total": 0, "category": category}
            
        cases = all_stale[category]
        
        return {
            "cases": cases[:limit],
            "total": len(cases),
            "category": category,
            "remaining": max(0, len(cases) - limit)
        }
    
    def mark_case_contacted(self, pv, contact_type="follow_up"):
        """
        Mark a case as recently contacted to move it out of stale categories
        """
        if pv in self.data["cases"]:
            self.log_case_activity(
                case_pv=pv,
                activity_type="email_sent",
                details={
                    "contact_type": contact_type,
                    "manual_update": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            # Clear cache so next stale analysis will be fresh
            if hasattr(self, '_cached_stale_results'):
                delattr(self, '_cached_stale_results')
            logger.info(f"Marked case {pv} as contacted - moved out of stale categories")
            return True
        return False
    
    def _get_case_basic_info(self, case_manager, pv):
        """Fast lookup of basic case info by PV number"""
        try:
            # Try to find the case efficiently
            cases_df = case_manager.df
            pv_matches = cases_df[cases_df.iloc[:, 1].astype(str).str.strip() == str(pv)]
            
            if not pv_matches.empty:
                row = pv_matches.iloc[0]
                return case_manager.format_case(row)
            return None
        except:
            return None

    def bootstrap_from_gmail_direct(self, gmail_service, case_manager):
        """
        Bootstrap collections tracking by searching Gmail directly for each case
        This analyzes the entire Gmail history, not just the 500 email cache
        """
        logger.info("Bootstrapping collections tracker from Gmail directly...")
        
        # Get all cases for analysis
        try:
            cases_df = case_manager.df
            all_cases = []
            
            for _, row in cases_df.iterrows():
                case_info = case_manager.format_case(row)
                pv = str(case_info.get("PV", "")).strip()
                status = str(case_info.get("Status", "")).lower()
                
                # Analyze all cases regardless of status
                if pv:
                    all_cases.append({
                        "PV": pv,
                        "Name": case_info.get("Name", ""),
                        "Attorney Email": case_info.get("Attorney Email", ""),
                        "Law Firm": case_info.get("Law Firm", ""),
                        "CMS": case_info.get("CMS", ""),
                        "DOI": case_info.get("DOI", "")
                    })
        except Exception as e:
            logger.error(f"Error loading cases for Gmail bootstrap: {e}")
            return None
        
        processed_cases = 0
        matched_activities = 0
        
        print(f"🔍 Analyzing {len(all_cases)} cases from your entire Gmail history...")
        
        # Process cases in batches for progress updates
        batch_size = 50
        total_batches = (len(all_cases) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(all_cases))
            batch = all_cases[start_idx:end_idx]
            
            print(f"📊 Processing batch {batch_num + 1}/{total_batches} (cases {start_idx + 1}-{end_idx})")
            
            for case in batch:
                try:
                    # Build search query for this case
                    query = self._build_gmail_search_query(case)
                    
                    # Search Gmail for sent emails related to this case
                    sent_query = f"in:sent ({query})"
                    sent_messages = gmail_service.search_messages(sent_query, max_results=10)
                    
                    processed_cases += 1
                    
                    if sent_messages:
                        # Process each sent email
                        for msg in sent_messages:
                            try:
                                # Get full email content
                                full_msg = gmail_service.get_message(msg['id'])
                                if not full_msg:
                                    continue
                                
                                # Extract email metadata
                                headers = {h['name'].lower(): h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
                                subject = headers.get('subject', '')
                                to_email = headers.get('to', '')
                                date_str = headers.get('date', '')
                                
                                # Parse email date
                                email_date = self._parse_email_date(date_str)
                                
                                # Check if this is a collections-related email
                                snippet = msg.get('snippet', '')
                                if self._is_collections_email(subject, snippet):
                                    # Log the email activity
                                    self.log_case_activity(
                                        case_pv=case["PV"],
                                        activity_type="email_sent",
                                        details={
                                            "recipient_email": to_email,
                                            "subject": subject,
                                            "sent_date": email_date.isoformat() if email_date else None,
                                            "is_follow_up": "follow" in snippet.lower() or "following up" in snippet.lower(),
                                            "is_initial": "initial" in snippet.lower() or not ("follow" in snippet.lower()),
                                            "gmail_id": msg['id']
                                        }
                                    )
                                    
                                    # Update case metadata
                                    if case["PV"] in self.data["cases"]:
                                        # Use actual email date, not current time
                                        self.data["cases"][case["PV"]]["last_contact"] = email_date.isoformat() if email_date else datetime.now().isoformat()
                                        
                                        # Set firm email
                                        if to_email and "@" in to_email:
                                            self.data["cases"][case["PV"]]["firm_email"] = to_email
                                    
                                    matched_activities += 1
                                    
                            except Exception as e:
                                logger.error(f"Error processing email {msg.get('id', 'unknown')}: {e}")
                                continue
                    
                    # Look for received emails (responses) as well
                    if case.get('Attorney Email'):
                        received_query = f"from:{case['Attorney Email']} ({query})"
                        received_messages = gmail_service.search_messages(received_query, max_results=5)
                        
                        if received_messages:
                            # Process received emails - they also count as contact!
                            for msg in received_messages:
                                try:
                                    full_msg = gmail_service.get_message(msg['id'])
                                    if not full_msg:
                                        continue
                                    
                                    headers = {h['name'].lower(): h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
                                    date_str = headers.get('date', '')
                                    from_email = headers.get('from', '').lower()
                                    subject = headers.get('subject', '').lower()
                                    
                                    # Skip if this is from us (Dean/Prohealth)
                                    if 'dean' in from_email or 'prohealth' in from_email or 'hyland' in from_email:
                                        continue
                                    
                                    # Skip if this is a daemon/bounce email
                                    daemon_indicators = ['mailer-daemon', 'postmaster', 'delivery', 'undeliverable', 
                                                       'bounce', 'failure', 'failed', 'rejected', 'returned mail']
                                    if any(indicator in from_email for indicator in daemon_indicators):
                                        # Log as bounce/failed delivery instead of response
                                        self.log_case_activity(
                                            case_pv=case["PV"],
                                            activity_type="email_bounced",
                                            details={
                                                "sender_email": from_email,
                                                "subject": subject,
                                                "received_date": self._parse_email_date(date_str).isoformat() if self._parse_email_date(date_str) else None,
                                                "gmail_id": msg['id'],
                                                "source": "bootstrap"
                                            }
                                        )
                                        continue
                                    
                                    # Skip auto-replies
                                    auto_reply_indicators = ['out of office', 'auto-reply', 'automatic reply', 
                                                           'away from office', 'on vacation', 'on leave']
                                    if any(indicator in subject for indicator in auto_reply_indicators):
                                        continue
                                    
                                    email_date = self._parse_email_date(date_str)
                                    
                                    # This is a legitimate response - log it
                                    self.log_case_activity(
                                        case_pv=case["PV"],
                                        activity_type="email_received",
                                        details={
                                            "sender_email": from_email,
                                            "subject": subject,
                                            "received_date": email_date.isoformat() if email_date else None,
                                            "gmail_id": msg['id'],
                                            "source": "bootstrap"
                                        }
                                    )
                                    
                                    # Update response count and potentially last_contact if this is more recent
                                    if case["PV"] in self.data["cases"]:
                                        self.data["cases"][case["PV"]]["response_count"] += 1
                                        
                                        # If this received email is more recent than last_contact, update it
                                        current_last = self.data["cases"][case["PV"]].get("last_contact")
                                        if email_date and (not current_last or email_date.isoformat() > current_last):
                                            self.data["cases"][case["PV"]]["last_contact"] = email_date.isoformat()
                                    
                                except Exception as e:
                                    logger.error(f"Error processing received email for case {case['PV']}: {e}")
                                    continue
                    
                except Exception as e:
                    logger.error(f"Error analyzing case {case['PV']} in Gmail bootstrap: {e}")
                    continue
            
            # Brief pause to avoid hitting Gmail API limits
            import time
            time.sleep(0.5)
        
        # Save the populated data
        self._save_tracking_data()
        
        logger.info(f"Gmail bootstrap complete: processed {processed_cases} cases, found {matched_activities} activities")
        
        return {
            "processed_cases": processed_cases,
            "matched_activities": matched_activities,
            "cases_tracked": len([pv for pv, case in self.data["cases"].items() if case["activities"]])
        }
    
    def _build_gmail_search_query(self, case):
        """Build Gmail search query for a specific case"""
        query = f'"{case["Name"]}" OR {case["PV"]}'
        if case.get('CMS'):
            query += f' OR {case["CMS"]}'
        # Note: DOI excluded as Gmail can't search datetime objects properly
        return query
    
    def backfill_missing_cases(self, gmail_service, case_manager):
        """
        Backfill cases that bootstrap missed - much faster than full re-bootstrap
        """
        logger.info("Starting backfill of missing cases...")
        
        # Load missing cases log
        missing_log_file = Config.get_file_path("data/missing_from_bootstrap.json")
        if not os.path.exists(missing_log_file):
            logger.info("No missing cases log found - run 'stale cases' first")
            return {"processed": 0, "found": 0, "message": "No missing cases to backfill"}
        
        try:
            with open(missing_log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            missing_cases = log_data.get("missing_cases", [])
            if not missing_cases:
                logger.info("No missing cases in log")
                return {"processed": 0, "found": 0, "message": "No missing cases to backfill"}
            
        except Exception as e:
            logger.error(f"Error loading missing cases log: {e}")
            return {"processed": 0, "found": 0, "message": f"Error loading missing cases: {e}"}
        
        logger.info(f"Backfilling {len(missing_cases)} missing cases...")
        
        processed_count = 0
        found_count = 0
        
        for pv in missing_cases:
            try:
                # Get case info for search query
                case_info = self._get_case_basic_info(case_manager, pv)
                if not case_info:
                    continue
                
                # Build search query same as bootstrap
                query = f'"{case_info["Name"]}" OR {pv}'
                if case_info.get('CMS'):
                    query += f' OR {case_info["CMS"]}'
                
                # Search for sent emails
                sent_query = f"in:sent ({query})"
                sent_messages = gmail_service.search_messages(sent_query, max_results=10)
                
                processed_count += 1
                
                if sent_messages:
                    found_count += 1
                    logger.info(f"Backfill found {len(sent_messages)} emails for case {pv}")
                    
                    # Process each email same as bootstrap
                    for msg in sent_messages:
                        try:
                            # Get full email content  
                            full_msg = gmail_service.get_message(msg['id'])
                            if not full_msg:
                                continue
                            
                            # Extract email metadata
                            headers = {h['name'].lower(): h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
                            subject = headers.get('subject', '')
                            to_email = headers.get('to', '')
                            date_str = headers.get('date', '')
                            
                            # Parse email date
                            email_date = self._parse_email_date(date_str)
                            
                            # Check if collections-related
                            snippet = msg.get('snippet', '')
                            if self._is_collections_email(subject, snippet):
                                # Log the activity
                                self.log_case_activity(
                                    case_pv=pv,
                                    activity_type="email_sent", 
                                    details={
                                        "recipient_email": to_email,
                                        "subject": subject,
                                        "sent_date": email_date.isoformat() if email_date else None,
                                        "is_follow_up": "follow" in snippet.lower(),
                                        "is_initial": "initial" in snippet.lower(),
                                        "gmail_id": msg['id'],
                                        "source": "backfill"
                                    }
                                )
                                
                                # Update case metadata
                                if pv in self.data["cases"]:
                                    self.data["cases"][pv]["last_contact"] = email_date.isoformat() if email_date else datetime.now().isoformat()
                                    if to_email and "@" in to_email:
                                        self.data["cases"][pv]["firm_email"] = to_email
                                
                        except Exception as e:
                            logger.error(f"Error processing backfill email for case {pv}: {e}")
                            continue
                
                # Brief pause to avoid API limits
                import time
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error backfilling case {pv}: {e}")
                continue
        
        # Save updated data
        self._save_tracking_data()
        
        # Clear stale cache so next analysis uses new data
        self.clear_stale_cache()
        
        # Archive the missing cases log
        try:
            archive_file = missing_log_file.replace('.json', f'_completed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            os.rename(missing_log_file, archive_file)
            logger.info(f"Archived completed missing cases log to {archive_file}")
        except:
            pass
        
        result = {
            "processed": processed_count,
            "found": found_count, 
            "message": f"Backfilled {found_count}/{processed_count} cases with email data"
        }
        
        logger.info(f"Backfill complete: {result['message']}")
        return result