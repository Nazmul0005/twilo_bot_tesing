import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Example: Access environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
RECIPIENT_PHONE_NUMBER = os.getenv("RECIPIENT_PHONE_NUMBER")
OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")


# Add more variables as needed