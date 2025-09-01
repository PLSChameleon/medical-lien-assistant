import os
from dotenv import load_dotenv

# Get the directory where this config.py file is located
config_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(config_dir, 'config.env')

# Check if config.env exists
if not os.path.exists(env_path):
    print(f"ERROR: config.env not found at {env_path}")
    print("Please ensure config.env file is in the ai_assistant directory")
    print("Current working directory:", os.getcwd())
    print("Config directory:", config_dir)
    print("\nLooking for config files...")
    for file in os.listdir(config_dir):
        if file.endswith('.env'):
            print(f"  Found: {file}")
    # Try loading from .env as fallback
    fallback_path = os.path.join(config_dir, '.env')
    if os.path.exists(fallback_path):
        print(f"Loading fallback .env from {fallback_path}")
        load_dotenv(fallback_path)
    else:
        print("No .env fallback found either")
else:
    # Load the config.env file from the same directory as config.py
    load_dotenv(env_path)
    print(f"Successfully loaded config.env from {env_path}")

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