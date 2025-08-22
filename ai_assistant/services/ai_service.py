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
            You are a medical collections specialist at Prohealth Advanced Imaging following up on patient {name} (DOI: {doi}).

            Previous Email Thread:
            {thread}

            CRITICAL RULES:
            1. ALWAYS start with "Hello again," - NEVER use attorney names or "Dear [Name]"
            2. DO NOT mention lien reductions, settlements, or payment amounts unless explicitly discussed in the thread
            3. DO NOT offer to negotiate or reduce amounts
            4. DO NOT mention statute of limitations unless specifically relevant
            5. ONLY reference what actually appears in the email thread
            6. Keep it SHORT - 2-3 sentences maximum
            7. End with ONLY "Thank you" - NO name, NO "Dean Hyland", NO "Prohealth Advanced Imaging" (signature is automatic)

            Write a brief follow-up email that:
            - Acknowledges you haven't heard back (if true) OR references their last response
            - Simply asks for a case status update
            - Shows this is about Prohealth Advanced Imaging billing/liens
            
            Examples of good follow-ups:
            "Hello again,

            I am following up on my previous emails requesting the status of this file. Please get back to me when you can."
            
            OR if they haven't responded:
            "Hello again,

            I hope this email finds you well. Just following up on our previous emails as we haven't heard back yet. Could you kindly provide an update on the current status of the Prohealth Advanced Imaging bills?"

            End with just "Thank you" or "Thank you for your attention to this matter" - NO name, NO signature (Gmail adds complete signature automatically).
            """,
            "status_request_prompt": """
            You are a medical collections specialist at Prohealth Advanced Imaging requesting status on a personal injury case.
            
            Patient: {name}
            Date of Injury: {doi}
            
            CRITICAL RULES:
            1. ALWAYS start with "Hello Attorney," - NEVER use law firm names or attorney names
            2. Keep it SHORT and professional - 2-3 sentences maximum
            3. DO NOT mention specific dollar amounts
            4. DO NOT offer settlements or reductions
            5. Simply request case status
            6. End with ONLY "Thank you" or "Thank you for your attention to this matter" - NO name, NO signature
            
            Write a brief initial status request that:
            - States you're from Prohealth Advanced Imaging
            - References the patient name and DOI
            - Asks for current case status (pending/settled/dropped)
            - Mentions this is regarding medical liens/billing
            
            Example format:
            "Hello Attorney,

            I am writing to request a status update on the medical lien case for patient [NAME], who was injured on [DATE]. Please let me know the current status of this case.

            Thank you for your attention to this matter."
            
            OR:
            "Hello Attorney,

            I am reaching out from Prohealth Advanced Imaging regarding our bills for [NAME] (DOI: [DATE]). Could you please provide a status update on this case?

            Thank you."

            End with just "Thank you" or "Thank you for your attention to this matter" - NO name, NO signature (Gmail adds complete signature automatically).
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
            
            # Sort by internal date (oldest first for chronological order)
            all_msgs.sort(key=lambda m: int(m.get("internalDate", "0")))
            
            # Analyze email history
            from datetime import datetime
            our_emails_sent = 0
            their_responses = 0
            last_our_email_date = None
            last_their_response_date = None
            no_response_count = 0
            
            # Create detailed preview with analysis
            preview = []
            for msg in all_msgs:
                sender = next(
                    (h['value'] for h in msg.get("payload", {}).get("headers", []) 
                     if h['name'].lower() == "from"), 
                    ""
                )
                
                # Parse date from internal timestamp (milliseconds since epoch)
                try:
                    msg_timestamp = int(msg.get("internalDate", "0")) / 1000
                    msg_date = datetime.fromtimestamp(msg_timestamp)
                    date_str = msg_date.strftime("%m/%d/%Y")
                except:
                    date_str = "Unknown date"
                    msg_date = None
                
                snippet = msg.get("snippet", "").strip()
                
                # Determine if from us or them
                is_from_us = 'dean' in sender.lower() or 'prohealth' in sender.lower() or 'transcon' in sender.lower()
                
                if is_from_us:
                    our_emails_sent += 1
                    if msg_date:
                        last_our_email_date = msg_date
                    preview.append(f"[{date_str}] WE SENT:\n{snippet[:200]}\n")
                else:
                    their_responses += 1
                    if msg_date:
                        last_their_response_date = msg_date
                    preview.append(f"[{date_str}] ATTORNEY REPLIED:\n{snippet[:200]}\n")
            
            # Calculate no-response situation
            if our_emails_sent > 0 and their_responses == 0:
                no_response_count = our_emails_sent
            elif last_our_email_date and last_their_response_date:
                if last_our_email_date > last_their_response_date:
                    # We sent emails after their last response
                    no_response_count = sum(1 for msg in all_msgs 
                                           if int(msg.get("internalDate", "0"))/1000 > last_their_response_date.timestamp())
            
            # Take only recent messages for context (last 5)
            thread_text = "\n---\n".join(preview[-5:]) if preview else "No previous emails found"
            
            # DEBUG: Log what thread content we're sending to AI
            logger.info(f"Thread content being sent to AI: {thread_text[:500]}")
            
            # Build enhanced prompt with email history analysis
            enhanced_prompt = f"""
            You are a medical collections specialist at Prohealth Advanced Imaging following up on patient {case["Name"]} (DOI: {case["DOI"].strftime('%B %d, %Y') if hasattr(case["DOI"], 'strftime') else str(case["DOI"])}).

            EMAIL HISTORY:
            - Emails sent: {our_emails_sent}
            - Responses received: {their_responses}
            {f"- Unanswered emails: {no_response_count}" if no_response_count > 0 else ""}
            
            Previous Thread:
            {thread_text}

            CRITICAL RULES:
            1. MUST start with "Hello again," or "Hello," - NEVER use names
            2. DO NOT mention lien reductions, settlements, or payment amounts unless explicitly in the thread
            3. DO NOT offer to negotiate or reduce amounts
            4. ONLY reference what's actually in the email thread
            5. Keep it SHORT - maximum 2-3 sentences
            6. Ask about case STATUS, not "bills" - use phrases like "status of the case" or "case status"
            7. Use "in regards to" or "as it relates to" Prohealth Advanced Imaging billing and liens
            8. NO SIGNATURE - end with just "Thank you" or "Thank you for your time"

            Write a brief follow-up that:
            {"- Acknowledges we haven't heard back" if no_response_count > 0 else "- References their last response"}
            {"- Notes this is another follow-up to previous emails" if no_response_count > 1 else ""}
            - Asks about the status of the case as it relates to Prohealth Advanced Imaging billing and liens
            - Mentions "in regards to" or "as it relates to" Prohealth Advanced Imaging
            
            Good examples based on situation:
            
            {'''No response yet:
            "Hello again,
            
            I am following up on my previous emails requesting the status of this file. Please get back to me when you can."''' if no_response_count == 1 else ''''''}
            
            {'''Multiple no responses:
            "Hello again,
            
            In regards to Prohealth Advanced Imaging billing and liens, I am following up on my previous emails requesting the status of the case at this time. Please get back to me when you have a moment."''' if no_response_count > 1 else ''''''}
            
            {'''They responded before:
            "Hello again,
            
            I wanted to follow up on our last exchange. Could you please provide an updated status on this case?"''' if their_responses > 0 and no_response_count == 0 else ''''''}

            End with ONLY "Thank you" or "Thank you for your time" - NO name, NO signature, NO "Sincerely" or "Best regards" (Gmail adds complete signature automatically).
            """
            
            base_prompt = enhanced_prompt
            
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