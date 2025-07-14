import logging
from typing import Dict, List, Optional, Tuple
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot_schema import AppointmentState

logger = logging.getLogger(__name__)

class AppointmentBookingSystem:
    """Handles structured multi-turn appointment booking"""
    
    APPOINTMENT_QUESTIONS = [
        {
            "key": "purpose",
            "question": "What is the appointment for? (e.g., general checkup, consultation, specific concern)",
            "required": True
        },
        {
            "key": "patient",
            "question": "Who is the appointment for? Please specify 'self' or provide the name of the person",
            "required": True
        },
        {
            "key": "date",
            "question": "Which date would you like for your appointment? (e.g., specific date)",
            "required": True
        },
        {
            "key": "time",
            "question": "What time would you prefer? (e.g., specific time)",
            "required": True
        },
        {
            "key": "format",
            "question": "How would you like to attend? Please choose: phone-call, video, or onsite",
            "required": True
        },
        {
            "key": "specialist",
            "question": "Do you have any preferred specialist or doctor? (optional - you can say 'no preference')",
            "required": False
        }
    ]
    
    def __init__(self):
        logger.debug("AppointmentBookingSystem initialized")
    
    def start_booking(self) -> Tuple[str, AppointmentState]:
        """Start the appointment booking process"""
        logger.info("Starting appointment booking process")
        
        state = AppointmentState(
            is_booking=True,
            current_question=0,
            answers={}
        )
        
        first_question = self.APPOINTMENT_QUESTIONS[0]["question"]
        response = f"I'd be happy to help you book an appointment! Let me gather some information.\n\n{first_question}"
        
        logger.debug(f"Started booking with first question: {first_question}")
        return response, state
    
    def process_answer(self, user_message: str, state: AppointmentState) -> Tuple[str, AppointmentState, bool]:
        """
        Process user's answer and return next question or completion
        Returns: (response, updated_state, is_complete)
        """
        logger.info(f"Processing answer for question {state.current_question}: '{user_message[:50]}...'")
        logger.info(f"Current booking state - is_booking: {state.is_booking}, current_question: {state.current_question}")
        logger.info(f"Current answers: {state.answers}")
        
        if not state.is_booking:
            logger.warning("Attempted to process answer when not in booking mode")
            return "I'm not currently in appointment booking mode.", state, False
        
        if state.current_question >= len(self.APPOINTMENT_QUESTIONS):
            logger.warning(f"Current question index {state.current_question} out of range (max: {len(self.APPOINTMENT_QUESTIONS)})")
            return "There seems to be an error with the booking process.", state, False
        
        # Store the current answer
        current_q = self.APPOINTMENT_QUESTIONS[state.current_question]
        state.answers[current_q["key"]] = user_message.strip()
        
        logger.info(f"Stored answer for '{current_q['key']}': '{user_message[:30]}...'")
        logger.info(f"Updated answers: {state.answers}")
        
        # Move to next question
        state.current_question += 1
        logger.info(f"Moved to next question index: {state.current_question}")
        
        # Check if we have more questions
        if state.current_question < len(self.APPOINTMENT_QUESTIONS):
            next_question = self.APPOINTMENT_QUESTIONS[state.current_question]["question"]
            response = f"Thank you! Next question:\n\n{next_question}"
            logger.info(f"Moving to question {state.current_question}: {next_question}")
            return response, state, False
        else:
            # All questions answered - show confirmation
            confirmation = self._generate_confirmation(state.answers)
            state.is_booking = False  # End booking process
            logger.info("Appointment booking completed - setting is_booking to False")
            return confirmation, state, True
    
    def _generate_confirmation(self, answers: Dict[str, str]) -> str:
        """Generate appointment confirmation message"""
        logger.debug("Generating appointment confirmation")
        
        confirmation = "Perfect! Here's a summary of your appointment request:\n\n"
        confirmation += f"📅 **Appointment Details:**\n"
        confirmation += f"• Purpose: {answers.get('purpose', 'Not specified')}\n"
        confirmation += f"• Patient: {answers.get('patient', 'Not specified')}\n"
        confirmation += f"• Date: {answers.get('date', 'Not specified')}\n"
        confirmation += f"• Time: {answers.get('time', 'Not specified')}\n"
        confirmation += f"• Format: {answers.get('format', 'Not specified')}\n"
        
        if answers.get('specialist') and answers['specialist'].lower() not in ['no preference', 'no', 'none']:
            confirmation += f"• Preferred specialist: {answers['specialist']}\n"
        
        confirmation += "\n✅ Your appointment request has been submitted! Our team will contact you shortly to confirm the details.\n\n"
        confirmation += "Is there anything else I can help you with today?"
        
        return confirmation
    
    def cancel_booking(self, state: AppointmentState) -> Tuple[str, AppointmentState]:
        """Cancel the current booking process"""
        logger.info("Cancelling appointment booking")
        
        state.is_booking = False
        state.current_question = 0
        state.answers = {}
        
        response = "I've cancelled the appointment booking process. Is there anything else I can help you with?"
        return response, state
    
    def is_cancel_intent(self, message: str) -> bool:
        """Check if user wants to cancel booking"""
        cancel_keywords = [
            "cancel", "stop", "quit", "exit", "nevermind", "never mind",
            "abort", "back", "return", "no thanks", "not now"
        ]
        
        message_lower = message.lower().strip()
        return any(keyword in message_lower for keyword in cancel_keywords)
    
    def get_current_question(self, state: AppointmentState) -> Optional[str]:
        """Get the current question text"""
        if not state.is_booking or state.current_question >= len(self.APPOINTMENT_QUESTIONS):
            return None
        
        return self.APPOINTMENT_QUESTIONS[state.current_question]["question"]