from openai import OpenAI
import json
import logging
from config import Config

logger = logging.getLogger(__name__)

class AIService:
    """OpenAI API service wrapper"""
    
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found. Please check your environment variables.")
        
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.prompt_templates = self._load_prompt_templates()
        logger.info("AI service initialized successfully")
    
    def _load_prompt_templates(self):
        """Load prompt templates from JSON file"""
        try:
            with open(Config.get_file_path("prompt_template.json"), "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("prompt_template.json not found. Using default templates.")
            return self._get_default_templates()
        except Exception as e:
            logger.error(f"Error loading prompt templates: {e}")
            return self._get_default_templates()
    
    def _get_default_templates(self):
        """Default prompt templates if file is missing"""
        return {
            "followup_prompt": """
            You are drafting a follow-up email for Prohealth Advanced Imaging collections regarding patient {name} (DOI: {doi}).

            Previous Email Thread:
            {thread}

            CRITICAL CONSTRAINTS:
            - ONLY reference information that actually appears in the email thread above
            - DO NOT mention lien reductions, settlements, or other topics unless explicitly mentioned in the thread
            - This is collections follow-up - you're checking on case status (pending/settled/dropped)
            - Common responses from attorneys: "pending", "settled", "dropped", or no response
            - Be professional but direct - you're following up on medical billing/liens

            Draft a professional follow-up email as Dean Hyland from Prohealth Advanced Imaging that:
            1. References the specific last communication from the thread
            2. Politely requests a case status update
            3. Does NOT invent or assume information not in the thread
            4. Stays focused on getting case status for billing purposes

            Keep it concise and professional.
            """,
            "status_request_prompt": """
            Draft a professional initial status request email for Prohealth Advanced Imaging collections.
            
            Patient: {name}
            Date of Injury: {doi} 
            Attorney: {email}
            
            This is your FIRST contact about this case. Draft an email that:
            1. Introduces yourself as Dean Hyland from Prohealth Advanced Imaging
            2. States you're inquiring about the case status for billing/liens purposes
            3. Asks if the case is pending, settled, or dropped
            4. Offers to provide medical reports or records if needed
            5. Requests a response with case status
            
            Be professional, concise, and clear about your purpose (medical billing collections).
            End with just "Thank you" - Gmail will add the signature automatically.
            """
        }
    
    def generate_followup_email(self, case, thread_messages, cadence_guidance=None):
        """
        Generate a follow-up email based on case and thread history
        
        Args:
            case (dict): Case information
            thread_messages (list): List of thread messages
            
        Returns:
            str: Generated email content
        """
        try:
            # Prepare thread preview for GPT
            all_msgs = []
            for thread in thread_messages:
                all_msgs.extend(thread.get("messages", []))
            
            # Sort by internal date
            all_msgs.sort(key=lambda m: int(m.get("internalDate", "0")), reverse=True)
            
            # Create preview of recent messages
            preview = []
            for msg in all_msgs[:5]:
                sender = next(
                    (h['value'] for h in msg.get("payload", {}).get("headers", []) 
                     if h['name'].lower() == "from"), 
                    ""
                )
                snippet = msg.get("snippet", "").strip()
                preview.append(f"{sender}:\n{snippet}\n")
            
            thread_text = "\n---\n".join(preview)
            
            # DEBUG: Log what thread content we're sending to AI
            logger.info(f"Thread content being sent to AI: {thread_text[:500]}")
            
            # Build cadence-aware prompt
            base_prompt = self.prompt_templates["followup_prompt"].format(
                name=case["Name"],
                doi=case["DOI"].strftime('%B %d, %Y') if hasattr(case["DOI"], 'strftime') else str(case["DOI"]),
                thread=thread_text
            )
            
            # DEBUG: Log the full prompt being sent
            logger.info(f"Full prompt being sent to AI: {base_prompt[:800]}")
            
            # Add cadence guidance if available
            if cadence_guidance:
                style_instruction = f"""
                
IMPORTANT: Match this writing style:
- Tone: {cadence_guidance.get('tone', 'professional')}
- Style: {cadence_guidance.get('style', 'formal')} 
- Length: Keep around {cadence_guidance.get('avg_length', 200)} characters
- Use this greeting pattern: {cadence_guidance.get('greeting', 'Dear [Name],')}
- End with: "Thank you" (Gmail will add signature automatically)
                """
                prompt = base_prompt + style_instruction
            else:
                prompt = base_prompt
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"Generated follow-up email for case {case.get('PV', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating follow-up email: {e}")
            return f"❌ Error generating email: {e}"
    
    def generate_status_request_email(self, case):
        """
        Generate a status request email for a case
        
        Args:
            case (dict): Case information
            
        Returns:
            str: Generated email content
        """
        try:
            prompt = self.prompt_templates["status_request_prompt"].format(
                name=case["Name"],
                doi=case["DOI"] if hasattr(case["DOI"], 'strftime') else str(case["DOI"]),
                email=case["Attorney Email"]
            )
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"Generated status request email for case {case.get('PV', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating status request email: {e}")
            return f"❌ Error generating email: {e}"
    
    def summarize_case_emails(self, case, email_messages):
        """
        Generate a summary of case-related emails with dates and reply status
        
        Args:
            case (dict): Case information
            email_messages (list): List of email messages
            
        Returns:
            str: Summary of the email conversation
        """
        try:
            if not email_messages:
                return "❌ No emails found for this case."
            
            # Sort emails by date (oldest first) for chronological order
            from datetime import datetime
            import email.utils
            
            def parse_email_date(date_str):
                if not date_str:
                    return datetime.min
                try:
                    # Parse RFC 2822 date format
                    return datetime(*email.utils.parsedate(date_str)[:6])
                except:
                    return datetime.min
            
            sorted_emails = sorted(email_messages, key=lambda x: parse_email_date(x.get('date')))
            
            # Format conversation with dates
            conversation_parts = []
            for i, msg in enumerate(sorted_emails):
                date_obj = parse_email_date(msg.get('date'))
                date_formatted = date_obj.strftime('%m-%d-%Y') if date_obj != datetime.min else 'Unknown Date'
                
                sender = msg.get('from', 'Unknown sender')
                snippet = msg.get('snippet', 'No snippet')
                
                # Determine if this is from us or from them
                is_from_us = 'dean' in sender.lower() or 'prohealth' in sender.lower()
                direction = "[SENT]" if is_from_us else "[RECEIVED]"
                
                conversation_parts.append(
                    f"({date_formatted}) {direction} {sender}:\n{snippet}\n"
                )
            
            conversation = "\n".join(conversation_parts)
            
            # Analyze reply patterns
            sent_count = sum(1 for msg in sorted_emails if 'dean' in msg.get('from', '').lower() or 'prohealth' in msg.get('from', '').lower())
            received_count = len(sorted_emails) - sent_count
            
            # Get last email info
            last_email = sorted_emails[-1] if sorted_emails else None
            last_was_from_us = False
            if last_email:
                last_from = last_email.get('from', '').lower()
                last_was_from_us = 'dean' in last_from or 'prohealth' in last_from
            
            prompt = f"""
            This is an email conversation about a legal case for patient {case['Name']} 
            (PV: {case.get('PV', 'Unknown')}, DOI: {case.get('DOI', 'Unknown')}).
            
            Email Statistics:
            - Total emails: {len(sorted_emails)}
            - Emails sent by us: {sent_count}
            - Emails received: {received_count}
            - Last email was {'from us (no response yet)' if last_was_from_us else 'from them (they responded)'}
            
            Please provide a detailed summary in this format:
            
            **CORRESPONDENCE SUMMARY:**
            - List each meaningful exchange with dates in MM-DD-YYYY format
            - Format: (MM-DD-YYYY) Person/Firm reached out regarding...
            - Note if there was a reply or no response
            - Highlight any lien reduction requests, settlement discussions, or case status updates
            
            **CURRENT STATUS:**
            - What is the current state of this case based on the emails?
            - Are we waiting for a response or do we need to follow up?
            
            **RECOMMENDED ACTION:**
            - What should Dean Hyland do next?
            
            Conversation:
            {conversation}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"Generated enhanced case summary for {case.get('PV', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating case summary: {e}")
            return f"❌ Error generating summary: {e}"