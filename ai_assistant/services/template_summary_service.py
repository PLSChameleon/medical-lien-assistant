"""
Template-based Summary Service
Generates high-quality case summaries from email cache without requiring AI API calls
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class TemplateSummaryService:
    """Generate intelligent summaries from email cache data"""
    
    def __init__(self, email_cache_service=None, case_manager=None):
        self.email_cache = email_cache_service
        self.case_manager = case_manager
        
        # Email extraction patterns
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Key phrase patterns for detecting important events
        self.settlement_patterns = [
            r'settl(e|ed|ement|ing)',
            r'resolv(e|ed|ing)',
            r'agree(d|ment)',
            r'offer',
            r'demand',
            r'negotiat'
        ]
        
        self.reduction_patterns = [
            r'reduc(e|ed|tion|ing)',
            r'discount',
            r'lower(ed|ing)?',
            r'decrease'
        ]
        
        self.urgent_patterns = [
            r'urgent',
            r'immediate(ly)?',
            r'asap',
            r'time.?sensitive',
            r'deadline',
            r'expire'
        ]
        
        self.status_keywords = {
            'pending': ['pending', 'open', 'active', 'ongoing', 'in progress'],
            'settled': ['settled', 'closed', 'resolved', 'complete', 'paid'],
            'dropped': ['dropped', 'dismissed', 'withdrawn', 'abandoned'],
            'litigation': ['litigation', 'lawsuit', 'court', 'trial', 'filed suit']
        }
    
    def generate_summary(self, pv: str, case_data: Dict = None) -> str:
        """
        Generate comprehensive summary for a case
        
        Args:
            pv: Patient Visit number
            case_data: Optional case data from case manager
            
        Returns:
            Formatted summary string
        """
        try:
            # Get case data if not provided
            if not case_data and self.case_manager:
                case_data = self.case_manager.get_case_by_pv(pv)
            
            # Get email history from cache
            email_history = self._get_email_history(pv, case_data)
            
            # Analyze the email patterns
            analysis = self._analyze_email_patterns(email_history)
            
            # Extract email addresses from conversations
            found_emails = self._extract_email_addresses(email_history)
            
            # Generate status determination
            status = self._determine_case_status(analysis, email_history)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis, status)
            
            # Format the summary
            summary = self._format_summary(
                pv, case_data, email_history, analysis, 
                status, recommendations, found_emails
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary for PV {pv}: {e}")
            return f"Error generating summary: {str(e)}"
    
    def _get_email_history(self, pv: str, case_data: Dict = None) -> List[Dict]:
        """Get email history from cache - searching by patient NAME primarily"""
        emails = []
        
        if self.email_cache:
            # IMPORTANT: Search by patient NAME first (not PV)
            # Users rarely include PV in emails
            if case_data and case_data.get('Name'):
                patient_name = case_data.get('Name', '')
                doi = case_data.get('DOI') if case_data else None
                
                # Use the improved patient name search with DOI filtering
                logger.info(f"Searching emails for patient: {patient_name}")
                
                # Check if the email cache has our new method
                if hasattr(self.email_cache, 'search_emails_by_patient_name'):
                    name_emails = self.email_cache.search_emails_by_patient_name(patient_name, doi)
                else:
                    # Fallback to the standard method
                    name_emails = self.email_cache.get_all_emails_for_case(patient_name)
                
                logger.info(f"Found {len(name_emails)} emails for {patient_name}")
                emails.extend(name_emails)
            
            # As a fallback, also try searching by PV (in case it's in Reference # line)
            if pv:
                pv_emails = self.email_cache.get_case_emails(pv)
                # Add any PV-based emails not already found
                existing_ids = {e.get('id') for e in emails}
                for email in pv_emails:
                    if email.get('id') and email.get('id') not in existing_ids:
                        emails.append(email)
        
        # Sort by date (newest first)
        emails.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return emails
    
    def _analyze_email_patterns(self, emails: List[Dict]) -> Dict:
        """Analyze email patterns for insights"""
        analysis = {
            'total_emails': len(emails),
            'emails_sent': 0,
            'emails_received': 0,
            'last_contact_date': None,
            'last_response_date': None,
            'first_contact_date': None,
            'response_times': [],
            'no_response_count': 0,
            'settlement_mentioned': False,
            'reduction_mentioned': False,
            'urgent_mentioned': False,
            'key_events': [],
            'communication_gaps': [],
            'response_rate': 0,
            'avg_response_time': None
        }
        
        if not emails:
            return analysis
        
        # Categorize emails
        our_domains = ['prohealth', 'transcon', 'dean']
        sent_emails = []
        received_emails = []
        
        for email in emails:
            from_addr = (email.get('from') or '').lower()
            to_addr = (email.get('to') or '').lower()
            is_from_us = any(domain in from_addr for domain in our_domains)
            
            if is_from_us:
                sent_emails.append(email)
                analysis['emails_sent'] += 1
            else:
                received_emails.append(email)
                analysis['emails_received'] += 1
            
            # Check for key phrases
            body = (email.get('body') or '').lower() + ' ' + (email.get('snippet') or '').lower()
            
            if any(re.search(pattern, body) for pattern in self.settlement_patterns):
                analysis['settlement_mentioned'] = True
                analysis['key_events'].append({
                    'date': email.get('date'),
                    'type': 'settlement_discussion',
                    'detail': 'Settlement mentioned in correspondence'
                })
            
            if any(re.search(pattern, body) for pattern in self.reduction_patterns):
                analysis['reduction_mentioned'] = True
                analysis['key_events'].append({
                    'date': email.get('date'),
                    'type': 'reduction_discussion',
                    'detail': 'Reduction or discount discussed'
                })
            
            if any(re.search(pattern, body) for pattern in self.urgent_patterns):
                analysis['urgent_mentioned'] = True
                analysis['key_events'].append({
                    'date': email.get('date'),
                    'type': 'urgent_matter',
                    'detail': 'Urgent or time-sensitive matter noted'
                })
        
        # Calculate dates and gaps
        if emails:
            analysis['first_contact_date'] = emails[-1].get('date')
            analysis['last_contact_date'] = emails[0].get('date')
        
        if received_emails:
            analysis['last_response_date'] = received_emails[0].get('date')
        
        if sent_emails:
            # Count unanswered emails
            last_response = analysis['last_response_date']
            if last_response:
                for sent in sent_emails:
                    if sent.get('date') > last_response:
                        analysis['no_response_count'] += 1
            else:
                analysis['no_response_count'] = len(sent_emails)
        
        # Calculate response rate
        if analysis['emails_sent'] > 0:
            analysis['response_rate'] = (
                analysis['emails_received'] / analysis['emails_sent'] * 100
            )
        
        # Find communication gaps (periods > 30 days between emails)
        if len(emails) > 1:
            for i in range(len(emails) - 1):
                current_date = self._parse_date(emails[i].get('date'))
                next_date = self._parse_date(emails[i + 1].get('date'))
                
                if current_date and next_date:
                    # Ensure both dates are timezone-naive
                    if current_date.tzinfo is not None:
                        current_date = current_date.replace(tzinfo=None)
                    if next_date.tzinfo is not None:
                        next_date = next_date.replace(tzinfo=None)
                    
                    try:
                        gap_days = (current_date - next_date).days
                    except TypeError:
                        continue  # Skip if we can't calculate the gap
                    
                    if gap_days > 30:
                        analysis['communication_gaps'].append({
                            'start': next_date.strftime('%m/%d/%Y'),
                            'end': current_date.strftime('%m/%d/%Y'),
                            'days': gap_days
                        })
        
        return analysis
    
    def _extract_email_addresses(self, emails: List[Dict]) -> Set[str]:
        """Extract email addresses mentioned in email bodies"""
        found_emails = set()
        
        # Our own domains to exclude
        exclude_domains = ['prohealth', 'transcon', 'gmail.com']
        
        for email in emails:
            # Check email body
            body = email.get('body') or ''
            snippet = email.get('snippet') or ''
            full_text = f"{body} {snippet}"
            
            # Find all email addresses
            matches = self.email_pattern.findall(full_text)
            
            for match in matches:
                # Filter out our own emails and common domains
                if not any(domain in match.lower() for domain in exclude_domains):
                    # Look for context around the email
                    context = self._get_email_context(full_text, match)
                    if self._is_relevant_email(context):
                        found_emails.add(match.lower())
        
        return found_emails
    
    def _get_email_context(self, text: str, email: str) -> str:
        """Get context around an email address"""
        try:
            if not text:
                return ""
            index = text.lower().index(email.lower())
            start = max(0, index - 100)
            end = min(len(text), index + 100)
            return text[start:end]
        except (ValueError, AttributeError):
            return ""
    
    def _is_relevant_email(self, context: str) -> bool:
        """Check if email context suggests it's for correspondence"""
        relevant_phrases = [
            'email', 'contact', 'send', 'forward', 'correspondence',
            'reach', 'reply', 'respond', 'cc', 'questions', 'inquir'
        ]
        context_lower = context.lower()
        return any(phrase in context_lower for phrase in relevant_phrases)
    
    def _determine_case_status(self, analysis: Dict, emails: List[Dict]) -> Dict:
        """Determine current case status from patterns"""
        status = {
            'current_status': 'Unknown',
            'confidence': 0,
            'details': [],
            'days_since_last_contact': None,
            'days_since_last_response': None,
            'requires_action': False
        }
        
        # Calculate days since contacts (handle timezone issues)
        if analysis.get('last_contact_date'):
            last_contact = self._parse_date(analysis['last_contact_date'])
            if last_contact:
                # Ensure both datetimes are timezone-naive for comparison
                now = datetime.now()
                if last_contact.tzinfo is not None:
                    # Convert timezone-aware to naive (local time)
                    last_contact = last_contact.replace(tzinfo=None)
                try:
                    days_since = (now - last_contact).days
                    status['days_since_last_contact'] = days_since
                except TypeError:
                    # If still having issues, log and continue
                    logger.warning(f"Could not calculate days since last contact")
        
        if analysis.get('last_response_date'):
            last_response = self._parse_date(analysis['last_response_date'])
            if last_response:
                # Ensure both datetimes are timezone-naive for comparison
                now = datetime.now()
                if last_response.tzinfo is not None:
                    # Convert timezone-aware to naive (local time)
                    last_response = last_response.replace(tzinfo=None)
                try:
                    days_since = (now - last_response).days
                    status['days_since_last_response'] = days_since
                except TypeError:
                    # If still having issues, log and continue
                    logger.warning(f"Could not calculate days since last response")
        
        # Determine status based on patterns
        no_response_count = analysis.get('no_response_count', 0)
        if no_response_count >= 3:
            status['current_status'] = 'No Response - Multiple Attempts'
            status['confidence'] = 90
            status['requires_action'] = True
            status['details'].append('No response after 3+ attempts')
        elif no_response_count >= 1:
            status['current_status'] = 'Awaiting Response'
            status['confidence'] = 80
            status['requires_action'] = True
            status['details'].append(f"{no_response_count} unanswered email(s)")
        elif analysis.get('settlement_mentioned', False):
            status['current_status'] = 'Settlement Discussion'
            status['confidence'] = 85
            status['details'].append('Settlement has been discussed')
        elif analysis.get('emails_received', 0) > 0:
            if status['days_since_last_response'] and status['days_since_last_response'] < 30:
                status['current_status'] = 'Active - Recent Response'
                status['confidence'] = 90
                status['details'].append('Recent attorney response')
            else:
                status['current_status'] = 'Active - Follow-up Needed'
                status['confidence'] = 75
                status['requires_action'] = True
                status['details'].append('No recent activity')
        else:
            status['current_status'] = 'Initial Outreach'
            status['confidence'] = 70
            status['requires_action'] = True
            status['details'].append('No response received yet')
        
        # Check for urgent matters
        if analysis.get('urgent_mentioned', False):
            status['requires_action'] = True
            status['details'].append('[!] Urgent matter noted')
        
        return status
    
    def _generate_recommendations(self, analysis: Dict, status: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on response patterns
        no_response_count = analysis.get('no_response_count', 0)
        if no_response_count >= 3:
            recommendations.append("Consider phone follow-up - multiple emails unanswered")
            recommendations.append("Verify attorney email address is correct")
        elif no_response_count >= 1:
            recommendations.append("Send follow-up email or attempt phone contact")
        
        # Based on time gaps
        days_since_response = status.get('days_since_last_response')
        if days_since_response and days_since_response > 60:
            recommendations.append("High priority - No response in 60+ days")
        elif days_since_response and days_since_response > 30:
            recommendations.append("Follow up - No response in 30+ days")
        
        # Based on case status
        if analysis.get('settlement_mentioned', False):
            recommendations.append("Monitor settlement progress closely")
            recommendations.append("Prepare final billing documentation")
        
        if analysis.get('reduction_mentioned', False):
            recommendations.append("Review reduction request and prepare response")
        
        if analysis.get('urgent_mentioned', False):
            recommendations.append("[!] Address urgent matter immediately")
        
        # Check for statute of limitations (2 years)
        days_since_contact = status.get('days_since_last_contact')
        if days_since_contact and days_since_contact > 700:
            recommendations.append("Consider CCP 335.1 inquiry - approaching 2-year statute")
        
        # If no specific recommendations, provide general guidance
        if not recommendations:
            if status.get('requires_action', False):
                recommendations.append("Follow up on case status")
            else:
                recommendations.append("Continue monitoring case progress")
        
        return recommendations
    
    def _format_summary(self, pv: str, case_data: Dict, emails: List[Dict],
                       analysis: Dict, status: Dict, recommendations: List[str],
                       found_emails: Set[str]) -> str:
        """Format the complete summary"""
        
        # Get case details
        name = case_data.get('Name', 'Unknown') if case_data else 'Unknown'
        doi = case_data.get('DOI', 'Unknown') if case_data else 'Unknown'
        balance = case_data.get('Balance', 0) if case_data else 0
        attorney = case_data.get('Attorney Email', 'Unknown') if case_data else 'Unknown'
        law_firm = case_data.get('Law Firm', 'Unknown') if case_data else 'Unknown'
        cms_number = case_data.get('CMS', 'Unknown') if case_data else 'Unknown'
        
        # Format dates
        if isinstance(doi, datetime):
            doi_str = doi.strftime('%m/%d/%Y')
        else:
            doi_str = str(doi)
        
        # Build summary sections
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"CASE SUMMARY - {name}")
        lines.append(f"{'='*60}")
        lines.append(f"PV #: {pv}")
        lines.append(f"CMS #: {cms_number}")
        lines.append(f"DOI: {doi_str}")
        lines.append(f"Balance: ${balance:,.2f}")
        lines.append(f"Law Firm: {law_firm}")
        lines.append(f"Attorney: {attorney}")
        lines.append("")
        
        # Status Section
        lines.append("CURRENT STATUS")
        lines.append("-" * 40)
        lines.append(f"Status: {status.get('current_status', 'Unknown')}")
        lines.append(f"Confidence: {status.get('confidence', 0)}%")
        if status.get('days_since_last_contact'):
            lines.append(f"Days Since Last Contact: {status['days_since_last_contact']}")
        if status.get('days_since_last_response'):
            lines.append(f"Days Since Attorney Response: {status['days_since_last_response']}")
        if status.get('details'):
            lines.append("Details:")
            for detail in status.get('details', []):
                lines.append(f"  • {detail}")
        lines.append("")
        
        # Communication Summary
        lines.append("COMMUNICATION SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Emails: {analysis.get('total_emails', 0)}")
        lines.append(f"Emails Sent by Us: {analysis.get('emails_sent', 0)}")
        lines.append(f"Attorney Responses: {analysis.get('emails_received', 0)}")
        lines.append(f"Response Rate: {analysis.get('response_rate', 0):.1f}%")
        lines.append(f"Unanswered Emails: {analysis.get('no_response_count', 0)}")
        
        if analysis.get('first_contact_date'):
            first_date = self._format_date(analysis['first_contact_date'])
            lines.append(f"First Contact: {first_date}")
        if analysis.get('last_contact_date'):
            last_date = self._format_date(analysis['last_contact_date'])
            lines.append(f"Most Recent Contact: {last_date}")
        if analysis.get('last_response_date'):
            response_date = self._format_date(analysis['last_response_date'])
            lines.append(f"Last Attorney Response: {response_date}")
        lines.append("")
        
        # Key Events
        key_events = analysis.get('key_events')
        if key_events and isinstance(key_events, list):
            lines.append("KEY EVENTS")
            lines.append("-" * 40)
            for event in key_events[:5]:  # Show top 5 events
                if event and isinstance(event, dict):
                    event_date = self._format_date(event.get('date', ''))
                    detail = event.get('detail', 'Unknown event')
                    lines.append(f"• {event_date}: {detail}")
            lines.append("")
        
        # Communication Gaps
        comm_gaps = analysis.get('communication_gaps')
        if comm_gaps and isinstance(comm_gaps, list):
            lines.append("COMMUNICATION GAPS")
            lines.append("-" * 40)
            for gap in comm_gaps[:3]:  # Show top 3 gaps
                if gap and isinstance(gap, dict):
                    days = gap.get('days', 0)
                    start = gap.get('start', 'Unknown')
                    end = gap.get('end', 'Unknown')
                    lines.append(f"• {days} days: {start} to {end}")
            lines.append("")
        
        # Email Conversation Summary (what was discussed)
        if emails:
            lines.append("EMAIL CONVERSATION SUMMARY")
            lines.append("-" * 40)
            conversation = self._extract_email_conversation_summary(emails)
            # Show up to 10 most recent conversations
            if conversation and isinstance(conversation, list):
                for conv in conversation[-10:]:
                    if conv and isinstance(conv, dict):
                        date = conv.get('date', 'Unknown')
                        direction = conv.get('direction', 'Unknown')
                        summary = conv.get('summary', 'No summary available')
                        lines.append(f"({date}) {direction}: {summary}")
                if len(conversation) > 10:
                    lines.append(f"... and {len(conversation) - 10} earlier emails")
            lines.append("")
        
        # Recent Email Activity (subjects only - last 5)
        if emails and isinstance(emails, list):
            lines.append("RECENT ACTIVITY")
            lines.append("-" * 40)
            for email in emails[:5]:
                date = self._format_date(email.get('date'))
                from_addr = email.get('from') or ''
                is_from_us = 'prohealth' in from_addr.lower() or 'transcon' in from_addr.lower()
                direction = ">> SENT" if is_from_us else "<< RECEIVED"
                subject = email.get('subject', 'No Subject')
                if subject:
                    subject = subject[:50]
                else:
                    subject = 'No Subject'
                lines.append(f"{date} {direction}: {subject}")
            lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDED ACTIONS")
        lines.append("-" * 40)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        # Email Addresses Found
        if found_emails:
            lines.append("EMAIL ADDRESSES FOUND IN CONVERSATIONS")
            lines.append("-" * 40)
            for email_addr in sorted(found_emails):
                lines.append(f"  • {email_addr}")
            lines.append("")
            lines.append("Note: Review context before using alternate email addresses")
        
        # Footer
        lines.append("")
        lines.append(f"Summary generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}")
        lines.append("=" * 60)
        
        # Full Email History (at the very bottom as requested)
        if emails and isinstance(emails, list):
            lines.append("")
            lines.append("")
            lines.append("=" * 60)
            lines.append("FULL EMAIL HISTORY")
            lines.append("=" * 60)
            lines.append("")
            
            # Sort emails by date (oldest first for chronological order)
            sorted_emails = sorted(emails, key=lambda x: x.get('date', ''))
            
            for email in sorted_emails:
                # Extract email details
                date = self._format_date(email.get('date'))
                from_addr = email.get('from') or 'Unknown'
                to_addr = email.get('to') or 'Unknown'
                subject = email.get('subject') or 'No Subject'
                # Use full body if available, otherwise fall back to snippet
                body = email.get('body') or email.get('snippet') or ''
                
                # Remove email signatures (common patterns)
                if body:
                    # Common signature indicators
                    signature_indicators = [
                        '\n--\n',  # Standard email signature delimiter
                        '\nSent from',
                        '\nGet Outlook',
                        '\nThis email was sent',
                        '\nDean Halvorsen\nTranscon',  # Specific to your signature
                        '\nKaren Huizar\nTranscon',  # Another known signature
                        '\nSincerely,',
                        '\nBest regards,',
                        '\nRegards,',
                        '\nThank you,',
                        '\nThanks,',
                    ]
                    
                    # Find the earliest signature indicator
                    earliest_pos = len(body)
                    for indicator in signature_indicators:
                        pos = body.find(indicator)
                        if pos != -1 and pos < earliest_pos:
                            earliest_pos = pos
                    
                    # Truncate at signature if found
                    if earliest_pos < len(body):
                        body = body[:earliest_pos].strip()
                
                # Determine direction
                is_from_us = any(domain in from_addr.lower() for domain in ['prohealth', 'transcon', 'dean'])
                
                if is_from_us:
                    header = f"{date} (SENT To: {to_addr})"
                else:
                    header = f"{date} (RECEIVED From: {from_addr})"
                
                lines.append("-" * 60)
                lines.append(header)
                lines.append(f"Subject: {subject}")
                lines.append("-" * 60)
                
                # Add the full email body
                if body:
                    # Clean up the body text a bit for display
                    body_lines = body.strip().split('\n')
                    for line in body_lines:
                        lines.append(line)
                else:
                    lines.append("[No email body available]")
                
                lines.append("")  # Add spacing between emails
            
            lines.append("=" * 60)
            lines.append("END OF EMAIL HISTORY")
            lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime (always returns timezone-naive)"""
        if not date_str:
            return None
        
        try:
            # Try common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%m/%d/%Y %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S.%f'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    # Ensure timezone-naive
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    return dt
                except ValueError:
                    continue
            
            # If all formats fail, try pandas
            import pandas as pd
            dt = pd.to_datetime(date_str)
            
            # Convert pandas Timestamp to datetime and ensure timezone-naive
            if hasattr(dt, 'to_pydatetime'):
                dt = dt.to_pydatetime()
            
            # Remove timezone info if present
            if dt and dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            
            return dt
            
        except Exception as e:
            logger.debug(f"Could not parse date '{date_str}': {e}")
            return None
    
    def _format_date(self, date_str: str) -> str:
        """Format date string for display"""
        parsed = self._parse_date(date_str)
        if parsed:
            return parsed.strftime('%m/%d/%Y')
        return date_str if date_str else 'Unknown'
    
    def _extract_email_conversation_summary(self, emails: List[Dict]) -> List[Dict]:
        """Extract conversation summary from emails"""
        conversation = []
        
        # Sort emails by date (oldest first for chronological order)
        sorted_emails = sorted(emails, key=lambda x: x.get('date', ''))
        
        for email in sorted_emails:
            from_addr = (email.get('from') or '').lower()
            to_addr = (email.get('to') or '').lower()
            subject = email.get('subject') or ''
            snippet = email.get('snippet') or ''
            body = email.get('body') or snippet  # Use body if available, else snippet
            date = self._format_date(email.get('date'))
            
            # Determine if sent or received
            is_from_us = any(domain in from_addr for domain in ['prohealth', 'transcon', 'dean'])
            direction = "SENT" if is_from_us else "RECEIVED"
            
            # Extract key information from the email content
            summary = self._summarize_email_content(body, subject, from_addr, to_addr, is_from_us)
            
            conversation.append({
                'date': date,
                'direction': direction,
                'summary': summary,
                'from': from_addr,
                'to': to_addr
            })
        
        return conversation
    
    def _summarize_email_content(self, body: str, subject: str, from_addr: str, to_addr: str, is_from_us: bool) -> str:
        """Create a brief summary of email content"""
        body_lower = body.lower() if body else ''
        subject_lower = subject.lower() if subject else ''
        
        # Key phrases to look for
        if is_from_us:
            # Our emails - what did we ask/say?
            if 'status' in body_lower or 'update' in body_lower or 'status' in subject_lower:
                if 'follow' in body_lower or 'following up' in body_lower:
                    return "Following up on previous request for case status"
                return "Requested status update on the case"
            elif 'lien' in body_lower and ('attach' in body_lower or 'enclos' in body_lower):
                return "Sent lien documentation"
            elif 'bill' in body_lower or 'invoice' in body_lower:
                return "Sent billing information"
            elif 'settle' in body_lower:
                return "Discussed settlement matters"
            elif 'doi' in subject_lower or 'date of injury' in body_lower:
                if 'follow' in body_lower:
                    return "Follow-up regarding medical lien case"
                return "Initial outreach regarding medical lien"
            elif 'thank you' in body_lower and len(body_lower) < 200:
                return "Acknowledged receipt"
            else:
                # Default for our emails
                return "Sent correspondence regarding the case"
        else:
            # Their emails - what did they say?
            if 'settle' in body_lower:
                if 'offer' in body_lower:
                    return "Provided settlement offer information"
                elif 'discuss' in body_lower or 'negotiat' in body_lower:
                    return "Discussing settlement negotiations"
                elif 'reach' in body_lower or 'agreed' in body_lower:
                    return "Settlement reached or in progress"
                else:
                    return "Mentioned settlement status"
            elif 'pending' in body_lower:
                return "Case is pending"
            elif 'litigation' in body_lower or 'lawsuit' in body_lower or 'court' in body_lower:
                if 'filed' in body_lower:
                    return "Litigation has been filed"
                return "Discussed litigation status"
            elif 'dropped' in body_lower or 'dismiss' in body_lower:
                return "Case dropped or dismissed"
            elif 'waiting' in body_lower or 'await' in body_lower:
                if 'client' in body_lower:
                    return "Waiting for client decision"
                elif 'insurance' in body_lower:
                    return "Waiting for insurance response"
                return "Case awaiting further action"
            elif 'forward' in body_lower or 'send' in body_lower:
                if 'document' in body_lower or 'bill' in body_lower:
                    return "Requested documentation or bills"
                return "Requested information"
            elif 'received' in body_lower or 'receipt' in body_lower:
                return "Acknowledged receipt of information"
            elif 'contact' in body_lower or 'email' in body_lower:
                # Check if they're providing alternate contact
                if '@' in body:
                    return "Provided alternate contact information"
                return "Discussed contact preferences"
            else:
                # Try to extract first meaningful sentence
                if body:
                    sentences = body.split('.')
                    for sentence in sentences:
                        if sentence:
                            # Skip greetings and signatures
                            if len(sentence) > 20 and not any(skip in sentence.lower() for skip in ['hello', 'dear', 'regards', 'sincerely', 'thank you']):
                                # Return first 100 chars of meaningful content
                                cleaned = sentence.strip()
                                if cleaned:
                                    return cleaned[:100] if cleaned else "Email content"
                
                # Default for their emails
                return "Responded to inquiry"