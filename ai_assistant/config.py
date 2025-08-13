import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration management"""
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # Application settings
    CASES_FILE_PATH = os.getenv("CASES_FILE_PATH", "data/cases.xlsx")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_EMAIL_RESULTS = int(os.getenv("MAX_EMAIL_RESULTS", "10"))
    
    # Email settings
    DEFAULT_FROM_NAME = os.getenv("DEFAULT_FROM_NAME", "AI Assistant")
    DEFAULT_SIGNATURE = os.getenv("DEFAULT_SIGNATURE", "")
    
    # Gmail API scopes
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify"
    ]
    
    @classmethod
    def validate_required_vars(cls):
        """Validate that required environment variables are set"""
        required_vars = {
            "OPEN_AI_API_KEY": cls.OPENAI_API_KEY,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please check your config.env file or environment variables."
            )
        
        return True
    
    @classmethod
    def get_file_path(cls, filename):
        """Get absolute path for a file relative to project root"""
        project_root = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(project_root, filename)