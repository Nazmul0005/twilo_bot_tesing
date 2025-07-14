import logging
from typing import Optional, Tuple, Dict, Any
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from fastapi import HTTPException
from com.mhire.app.config.config import Config
from com.mhire.app.common.network_responses import HTTPCode
from com.mhire.app.services.twilio_services.twilio_sms.twilio_sms_schema import MessageStatus, OrganizationType
from com.mhire.app.services.twilio_services.sms_utils.mobile_session.mobile_session_manager import MobileSessionManager
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot import AIChatbot
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot_schema import ChatRequest, OrganizationType as ChatbotOrganizationType, EscalationType

logger = logging.getLogger(__name__)

class TwilioSMSService:
    """Service for handling Twilio SMS operations"""
    
    def __init__(self):
        self.config = Config()
        self.mobile_session_manager = MobileSessionManager()
        self.ai_chatbot = AIChatbot()
        
        # Initialize Twilio client
        if self.config.twilio_account_sid and self.config.twilio_auth_token:
            self.twilio_client = Client(
                self.config.twilio_account_sid, 
                self.config.twilio_auth_token
            )
            logger.debug("Twilio client initialized successfully")
        else:
            self.twilio_client = None
            logger.warning("Twilio client not initialized - missing credentials")
    
    def _validate_twilio_config(self) -> bool:
        """Validate Twilio configuration"""
        if not self.config.twilio_account_sid:
            logger.error("TWILIO_ACCOUNT_SID not configured")
            return False
        if not self.config.twilio_auth_token:
            logger.error("TWILIO_AUTH_TOKEN not configured")
            return False
        if not self.config.twilio_phone_number:
            logger.error("TWILIO_PHONE_NUMBER not configured")
            return False
        return True
    
    def _get_organization_prompt_type(self, org_type: OrganizationType) -> ChatbotOrganizationType:
        """Convert organization type to prompt type for chatbot"""
        if org_type == OrganizationType.SMB:
            return ChatbotOrganizationType.SMB
        elif org_type == OrganizationType.HRH:
            return ChatbotOrganizationType.HRH
        else:
            return ChatbotOrganizationType.SMB  # default
    
    async def process_message_with_chatbot(
        self, 
        mobile_number: str, 
        message: str, 
        organization_type: OrganizationType
    ) -> Tuple[Dict[str, Any], str]:
        """Process message through chatbot and return response with session ID"""
        
        # Get or create session for mobile number
        mobile_session_id = self.mobile_session_manager.get_or_create_session_for_mobile(mobile_number)
        
        # Add user message to session history
        self.mobile_session_manager.add_message_to_mobile_session(
            mobile_number, "user", message
        )
        
        # Get organization prompt type
        prompt_type = self._get_organization_prompt_type(organization_type)
        
        # Create chat request
        chat_request = ChatRequest(
            message=message,
            session_id=mobile_session_id,
            organization_type=prompt_type
        )
        
        try:
            # Process through chatbot
            chat_response = await self.ai_chatbot.process_message(chat_request)
            
            # Add bot response to session history
            self.mobile_session_manager.add_message_to_mobile_session(
                mobile_number, "assistant", chat_response.response
            )
            
            # Prepare response data
            response_data = {
                "chatbot_response": chat_response.response,
                "escalation_type": chat_response.escalation_type.value,
                "escalation_message": None,  # ChatResponse doesn't have this field
                "appointment_booking": chat_response.appointment_escalation,
                "appointment_details": None,  # ChatResponse doesn't have this field
                "session_data": {
                    "session_id": mobile_session_id,
                    "conversation_history": self.mobile_session_manager.get_mobile_conversation_history(mobile_number),
                    "in_appointment_booking": self.mobile_session_manager.is_mobile_in_appointment_booking(mobile_number)
                }
            }
            
            logger.debug(f"Chatbot processed message for {mobile_number}, session: {mobile_session_id}")
            return response_data, mobile_session_id
            
        except Exception as e:
            logger.error(f"Error processing message through chatbot: {str(e)}")
            # Return error response - technical errors should escalate to human
            error_response = {
                "chatbot_response": "I apologize, but I'm experiencing technical difficulties. Please try again later.",
                "escalation_type": EscalationType.HUMAN.value,  # Use proper enum value
                "escalation_message": "System error occurred during message processing",
                "appointment_booking": False,
                "appointment_details": None,
                "session_data": {
                    "session_id": mobile_session_id,
                    "conversation_history": self.mobile_session_manager.get_mobile_conversation_history(mobile_number),
                    "in_appointment_booking": False
                }
            }
            return error_response, mobile_session_id
    
    async def send_sms(
        self, 
        mobile_number: str, 
        message: str, 
        organization_type: OrganizationType = OrganizationType.SMB
    ) -> Dict[str, Any]:
        """Send SMS message through Twilio after processing with chatbot"""
        
        # Validate configuration
        if not self._validate_twilio_config():
            raise HTTPException(
                status_code=HTTPCode.SERVICE_UNAVAILABLE,
                detail="Twilio configuration is incomplete"
            )
        
        if not self.twilio_client:
            raise HTTPException(
                status_code=HTTPCode.SERVICE_UNAVAILABLE,
                detail="Twilio client not available"
            )
        
        try:
            # Process message through chatbot first
            chatbot_data, mobile_session_id = await self.process_message_with_chatbot(
                mobile_number, message, organization_type
            )
            
            # Use chatbot response as the message to send
            sms_message = chatbot_data["chatbot_response"]
            
            # Send SMS through Twilio
            twilio_message = self.twilio_client.messages.create(
                body=sms_message,
                from_=self.config.twilio_phone_number,
                to=mobile_number
            )
            
            logger.info(f"SMS sent successfully to {mobile_number}, SID: {twilio_message.sid}")
            
            # Prepare successful response
            response = {
                "mobile_session_id": mobile_session_id,
                "twilio_message_sid": twilio_message.sid,
                "twilio_status": MessageStatus(twilio_message.status),
                **chatbot_data  # Include all chatbot response data
            }
            
            return response
            
        except TwilioException as e:
            logger.error(f"Twilio error sending SMS to {mobile_number}: {str(e)}")
            raise HTTPException(
                status_code=HTTPCode.BAD_REQUEST,
                detail=f"Failed to send SMS: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error sending SMS to {mobile_number}: {str(e)}")
            raise HTTPException(
                status_code=HTTPCode.INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )
    
    def get_message_status(self, message_sid: str) -> Optional[MessageStatus]:
        """Get status of a Twilio message"""
        if not self.twilio_client:
            return None
            
        try:
            message = self.twilio_client.messages(message_sid).fetch()
            return MessageStatus(message.status)
        except TwilioException as e:
            logger.error(f"Error fetching message status for {message_sid}: {str(e)}")
            return None