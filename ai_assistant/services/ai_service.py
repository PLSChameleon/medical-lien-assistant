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
        Generate a summary of case-related emails
        
        Args:
            case (dict): Case information
            email_messages (list): List of email messages
            
        Returns:
            str: Summary of the email conversation
        """
        try:
            if not email_messages:
                return "❌ No emails found for this case."
            
            conversation = "\n".join([
                f"{m.get('date', 'Unknown date')} - {m.get('from', 'Unknown sender')}:\n{m.get('snippet', 'No snippet')}\n"
                for m in email_messages
            ])
            
            prompt = f"""
            This is an email conversation about a legal case for patient {case['Name']} 
            (PV: {case.get('PV', 'Unknown')}, DOI: {case.get('DOI', 'Unknown')}).
            
            Summarize the back-and-forth between the parties in bullet points. 
            Suggest what Dean Hyland should do next to follow up or close out the case.
            
            Conversation:
            {conversation}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"Generated case summary for {case.get('PV', 'Unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating case summary: {e}")
            return f"❌ Error generating summary: {e}"