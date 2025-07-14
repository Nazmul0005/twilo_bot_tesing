import logging
import hashlib
from typing import Dict, Optional
from com.mhire.app.services.chatbot_services.chatbot_utils.session_utils.session_manager import SessionManager

logger = logging.getLogger(__name__)

class MobileSessionManager:
    """Manages sessions based on mobile numbers for SMS conversations"""
    
    def __init__(self):
        self.mobile_to_session: Dict[str, str] = {}  # mobile_number -> session_id mapping
        self.session_manager = SessionManager()
        logger.debug("MobileSessionManager initialized")
    
    def _normalize_mobile_number(self, mobile_number: str) -> str:
        """Normalize mobile number format"""
        # Remove all non-digit characters except +
        cleaned = ''.join(char for char in mobile_number if char.isdigit() or char == '+')
        
        # Remove + for processing
        digits_only = cleaned.replace('+', '')
        
        # Normalize to E.164 format
        if len(digits_only) == 10:
            # US number without country code
            normalized = '+1' + digits_only
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            # US number with country code
            normalized = '+' + digits_only
        elif cleaned.startswith('+'):
            # Already has country code
            normalized = cleaned
        else:
            # Default to US country code
            normalized = '+1' + digits_only
        
        logger.debug(f"Normalized mobile number: {mobile_number} -> {normalized}")
        return normalized
    
    def _generate_mobile_session_id(self, mobile_number: str) -> str:
        """Generate a consistent session ID for a mobile number"""
        normalized_number = self._normalize_mobile_number(mobile_number)
        
        # Extract digits only for the session ID (remove + and country code formatting)
        digits_only = ''.join(char for char in normalized_number if char.isdigit())
        
        # Create a hash of the mobile number for consistent session ID
        hash_object = hashlib.md5(normalized_number.encode())
        hash_part = hash_object.hexdigest()[:16]
        
        # Format: {phone_digits}_{hash}
        session_id = f"{digits_only}_{hash_part}"
        
        logger.debug(f"Generated mobile session ID: {session_id} for {normalized_number}")
        return session_id
    
    def get_or_create_session_for_mobile(self, mobile_number: str) -> str:
        """Get existing session ID or create new one for mobile number"""
        normalized_number = self._normalize_mobile_number(mobile_number)
        
        if normalized_number in self.mobile_to_session:
            session_id = self.mobile_to_session[normalized_number]
            logger.debug(f"Retrieved existing session {session_id} for {normalized_number}")
        else:
            session_id = self._generate_mobile_session_id(normalized_number)
            self.mobile_to_session[normalized_number] = session_id
            logger.debug(f"Created new session {session_id} for {normalized_number}")
        
        # Ensure session exists in session manager
        self.session_manager.get_session(session_id)
        
        return session_id
    
    def get_session_data(self, mobile_number: str):
        """Get session data for mobile number"""
        session_id = self.get_or_create_session_for_mobile(mobile_number)
        return self.session_manager.get_session(session_id)
    
    def add_message_to_mobile_session(self, mobile_number: str, message_type: str, content: str):
        """Add message to mobile number's session history"""
        session_id = self.get_or_create_session_for_mobile(mobile_number)
        self.session_manager.add_message_to_history(session_id, message_type, content)
        logger.debug(f"Added {message_type} message to mobile session for {mobile_number}")
    
    def get_mobile_conversation_history(self, mobile_number: str) -> list:
        """Get conversation history for mobile number"""
        session_id = self.get_or_create_session_for_mobile(mobile_number)
        return self.session_manager.get_conversation_history(session_id)
    
    def is_mobile_in_appointment_booking(self, mobile_number: str) -> bool:
        """Check if mobile number session is in appointment booking mode"""
        session_id = self.get_or_create_session_for_mobile(mobile_number)
        return self.session_manager.is_in_appointment_booking(session_id)
    
    def clear_mobile_session(self, mobile_number: str) -> bool:
        """Clear session for mobile number"""
        normalized_number = self._normalize_mobile_number(mobile_number)
        
        if normalized_number in self.mobile_to_session:
            session_id = self.mobile_to_session[normalized_number]
            del self.mobile_to_session[normalized_number]
            self.session_manager.clear_session(session_id)
            logger.debug(f"Cleared mobile session for {normalized_number}")
            return True
        return False
    
    def get_mobile_session_id(self, mobile_number: str) -> str:
        """Get the session ID for a mobile number without creating session data"""
        return self.get_or_create_session_for_mobile(mobile_number)