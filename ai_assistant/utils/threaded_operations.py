"""
Threaded operations for long-running tasks
Prevents UI freezing by running operations in background threads
"""

from PyQt5.QtCore import QThread, pyqtSignal, QObject
import time
import logging

logger = logging.getLogger(__name__)


class EmailCacheWorker(QThread):
    """Worker thread for email cache operations"""
    
    # Signals
    progress_update = pyqtSignal(int, str)  # percentage, message
    log_message = pyqtSignal(str)
    finished = pyqtSignal(object)  # result
    error = pyqtSignal(str)
    
    def __init__(self, email_cache_service, operation, *args, **kwargs):
        super().__init__()
        self.email_cache_service = email_cache_service
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.from_date = kwargs.get('from_date')
        
    def run(self):
        """Run the email operation in background thread"""
        try:
            # Create a progress callback that emits signals
            def progress_callback(value, message=None, log=None):
                if message:
                    self.progress_update.emit(value, message)
                if log:
                    self.log_message.emit(log)
            
            # Run the operation
            if self.operation == 'bootstrap':
                if self.from_date:
                    # Bootstrap from specific date
                    self.result = self.email_cache_service.bootstrap_from_date_threaded(
                        self.from_date, progress_callback=progress_callback
                    )
                else:
                    # Full bootstrap
                    self.result = self.email_cache_service.bootstrap_all_emails_threaded(
                        progress_callback=progress_callback
                    )
            elif self.operation == 'refresh':
                max_results = self.args[0] if self.args else 500
                self.result = self.email_cache_service.download_sent_emails_threaded(
                    max_results, progress_callback=progress_callback
                )
            elif self.operation == 'full_sync':
                max_results = self.kwargs.get('max_results')
                self.result = self.email_cache_service._full_sync_threaded(
                    max_results, progress_callback=progress_callback
                )
                
            self.finished.emit(self.result)
            
        except Exception as e:
            logger.error(f"Error in email worker: {e}")
            self.error.emit(str(e))


class GmailSearchWorker(QThread):
    """Worker thread for Gmail search operations"""
    
    # Signals
    progress_update = pyqtSignal(int, str)
    log_message = pyqtSignal(str)
    batch_complete = pyqtSignal(int)  # number of emails so far
    finished = pyqtSignal(list)  # results
    error = pyqtSignal(str)
    
    def __init__(self, gmail_service, query, max_results=None):
        super().__init__()
        self.gmail_service = gmail_service
        self.query = query
        self.max_results = max_results
        self.should_stop = False
        
    def stop(self):
        """Signal the worker to stop"""
        self.should_stop = True
        
    def run(self):
        """Run Gmail search in background thread"""
        try:
            all_messages = []
            page_token = None
            
            # Determine how many to fetch
            if self.max_results is None:
                fetch_all = True
                per_request = 100
            else:
                fetch_all = False
                per_request = min(self.max_results, 100) if self.max_results > 0 else 100
            
            self.log_message.emit(f"🔍 Query: {self.query}")
            if fetch_all:
                self.log_message.emit("⏳ Fetching all emails in batches of 100...")
            
            while not self.should_stop:
                # Build request parameters
                params = {
                    'userId': 'me',
                    'q': self.query,
                    'maxResults': per_request
                }
                if page_token:
                    params['pageToken'] = page_token
                
                # Execute request
                response = self.gmail_service.service.users().messages().list(**params).execute()
                
                messages = response.get("messages", [])
                if not messages:
                    break
                
                # Process this batch
                batch_count = 0
                for msg in messages:
                    if self.should_stop:
                        break
                        
                    if not fetch_all and len(all_messages) >= self.max_results:
                        break
                    
                    # Get full message details
                    message = self.gmail_service.service.users().messages().get(
                        userId='me',
                        id=msg["id"],
                        format="full"
                    ).execute()
                    
                    headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
                    all_messages.append({
                        "id": msg["id"],
                        "snippet": message.get("snippet", ""),
                        "from": headers.get("From"),
                        "to": headers.get("To"),
                        "subject": headers.get("Subject"),
                        "date": headers.get("Date"),
                        "thread_id": message.get("threadId")
                    })
                    
                    batch_count += 1
                    
                    # Update progress every 10 emails
                    if batch_count % 10 == 0:
                        percentage = min(100, int((len(all_messages) / (self.max_results or 1000)) * 100))
                        self.progress_update.emit(percentage, f"Processing email {len(all_messages)}...")
                
                # Log progress for large fetches
                if fetch_all and len(all_messages) % 100 == 0 and len(all_messages) > 0:
                    self.log_message.emit(f"📧 Fetched {len(all_messages)} emails so far...")
                    self.batch_complete.emit(len(all_messages))
                
                # Check if we should continue
                if not fetch_all and len(all_messages) >= self.max_results:
                    break
                
                # Get next page token
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            if len(all_messages) > 0:
                self.log_message.emit(f"✅ Total emails found: {len(all_messages)}")
            
            self.finished.emit(all_messages)
            
        except Exception as e:
            logger.error(f"Error in Gmail search: {e}")
            self.error.emit(str(e))


class CategorizeWorker(QThread):
    """Worker thread for case categorization"""
    
    progress_update = pyqtSignal(int, str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, bulk_service, active_only=True, force_refresh=False):
        super().__init__()
        self.bulk_service = bulk_service
        self.active_only = active_only
        self.force_refresh = force_refresh
        
    def run(self):
        """Run categorization in background"""
        try:
            # Create progress callback
            def progress_callback(msg, pct):
                self.progress_update.emit(pct, msg)
                if "Processing" in msg or "Found" in msg:
                    self.log_message.emit(msg)
            
            # Run categorization
            result = self.bulk_service.categorize_cases(
                active_only=self.active_only,
                force_refresh=self.force_refresh,
                progress_callback=progress_callback
            )
            
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"Error in categorization: {e}")
            self.error.emit(str(e))


class CollectionsAnalyzerWorker(QThread):
    """Worker thread for analyzing email cache against cases"""
    
    progress_update = pyqtSignal(int, str)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(bool, dict)  # success, results
    error = pyqtSignal(str)
    
    def __init__(self, tracker, case_manager):
        super().__init__()
        self.tracker = tracker
        self.case_manager = case_manager
        
    def run(self):
        """Run collections analysis in background"""
        try:
            # Check if we have an email cache
            if not hasattr(self.tracker, 'email_cache') or not self.tracker.email_cache.cache.get('emails'):
                self.error.emit("No email cache found. Please download email history first.")
                return
            
            cached_emails = self.tracker.email_cache.cache.get('emails', [])
            total_emails = len(cached_emails)
            cases_df = self.case_manager.df
            total_cases = len(cases_df)
            
            self.log_message.emit(f"📊 Starting analysis...")
            self.log_message.emit(f"📧 Found {total_emails} cached emails")
            self.log_message.emit(f"📁 Found {total_cases} cases to analyze")
            self.progress_update.emit(5, f"Analyzing {total_emails} emails against {total_cases} cases...")
            
            # Use bootstrap_from_email_cache if available
            if hasattr(self.tracker, 'bootstrap_from_email_cache'):
                self.progress_update.emit(10, "Running bootstrap analysis...")
                
                # Bootstrap from the email cache
                result = self.tracker.bootstrap_from_email_cache(
                    self.tracker.email_cache.cache,
                    self.case_manager,
                    max_emails=None  # Process all emails
                )
                
                if result:
                    self.progress_update.emit(90, "Finalizing categories...")
                    
                    # Force a comprehensive analysis with full email search after bootstrap
                    # This ensures Never Contacted is accurate
                    if hasattr(self.tracker, 'get_comprehensive_stale_cases'):
                        self.tracker.get_comprehensive_stale_cases(
                            self.case_manager,
                            skip_email_search=False  # Do full email search for accuracy
                        )
                    
                    self.progress_update.emit(100, "Analysis complete!")
                    self.log_message.emit(f"✅ Analysis complete: {result.get('matched_activities', 0)} activities tracked")
                    self.finished.emit(True, result)
                else:
                    self.progress_update.emit(100, "Bootstrap complete")
                    self.log_message.emit("✅ Bootstrap analysis complete")
                    self.finished.emit(True, {'success': True})
            else:
                # Fallback to basic analysis
                self.progress_update.emit(10, "Running standard analysis...")
                results = self._run_standard_analysis(cached_emails, cases_df, total_cases)
                self.finished.emit(True, results)
                
        except Exception as e:
            logger.error(f"Error in collections analysis: {e}")
            self.error.emit(str(e))
    
    def _run_enhanced_analysis(self):
        """Run the enhanced tracker's analysis"""
        try:
            # Get email cache info for progress display
            cached_emails = self.tracker.email_cache.cache.get('emails', [])
            total_emails = len(cached_emails)
            
            self.log_message.emit(f"🔍 Analyzing {total_emails} cached emails")
            
            # Get case count for progress display
            cases_df = self.case_manager.df
            total_cases = len(cases_df)
            
            if total_cases == 0:
                self.log_message.emit("⚠️ No cases in spreadsheet")
                return False
            
            self.progress_update.emit(20, f"Processing {total_cases} cases...")
            self.log_message.emit(f"📁 Processing {total_cases} cases")
            
            # Call the tracker's analyze_from_cache method
            self.progress_update.emit(50, "Matching emails to cases...")
            success = self.tracker.analyze_from_cache(self.case_manager)
            
            if success:
                # Get summary statistics from the analyzed data
                cases_with_activity = 0
                total_matches = 0
                
                for pv, case_data in self.tracker.data['cases'].items():
                    if case_data['sent_count'] > 0 or case_data['response_count'] > 0:
                        cases_with_activity += 1
                        total_matches += case_data['sent_count'] + case_data['response_count']
                
                self.progress_update.emit(95, "Finalizing...")
                self.log_message.emit(f"✅ Processed {total_cases} cases")
                self.log_message.emit(f"📧 Found {total_matches} email matches")
                self.log_message.emit(f"📊 {cases_with_activity} cases have email activity")
                
                return True
            else:
                self.log_message.emit("⚠️ Analysis completed with warnings")
                return False
            
        except Exception as e:
            logger.error(f"Error in enhanced analysis: {e}")
            self.error.emit(f"Analysis error: {e}")
            return False
    
    def _run_standard_analysis(self, cached_emails, cases_df, total_cases):
        """Run standard collections analysis"""
        tracking_data = {}
        matches_found = 0
        
        for idx, row in cases_df.iterrows():
            if idx % 10 == 0:
                percentage = min(90, int((idx / total_cases) * 80) + 10)
                self.progress_update.emit(
                    percentage,
                    f"Processing case {idx+1} of {total_cases}..."
                )
            
            case_info = self.case_manager.format_case(row)
            if not case_info:
                continue
            
            pv = str(case_info.get('pv', '')).strip()
            if not pv or pv == 'nan':
                continue
            
            # Search for related emails
            case_emails = []
            for email in cached_emails:
                email_text = f"{email.get('subject', '')} {email.get('snippet', '')}".lower()
                if pv.lower() in email_text:
                    case_emails.append(email)
                    matches_found += 1
            
            if case_emails:
                tracking_data[pv] = {
                    'case_info': case_info,
                    'emails': case_emails,
                    'total_emails': len(case_emails)
                }
        
        self.progress_update.emit(100, "Analysis complete!")
        self.log_message.emit(f"✅ Found {matches_found} emails for {len(tracking_data)} cases")
        
        return {'tracking_data': tracking_data, 'matches': matches_found}