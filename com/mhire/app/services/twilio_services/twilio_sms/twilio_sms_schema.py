from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class MessageStatus(str, Enum):
    """Twilio message status enum"""
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    UNDELIVERED = "undelivered"
    RECEIVING = "receiving"
    RECEIVED = "received"

class OrganizationType(str, Enum):
    """Organization type for prompt selection"""
    SMB = "SMB"
    HRH = "HRH"

class SMSRequest(BaseModel):
    """Request model for sending SMS"""
    mobile_number: str = Field(..., description="Recipient mobile number with country code (e.g., +1234567890)")
    message: str = Field(..., description="Message content to send")
    organization_type: OrganizationType = Field(default=OrganizationType.SMB, description="Organization type for prompt selection")

class SMSResponse(BaseModel):
    """Response model for SMS sending"""
    success: bool = Field(..., description="Whether the SMS was sent successfully")
    message: str = Field(..., description="Status message")
    mobile_session_id: str = Field(..., description="Session ID based on mobile number")
    twilio_message_sid: Optional[str] = Field(None, description="Twilio message SID")
    twilio_status: Optional[MessageStatus] = Field(None, description="Twilio message status")
    
    # Chatbot response fields (matching existing chatbot response structure)
    chatbot_response: Optional[str] = Field(None, description="AI generated response")
    escalation_type: Optional[str] = Field(None, description="Type of escalation if any")
    escalation_message: Optional[str] = Field(None, description="Escalation message if applicable")
    appointment_booking: Optional[bool] = Field(None, description="Whether appointment booking was triggered")
    appointment_details: Optional[Dict[str, Any]] = Field(None, description="Appointment details if booking")
    session_data: Optional[Dict[str, Any]] = Field(None, description="Session data for context")

class WebhookLogEntry(BaseModel):
    """Model for webhook log entries"""
    timestamp: str = Field(..., description="Timestamp of the webhook call")
    message_sid: str = Field(..., description="Twilio message SID")
    status: MessageStatus = Field(..., description="Message status")
    from_number: str = Field(..., description="Sender phone number")
    to_number: str = Field(..., description="Recipient phone number")
    error_code: Optional[str] = Field(None, description="Error code if any")
    error_message: Optional[str] = Field(None, description="Error message if any")

class WebhookLogResponse(BaseModel):
    """Response model for webhook logs"""
    total_logs: int = Field(..., description="Total number of log entries")
    logs: List[WebhookLogEntry] = Field(..., description="List of webhook log entries")