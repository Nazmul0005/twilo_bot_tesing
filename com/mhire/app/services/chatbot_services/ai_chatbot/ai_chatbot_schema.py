from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class OrganizationType(str, Enum):
    HRH = "HRH"
    SMB = "SMB"

class ChatRequest(BaseModel):
    message: str
    organization_type: OrganizationType = OrganizationType.SMB
    session_id: Optional[str] = None

class EscalationType(str, Enum):
    NONE = "none"
    HUMAN = "human_escalation"
    APPOINTMENT = "appointment_booking"

class AppointmentState(BaseModel):
    """Tracks appointment booking progress"""
    is_booking: bool = False
    current_question: int = 0
    answers: Dict[str, str] = {}
    
class SessionData(BaseModel):
    """Session data structure"""
    session_id: str
    appointment_state: AppointmentState = AppointmentState()
    conversation_history: List[Dict[str, str]] = []

class ChatResponse(BaseModel):
    response: str
    escalation_type: EscalationType
    human_escalation: bool = False
    appointment_escalation: bool = False
    session_id: Optional[str] = None
    requires_review: bool = False