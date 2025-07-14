import logging
import uuid
from typing import Dict, Optional
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot_schema import SessionData, AppointmentState

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages session data in memory"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        logger.debug("SessionManager initialized")
    
    def generate_session_id() -> str:
        """Generate a unique session ID"""
        session_id = str(uuid.uuid4())
        logger.debug(f"Generated session ID: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> SessionData:
        """Get or create session data"""
        if session_id not in self.sessions:
            logger.debug(f"Creating new session: {session_id}")
            self.sessions[session_id] = SessionData(
                session_id=session_id,
                appointment_state=AppointmentState(),
                conversation_history=[]
            )
        else:
            logger.debug(f"Retrieved existing session: {session_id}")
        
        return self.sessions[session_id]
    
    def update_session(self, session_id: str, session_data: SessionData):
        """Update session data"""
        self.sessions[session_id] = session_data
        logger.debug(f"Updated session: {session_id}")
    
    def add_message_to_history(self, session_id: str, message_type: str, content: str):
        """Add message to conversation history"""
        session = self.get_session(session_id)
        session.conversation_history.append({
            "type": message_type,
            "content": content
        })
        
        # Keep only last 20 messages to avoid memory issues
        if len(session.conversation_history) > 20:
            session.conversation_history = session.conversation_history[-20:]
        
        logger.debug(f"Added {message_type} message to session {session_id}")
    
    def get_conversation_history(self, session_id: str) -> list:
        """Get conversation history for a session"""
        session = self.get_session(session_id)
        return session.conversation_history
    
    def clear_session(self, session_id: str) -> bool:
        """Clear session data"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug(f"Cleared session: {session_id}")
            return True
        return False
    
    def is_in_appointment_booking(self, session_id: str) -> bool:
        """Check if session is currently in appointment booking mode"""
        session = self.get_session(session_id)
        return session.appointment_state.is_booking