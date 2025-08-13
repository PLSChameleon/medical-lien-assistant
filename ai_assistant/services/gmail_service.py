import os
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

logger = logging.getLogger(__name__)

class GmailService:
    """Gmail API service wrapper"""
    
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        creds = None
        
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", Config.GMAIL_SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Successfully refreshed Gmail credentials")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    raise Exception("Failed to refresh Gmail token. Please re-authenticate.")
            else:
                raise Exception(
                    "No valid Gmail token found. Please run the authentication setup first.\n"
                    "Make sure you have credentials.json in your project directory."
                )
        
        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail service authenticated successfully")
    
    def search_messages(self, query, max_results=None):
        """
        Search Gmail messages with a query
        
        Args:
            query (str): Gmail search query
            max_results (int): Maximum number of results to return (None = get ALL)
            
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
            if fetch_all:
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
                        print(f"   📧 Fetched {len(all_messages)} emails so far...")
                        logger.info(f"Fetched {len(all_messages)} messages so far...")
            
            if len(all_messages) > 0:
                print(f"   ✅ Total emails found: {len(all_messages)}")
            logger.info(f"Found {len(all_messages)} messages for query: {query}")
            return all_messages
            
        except Exception as e:
            logger.error(f"Error searching Gmail: {e}")
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