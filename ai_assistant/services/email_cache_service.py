import os
import json
import logging
from datetime import datetime, timedelta
from services.gmail_service import GmailService
from config import Config

logger = logging.getLogger(__name__)

class EmailCacheService:
    """Manages email caching and cadence analysis"""
    
    def __init__(self, gmail_service=None):
        self.gmail_service = gmail_service or GmailService()
        self.cache_file = Config.get_file_path("data/email_cache.json")
        self.cadence_file = Config.get_file_path("data/cadence_analysis.json")
        self.cache = self._load_cache()
        self.cadence = self._load_cadence()
    
    def _load_cache(self):
        """Load email cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"emails": [], "last_updated": None, "last_history_id": None, "last_sync_time": None}
        except Exception as e:
            logger.error(f"Error loading email cache: {e}")
            return {"emails": [], "last_updated": None, "last_history_id": None, "last_sync_time": None}
    
    def _save_cache(self):
        """Save email cache to file"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, default=str)
            logger.info(f"Email cache saved with {len(self.cache['emails'])} emails")
        except Exception as e:
            logger.error(f"Error saving email cache: {e}")
    
    def _load_cadence(self):
        """Load cadence analysis from file"""
        try:
            if os.path.exists(self.cadence_file):
                with open(self.cadence_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading cadence analysis: {e}")
            return {}
    
    def _save_cadence(self):
        """Save cadence analysis to file"""
        try:
            os.makedirs(os.path.dirname(self.cadence_file), exist_ok=True)
            with open(self.cadence_file, 'w', encoding='utf-8') as f:
                json.dump(self.cadence, f, indent=2, default=str)
            logger.info("Cadence analysis saved")
        except Exception as e:
            logger.error(f"Error saving cadence analysis: {e}")
    
    def bootstrap_all_emails(self):
        """Bootstrap cache with ALL emails (sent and received) for case categorization"""
        print("🚀 Bootstrapping email cache with ALL emails (sent & received)...")
        print("   This may take several minutes for large email histories...")
        return self._full_sync(max_results=None)
    
    def update_cache(self, incremental=True):
        """Update the email cache (incremental by default)"""
        return self.download_sent_emails(max_results=None, incremental=incremental)
    
    def download_sent_emails(self, max_results=None, incremental=True):
        """Download sent emails and cache them
        
        Args:
            max_results (int): Maximum number of emails to fetch (None = all emails)
            incremental (bool): If True, only fetch new emails since last sync
        """
        try:
            if incremental and self._can_do_incremental_update():
                return self._incremental_update(max_results)
            else:
                return self._full_sync(max_results)
            
        except Exception as e:
            logger.error(f"Error downloading sent emails: {e}")
            print(f"❌ Error downloading emails: {e}")
            return []
    
    def analyze_cadence(self, max_emails_for_cadence=500):
        """Analyze email cadence and style from cached SENT emails only
        
        Args:
            max_emails_for_cadence (int): Number of recent emails to use for cadence analysis
        """
        try:
            if not self.cache.get("emails"):
                print("⚠️ No cached emails to analyze")
                return
            
            print(f"🧠 Analyzing email cadence and style from last {max_emails_for_cadence} sent emails...")
            
            # Filter for SENT emails only for cadence analysis
            all_emails = self.cache["emails"]
            # Check if email is from our domain/sent by us
            sent_emails = [e for e in all_emails if self._is_sent_email(e)]
            emails = sent_emails[:max_emails_for_cadence]  # Take first N sent emails
            
            # Basic metrics
            total_emails = len(emails)
            total_cached = len(all_emails)
            
            # Time-based analysis
            email_dates = []
            for email in emails:
                try:
                    from email.utils import parsedate_to_datetime
                    date = parsedate_to_datetime(email.get('date', ''))
                    email_dates.append(date)
                except:
                    continue
            
            if email_dates:
                email_dates.sort()
                date_range = email_dates[-1] - email_dates[0]
                avg_frequency = date_range.days / len(email_dates) if len(email_dates) > 1 else 0
            else:
                avg_frequency = 0
            
            # Subject line analysis
            subjects = [email.get('subject', '') for email in emails if email.get('subject')]
            common_words = self._analyze_common_words(subjects)
            
            # Snippet analysis (email body style)
            snippets = [email.get('snippet', '') for email in emails if email.get('snippet')]
            style_patterns = self._analyze_style_patterns(snippets)
            
            # Build cadence profile
            self.cadence = {
                "analysis_date": datetime.now().isoformat(),
                "total_emails_analyzed": total_emails,
                "total_emails_cached": total_cached,
                "average_frequency_days": round(avg_frequency, 1),
                "common_subject_words": common_words[:10],  # Top 10
                "style_patterns": style_patterns,
                "greeting_patterns": self._extract_greetings(snippets),
                "closing_patterns": self._extract_closings(snippets),
                "tone_indicators": self._analyze_tone(snippets)
            }
            
            self._save_cadence()
            
            print("✅ Cadence analysis complete")
            self._display_cadence_summary()
            
        except Exception as e:
            logger.error(f"Error analyzing cadence: {e}")
            print(f"❌ Error analyzing cadence: {e}")
    
    def _analyze_common_words(self, texts):
        """Extract common words from text list"""
        from collections import Counter
        import re
        
        all_words = []
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        
        for text in texts:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            words = [word for word in words if word not in stop_words]
            all_words.extend(words)
        
        return [word for word, count in Counter(all_words).most_common()]
    
    def _analyze_style_patterns(self, snippets):
        """Analyze writing style patterns"""
        patterns = {
            "formal_language": 0,
            "casual_language": 0,
            "question_usage": 0,
            "exclamation_usage": 0,
            "average_length": 0
        }
        
        formal_indicators = ['please', 'thank you', 'regards', 'sincerely', 'kindly', 'pursuant']
        casual_indicators = ['hey', 'hi', 'thanks', 'cool', 'great', 'awesome']
        
        total_snippets = len(snippets)
        if total_snippets == 0:
            return patterns
        
        total_length = 0
        
        for snippet in snippets:
            if not snippet:
                continue
                
            snippet_lower = snippet.lower()
            total_length += len(snippet)
            
            # Count formal vs casual language
            formal_count = sum(1 for word in formal_indicators if word in snippet_lower)
            casual_count = sum(1 for word in casual_indicators if word in snippet_lower)
            
            if formal_count > casual_count:
                patterns["formal_language"] += 1
            elif casual_count > 0:
                patterns["casual_language"] += 1
            
            # Count punctuation usage
            if '?' in snippet:
                patterns["question_usage"] += 1
            if '!' in snippet:
                patterns["exclamation_usage"] += 1
        
        # Convert to percentages
        patterns["formal_language"] = round((patterns["formal_language"] / total_snippets) * 100, 1)
        patterns["casual_language"] = round((patterns["casual_language"] / total_snippets) * 100, 1)
        patterns["question_usage"] = round((patterns["question_usage"] / total_snippets) * 100, 1)
        patterns["exclamation_usage"] = round((patterns["exclamation_usage"] / total_snippets) * 100, 1)
        patterns["average_length"] = round(total_length / total_snippets, 0)
        
        return patterns
    
    def _extract_greetings(self, snippets):
        """Extract common greeting patterns"""
        greetings = []
        greeting_patterns = [
            r'^hi\b', r'^hello\b', r'^dear\b', r'^good morning\b', 
            r'^good afternoon\b', r'^hope this email finds you\b'
        ]
        
        import re
        for snippet in snippets[:50]:  # Check first 50 emails
            if not snippet:
                continue
            snippet_lower = snippet.lower()
            for pattern in greeting_patterns:
                if re.search(pattern, snippet_lower):
                    # Extract the first sentence as greeting
                    sentences = snippet.split('.')[0]
                    if len(sentences) < 100:  # Reasonable greeting length
                        greetings.append(sentences.strip())
                    break
        
        # Return most common greetings
        from collections import Counter
        return [greeting for greeting, count in Counter(greetings).most_common(5)]
    
    def _extract_closings(self, snippets):
        """Extract common closing patterns"""
        closings = []
        closing_patterns = [
            r'best regards', r'sincerely', r'thank you', r'thanks',
            r'best', r'regards', r'kind regards'
        ]
        
        import re
        for snippet in snippets[:50]:  # Check first 50 emails
            if not snippet:
                continue
            snippet_lower = snippet.lower()
            for pattern in closing_patterns:
                if pattern in snippet_lower:
                    # Extract the last sentence as closing
                    sentences = snippet.split('.')[-2:]  # Last 1-2 sentences
                    closing_text = '. '.join(sentences).strip()
                    if len(closing_text) < 150:  # Reasonable closing length
                        closings.append(closing_text)
                    break
        
        from collections import Counter
        return [closing for closing, count in Counter(closings).most_common(5)]
    
    def _analyze_tone(self, snippets):
        """Analyze tone indicators"""
        tone_words = {
            "professional": ["please", "kindly", "thank you", "regards", "sincerely"],
            "urgent": ["urgent", "asap", "immediately", "deadline", "time-sensitive"],
            "friendly": ["hope", "great", "wonderful", "appreciate", "happy"],
            "follow_up": ["following up", "follow up", "checking in", "touching base", "update"]
        }
        
        tone_counts = {tone: 0 for tone in tone_words.keys()}
        total_snippets = len(snippets)
        
        if total_snippets == 0:
            return tone_counts
        
        for snippet in snippets:
            if not snippet:
                continue
            snippet_lower = snippet.lower()
            for tone, words in tone_words.items():
                if any(word in snippet_lower for word in words):
                    tone_counts[tone] += 1
        
        # Convert to percentages
        return {tone: round((count / total_snippets) * 100, 1) for tone, count in tone_counts.items()}
    
    def _display_cadence_summary(self):
        """Display cadence analysis summary"""
        if not self.cadence:
            print("❌ No cadence data available")
            return
        
        print("\n" + "="*60)
        print("📊 EMAIL CADENCE ANALYSIS SUMMARY")
        print("="*60)
        
        print(f"📧 Emails analyzed for cadence: {self.cadence.get('total_emails_analyzed', 0)}")
        print(f"📦 Total emails in cache: {self.cadence.get('total_emails_cached', 0)}")
        print(f"⏰ Average frequency: {self.cadence.get('average_frequency_days', 0)} days")
        
        style = self.cadence.get('style_patterns', {})
        print(f"\n✍️ Writing Style:")
        print(f"   Formal language: {style.get('formal_language', 0)}%")
        print(f"   Casual language: {style.get('casual_language', 0)}%")
        print(f"   Average length: {style.get('average_length', 0)} characters")
        
        tone = self.cadence.get('tone_indicators', {})
        print(f"\n🎯 Tone Distribution:")
        for tone_type, percentage in tone.items():
            print(f"   {tone_type.replace('_', ' ').title()}: {percentage}%")
        
        print(f"\n📝 Common subject words: {', '.join(self.cadence.get('common_subject_words', [])[:5])}")
    
    def get_cadence_guidance(self):
        """Get cadence guidance for email drafting"""
        if not self.cadence:
            return {
                "tone": "professional",
                "style": "formal",
                "greeting": "Dear [Name],",
                "closing": "Best regards,\nDean Hyland\nProhealth Advanced Imaging"
            }
        
        style = self.cadence.get('style_patterns', {})
        tone = self.cadence.get('tone_indicators', {})
        greetings = self.cadence.get('greeting_patterns', [])
        closings = self.cadence.get('closing_patterns', [])
        
        # Determine preferred style
        preferred_style = "formal" if style.get('formal_language', 0) > style.get('casual_language', 0) else "casual"
        
        # Determine primary tone
        primary_tone = max(tone, key=tone.get) if tone else "professional"
        
        return {
            "tone": primary_tone,
            "style": preferred_style,
            "greeting": greetings[0] if greetings else "Dear [Name],",
            "closing": "Thank you",  # Gmail adds signature automatically
            "avg_length": style.get('average_length', 200)
        }
    
    def is_cache_stale(self, max_age_days=7):
        """Check if email cache needs refreshing"""
        if not self.cache.get('last_updated'):
            return True
        
        try:
            last_updated = datetime.fromisoformat(self.cache['last_updated'])
            age = datetime.now() - last_updated
            return age.days > max_age_days
        except:
            return True
    
    def _can_do_incremental_update(self):
        """Check if we can perform an incremental update"""
        return (
            self.cache.get('emails') and 
            self.cache.get('last_sync_time') and
            len(self.cache['emails']) > 0
        )
    
    def _full_sync(self, max_results=None):
        """Perform a full sync of all emails (sent and received)"""
        if max_results:
            print(f"📥 Performing full sync: Downloading {max_results} emails...")
        else:
            print(f"📥 Performing full sync: Downloading ALL emails (sent & received)...")
        
        # Search for ALL emails (both sent and received)
        # Using label:sent OR label:inbox to get both directions
        query = "in:sent OR in:inbox"
        sent_emails = self.gmail_service.search_messages(query, max_results)
        
        if not sent_emails:
            print("❌ No sent emails found")
            return []
        
        print(f"✅ Downloaded {len(sent_emails)} emails (sent & received)")
        
        # Get the latest history ID from the most recent email
        latest_history_id = None
        if sent_emails:
            try:
                latest_msg = self.gmail_service.get_message(sent_emails[0]['id'])
                if latest_msg:
                    latest_history_id = latest_msg.get('historyId')
            except:
                pass
        
        # Update cache
        self.cache = {
            "emails": sent_emails,
            "last_updated": datetime.now().isoformat(),
            "last_sync_time": datetime.now().isoformat(),
            "last_history_id": latest_history_id,
            "total_count": len(sent_emails)
        }
        
        self._save_cache()
        
        # Analyze cadence using last 500 emails from cache
        self.analyze_cadence()
        
        return sent_emails
    
    def _incremental_update(self, max_results=None):
        """Perform an incremental update, only fetching new emails since last sync"""
        print("🔄 Performing incremental update: Fetching only new emails...")
        
        last_sync = datetime.fromisoformat(self.cache['last_sync_time'])
        time_diff = datetime.now() - last_sync
        
        # Convert datetime to Gmail query format (YYYY/MM/DD)
        after_date = last_sync.strftime('%Y/%m/%d')
        
        # Build query for new emails (both sent and received) since last sync
        query = f"(in:sent OR in:inbox) after:{after_date}"
        
        print(f"   Checking for emails sent after {after_date} ({time_diff.days} days ago)")
        
        # Fetch new emails (no limit unless specified)
        new_emails = self.gmail_service.search_messages(query, max_results)
        
        if not new_emails:
            print("✅ No new emails since last sync")
            self.cache['last_updated'] = datetime.now().isoformat()
            self._save_cache()
            return self.cache['emails']
        
        print(f"📬 Found {len(new_emails)} new emails")
        
        # Merge new emails with existing cache
        existing_ids = {email['id'] for email in self.cache['emails']}
        truly_new = [email for email in new_emails if email['id'] not in existing_ids]
        
        if truly_new:
            print(f"   Adding {len(truly_new)} new unique emails to cache")
            # Add new emails to the beginning of the list (most recent first)
            self.cache['emails'] = truly_new + self.cache['emails']
            
        
        # Update metadata
        self.cache['last_updated'] = datetime.now().isoformat()
        self.cache['last_sync_time'] = datetime.now().isoformat()
        self.cache['total_count'] = len(self.cache['emails'])
        
        # Get the latest history ID if we have new emails
        if new_emails:
            try:
                latest_msg = self.gmail_service.get_message(new_emails[0]['id'])
                if latest_msg:
                    self.cache['last_history_id'] = latest_msg.get('historyId')
            except:
                pass
        
        self._save_cache()
        
        # Re-analyze cadence with updated data
        if truly_new:
            print("🧠 Updating cadence analysis with new data...")
            self.analyze_cadence()
        
        print(f"✅ Cache updated: {len(self.cache['emails'])} total emails")
        return self.cache['emails']
    
    def force_full_sync(self, max_results=None):
        """Force a full sync regardless of cache state
        
        Args:
            max_results (int): Maximum emails to fetch (None = all emails)
        """
        print("⚡ Forcing full sync...")
        return self._full_sync(max_results)
    
    def get_cache_stats(self):
        """Get statistics about the current cache"""
        if not self.cache.get('emails'):
            return {
                "status": "empty",
                "email_count": 0,
                "last_updated": None,
                "last_sync": None
            }
        
        last_updated = self.cache.get('last_updated')
        last_sync = self.cache.get('last_sync_time')
        
        stats = {
            "status": "populated",
            "email_count": len(self.cache['emails']),
            "last_updated": last_updated,
            "last_sync": last_sync,
            "cache_age_days": None,
            "sync_age_days": None
        }
        
        if last_updated:
            try:
                updated_dt = datetime.fromisoformat(last_updated)
                stats["cache_age_days"] = (datetime.now() - updated_dt).days
            except:
                pass
        
        if last_sync:
            try:
                sync_dt = datetime.fromisoformat(last_sync)
                stats["sync_age_days"] = (datetime.now() - sync_dt).days
            except:
                pass
        
        return stats
    
    def _is_sent_email(self, email):
        """Check if an email was sent by us (not received)"""
        # Check various indicators that this is a sent email
        from_field = email.get('from', '').lower()
        
        # Try to load user-specific indicators
        sent_indicators = self._get_sent_indicators()
        
        return any(indicator in from_field for indicator in sent_indicators)
    
    def _get_sent_indicators(self):
        """Get email indicators from user config or defaults"""
        # Try to load from user config first
        try:
            import os
            config_file = "data/email_indicators.json"
            if os.path.exists(config_file):
                import json
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    indicators = data.get('sent_indicators', [])
                    if indicators:
                        return indicators
        except:
            pass
        
        # Fall back to defaults (for existing users)
        return [
            'deanh.transcon@gmail.com',
            'dean',
            'prohealth',
            'transcon'
        ]
    
    def get_all_emails_for_case(self, search_query):
        """Get all cached emails matching a search query
        
        Args:
            search_query (str): Search terms to match against cached emails
            
        Returns:
            list: Matching emails from cache
        """
        if not self.cache.get('emails'):
            return []
        
        matching_emails = []
        search_terms = search_query.lower().split()
        
        for email in self.cache['emails']:
            # Check if any search term matches email fields
            email_text = f"{email.get('subject', '')} {email.get('snippet', '')} {email.get('from', '')} {email.get('to', '')}".lower()
            
            if any(term in email_text for term in search_terms):
                matching_emails.append(email)
        
        return matching_emails