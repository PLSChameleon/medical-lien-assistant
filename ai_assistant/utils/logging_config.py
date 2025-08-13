import logging
import os
from datetime import datetime
from config import Config

def setup_logging():
    """Configure application logging"""
    
    # Create logs directory if it doesn't exist
    logs_dir = Config.get_file_path("logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure logging
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (for user-facing messages)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (for detailed logs)
    log_file = os.path.join(logs_dir, f"assistant_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Suppress overly verbose third-party logs
    logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
    logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    
    logging.info("Logging configured successfully")

def log_sent_email(case_pv, recipient_email, subject, message_id=None):
    """
    Log sent email information
    
    Args:
        case_pv (str): Case PV number
        recipient_email (str): Recipient email address
        subject (str): Email subject
        message_id (str, optional): Gmail message ID
    """
    log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] PV: {case_pv} | To: {recipient_email} | Subject: {subject}"
    
    if message_id:
        log_entry += f" | Gmail ID: {message_id}"
    
    # Log to main log
    logger = logging.getLogger(__name__)
    logger.info(f"Email sent - {log_entry}")
    
    # Also log to separate sent emails file for easy tracking
    sent_log_file = Config.get_file_path("logs/sent_emails.log")
    try:
        with open(sent_log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        logger.error(f"Failed to write to sent emails log: {e}")