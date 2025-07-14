import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize configuration values"""
        # OpenAI Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # Twilio Configuration
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        logger.debug(f"Config initialized - Model: {self.model_name}")
        if self.openai_api_key:
            logger.debug(f"OpenAI API key loaded: {self.openai_api_key[:10]}...")
        else:
            logger.error("OpenAI API key not found in environment variables!")
            
        if self.twilio_account_sid:
            logger.debug(f"Twilio Account SID loaded: {self.twilio_account_sid[:10]}...")
        else:
            logger.warning("Twilio Account SID not found in environment variables!")
            
        if self.twilio_phone_number:
            logger.debug(f"Twilio Phone Number loaded: {self.twilio_phone_number}")
        else:
            logger.warning("Twilio Phone Number not found in environment variables!")