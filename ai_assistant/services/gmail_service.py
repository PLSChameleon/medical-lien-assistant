import os
import sys
import base64
from email.mime.text import MIMEText
from base64 import urlsafe_b64encode
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from datetime import datetime
import json
import logging
from config import Config

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.seamless_gmail_auth import authenticate_gmail

logger = logging.getLogger(__name__)

class GmailService:
    """Gmail API service wrapper"""
    
    def __init__(self, email_cache_service=None):
        self.service = None
        self.email_cache_service = email_cache_service
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using seamless OAuth2"""
        # Look for credentials and token in the ai_assistant directory
        base_dir = os.path.dirname(os.path.dirname(__file__))
        token_path = os.path.join(base_dir, "token.json")
        credentials_path = os.path.join(base_dir, "credentials.json")
        
        try:
            # Use seamless authentication
            creds = authenticate_gmail(
                credentials_file=credentials_path,
                token_file=token_path,
                scopes=Config.GMAIL_SCOPES
            )
            
            self.service = build("gmail", "v1", credentials=creds)
            logger.info("Gmail service authenticated successfully")
            
        except FileNotFoundError as e:
            logger.error(f"Credentials file not found: {e}")
            raise Exception(
                "Gmail credentials.json not found in ai_assistant directory.\n"
                "Please ensure credentials.json is present before running."
            )
        except TimeoutError as e:
            logger.error(f"Authentication timeout: {e}")
            raise Exception(
                "Gmail authentication timed out.\n"
                "Please try again and make sure to click 'Allow' in your browser."
            )
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise Exception(f"Failed to authenticate with Gmail: {e}")
    
    def search_messages(self, query, max_results=None, progress=None):
        """
        Search Gmail messages with a query
        
        Args:
            query (str): Gmail search query
            max_results (int): Maximum number of results to return (None = get ALL)
            progress: Optional progress manager for UI updates
            
        Returns:
            list: List of message dictionaries with headers and content
        """
        try:
            all_messages = []
            page_token = None
            
            # Determine how many to fetch
            if max_results is None:
                # Fetch ALL emails using pagination
                fetch_all = True
                per_request = 100  # Fetch 100 at a time
            else:
                fetch_all = False
                per_request = min(max_results, 100) if max_results > 0 else Config.MAX_EMAIL_RESULTS
            
            # Print initial status for user feedback
            if progress:
                progress.log(f"🔍 Query: {query}")
                if fetch_all:
                    progress.log("⏳ Fetching all emails in batches of 100...")
                progress.process_events()
            elif fetch_all:
                print(f"   🔍 Searching Gmail with query: {query}")
                print("   ⏳ Starting to fetch emails in batches of 100...")
            
            while True:
                # Build request parameters
                params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': per_request
                }
                if page_token:
                    params['pageToken'] = page_token
                
                # Execute request
                response = self.service.users().messages().list(**params).execute()
                
                messages = response.get("messages", [])
                if not messages:
                    break
                
                # Process this batch
                batch_count = 0
                for msg in messages:
                    if not fetch_all and len(all_messages) >= max_results:
                        break
                        
                    message = self.service.users().messages().get(
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
                    # Update progress every 10 messages within batch
                    if progress and batch_count % 10 == 0:
                        progress.process_events()
                
                # Check if we should continue
                if not fetch_all and len(all_messages) >= max_results:
                    break
                
                # Get next page token
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                
                # Log progress for large fetches
                if fetch_all:
                    if len(all_messages) % 100 == 0 and len(all_messages) > 0:
                        msg = f"📧 Fetched {len(all_messages)} emails so far..."
                        if progress:
                            progress.log(msg)
                            progress.process_events()
                        else:
                            print(f"   {msg}")
                        logger.info(f"Fetched {len(all_messages)} messages so far...")
            
            if len(all_messages) > 0:
                msg = f"✅ Total emails found: {len(all_messages)}"
                if progress:
                    progress.log(msg)
                    progress.process_events()
                else:
                    print(f"   {msg}")
            logger.info(f"Found {len(all_messages)} messages for query: {query}")
            return all_messages
            
        except Exception as e:
            logger.error(f"Error searching Gmail: {e}")
            raise Exception(f"Failed to search Gmail: {e}")
    
    def search_messages_threaded(self, query, max_results=None, progress_callback=None):
        """
        Thread-safe version of search_messages for background execution
        
        Args:
            query (str): Gmail search query
            max_results (int): Maximum number of results to return (None = get ALL)
            progress_callback: Callback function(percentage, message, log)
            
        Returns:
            list: List of message dictionaries with headers and content
        """
        try:
            all_messages = []
            page_token = None
            
            # Determine how many to fetch
            if max_results is None:
                fetch_all = True
                per_request = 100
            else:
                fetch_all = False
                per_request = min(max_results, 100) if max_results > 0 else Config.MAX_EMAIL_RESULTS
            
            # Initial status
            if progress_callback:
                progress_callback(0, f"Searching Gmail: {query}", f"🔍 Query: {query}")
                if fetch_all:
                    progress_callback(0, "Starting batch fetch...", "⏳ Fetching emails in batches of 100...")
            
            batch_number = 0
            while True:
                # Build request parameters
                params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': per_request
                }
                if page_token:
                    params['pageToken'] = page_token
                
                # Execute request
                response = self.service.users().messages().list(**params).execute()
                
                messages = response.get("messages", [])
                if not messages:
                    break
                
                batch_number += 1
                
                # Process this batch
                batch_count = 0
                for msg in messages:
                    if not fetch_all and len(all_messages) >= max_results:
                        break
                    
                    message = self.service.users().messages().get(
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
                    
                    # Update progress every 10 emails within batch
                    if progress_callback and batch_count % 10 == 0:
                        percentage = min(90, int((len(all_messages) / (max_results or 1000)) * 100))
                        progress_callback(
                            percentage,
                            f"Processing email {len(all_messages)}...",
                            None
                        )
                
                # Log progress for large fetches
                if fetch_all and len(all_messages) % 100 == 0 and len(all_messages) > 0:
                    if progress_callback:
                        progress_callback(
                            min(90, int((len(all_messages) / 1000) * 100)),
                            f"Processing batch {batch_number}...",
                            f"📧 Fetched {len(all_messages)} emails so far..."
                        )
                    logger.info(f"Fetched {len(all_messages)} messages so far...")
                
                # Check if we should continue
                if not fetch_all and len(all_messages) >= max_results:
                    break
                
                # Get next page token
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            if len(all_messages) > 0:
                if progress_callback:
                    progress_callback(
                        90,
                        f"Found {len(all_messages)} emails",
                        f"✅ Total emails found: {len(all_messages)}"
                    )
            
            logger.info(f"Found {len(all_messages)} messages for query: {query}")
            return all_messages
            
        except Exception as e:
            logger.error(f"Error in threaded Gmail search: {e}")
            if progress_callback:
                progress_callback(100, f"Error: {e}", f"❌ Error: {e}")
            raise Exception(f"Failed to search Gmail: {e}")
    
    def get_thread(self, message_id):
        """
        Get full thread for a message
        
        Args:
            message_id (str): Gmail message ID
            
        Returns:
            dict: Full thread data
        """
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            thread_id = message.get("threadId")
            thread = self.service.users().threads().get(
                userId='me', 
                id=thread_id, 
                format='full'
            ).execute()
            
            return thread
            
        except Exception as e:
            logger.error(f"Error fetching thread for message {message_id}: {e}")
            return {}
    
    def send_email(self, recipient_email, subject, body, thread_id=None):
        """
        Send an email
        
        Args:
            recipient_email (str): Recipient email address
            subject (str): Email subject
            body (str): Email body
            thread_id (str, optional): Thread ID for replies
            
        Returns:
            str: Sent message ID
        """
        try:
            message = MIMEText(body)
            message["to"] = recipient_email
            if subject:
                message["subject"] = subject
            
            raw = urlsafe_b64encode(message.as_bytes()).decode()
            message_data = {"raw": raw}
            
            if thread_id:
                message_data["threadId"] = thread_id
            
            sent_message = self.service.users().messages().send(
                userId="me", 
                body=message_data
            ).execute()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            
            # Immediately add to email cache if available
            if self.email_cache_service:
                try:
                    self.email_cache_service.add_sent_email_to_cache(
                        message_id=sent_message["id"],
                        recipient=recipient_email,
                        subject=subject,
                        body_snippet=body[:200] if body else "",
                        thread_id=thread_id
                    )
                    logger.info(f"Email auto-cached: {sent_message['id']}")
                except Exception as e:
                    logger.warning(f"Failed to auto-cache sent email: {e}")
            
            return sent_message["id"]
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            raise Exception(f"Failed to send email: {e}")
    
    def get_message(self, message_id):
        """
        Get a specific Gmail message by ID
        
        Args:
            message_id (str): Gmail message ID
            
        Returns:
            dict: Full message data
        """
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            return message
            
        except Exception as e:
            logger.error(f"Error fetching message {message_id}: {e}")
            return None

    def extract_message_body(self, message):
        """
        Extract plain text body from a Gmail message
        
        Args:
            message (dict): Gmail message object
            
        Returns:
            str: Plain text body
        """
        try:
            body = ""
            payload = message.get("payload", {})
            
            if payload.get("mimeType") == "text/plain":
                body_data = payload.get("body", {}).get("data", "")
            else:
                for part in payload.get("parts", []):
                    if part.get("mimeType") == "text/plain":
                        body_data = part.get("body", {}).get("data", "")
                        break
                else:
                    body_data = ""
            
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
            
            return body
            
        except Exception as e:
            logger.error(f"Error extracting message body: {e}")
            return ""