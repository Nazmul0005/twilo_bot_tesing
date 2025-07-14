import logging
import uuid
from typing import Optional, Dict, List
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from com.mhire.app.config.config import Config
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot_schema import (
    ChatRequest, ChatResponse, EscalationType, OrganizationType
)
from com.mhire.app.services.chatbot_services.chatbot_utils.dictionary_utils.prompt_dictionary import get_system_prompt
from com.mhire.app.services.chatbot_services.chatbot_utils.dictionary_utils.escalation_dictionary import check_escalation_keywords
from com.mhire.app.services.chatbot_services.chatbot_utils.appointment_utils.appointment_booking import AppointmentBookingSystem
from com.mhire.app.services.chatbot_services.chatbot_utils.session_utils.session_manager import SessionManager

logger = logging.getLogger(__name__)

class AIChatbot:
    def __init__(self):
        logger.debug("Initializing AIChatbot...")
        self.config = Config()
        
        logger.debug(f"Creating ChatOpenAI with API key: {self.config.openai_api_key[:10]}...")
        
        try:
            self.llm = ChatOpenAI(
                openai_api_key=self.config.openai_api_key,
                model_name=self.config.model_name,
                temperature=0.7,
                max_tokens=300
            )
            logger.info("ChatOpenAI initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI: {str(e)}")
            raise
        
        # Initialize appointment booking system and session manager
        self.appointment_system = AppointmentBookingSystem()
        self.session_manager = SessionManager()
        logger.info("AIChatbot fully initialized with appointment booking system")

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """Process incoming chat message and return appropriate response"""
        logger.info(f"Processing message: '{request.message[:50]}...'")
        
        # Generate session ID if not provided
        session_id = request.session_id or SessionManager.generate_session_id()
        logger.debug(f"Using session ID: {session_id}")
        
        # Get session data
        session_data = self.session_manager.get_session(session_id)
        
        # Check if we're in appointment booking mode
        if session_data.appointment_state.is_booking:
            logger.debug("Currently in appointment booking mode")
            return await self._handle_appointment_booking(request.message, session_id, session_data)
        
        # Check for escalation keywords
        human_escalation, appointment_escalation = check_escalation_keywords(request.message)
        logger.debug(f"Escalation check - Human: {human_escalation}, Appointment: {appointment_escalation}")
        
        # Handle human escalation (highest priority)
        if human_escalation:
            logger.info("Human escalation triggered")
            response_text = "Please take action immediately. Based on your message, it's important that you seek immediate medical attention or contact emergency services if this is a medical emergency."
            
            # Add AI response to history
            self.session_manager.add_message_to_history(session_id, "ai", response_text)
            
            return ChatResponse(
                response=response_text,
                escalation_type=EscalationType.HUMAN,
                human_escalation=True,
                appointment_escalation=False,
                session_id=session_id,
                requires_review=True
            )
        
        # Handle appointment escalation - start booking process
        if appointment_escalation:
            logger.info("Appointment escalation triggered - starting booking process")
            response_text, updated_state = self.appointment_system.start_booking()
            
            # Update session with new appointment state
            session_data.appointment_state = updated_state
            self.session_manager.update_session(session_id, session_data)
            
            # Add AI response to history
            self.session_manager.add_message_to_history(session_id, "ai", response_text)
            
            return ChatResponse(
                response=response_text,
                escalation_type=EscalationType.APPOINTMENT,
                human_escalation=False,
                appointment_escalation=True,
                session_id=session_id,
                requires_review=False
            )
        
        # Generate AI response for general queries
        try:
            logger.debug("Generating AI response with LangChain...")
            ai_response = await self._generate_ai_response(
                request.message, 
                request.organization_type, 
                session_id
            )
            
            logger.info(f"Successfully generated AI response: '{ai_response[:100]}...'")
            
            # Add user message to history AFTER generating response to avoid duplicates
            self.session_manager.add_message_to_history(session_id, "human", request.message)
            # Add AI response to history
            self.session_manager.add_message_to_history(session_id, "ai", ai_response)
            
            return ChatResponse(
                response=ai_response,
                escalation_type=EscalationType.NONE,
                human_escalation=False,
                appointment_escalation=False,
                session_id=session_id,
                requires_review=False
            )
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}", exc_info=True)
            
            # Return fallback response
            fallback_response = "I'm having trouble processing your request right now. For immediate medical concerns, please contact your healthcare provider or emergency services."
            
            # Add fallback response to history
            self.session_manager.add_message_to_history(session_id, "human", request.message)
            self.session_manager.add_message_to_history(session_id, "ai", fallback_response)
            
            return ChatResponse(
                response=fallback_response,
                escalation_type=EscalationType.HUMAN,
                human_escalation=True,
                appointment_escalation=False,
                session_id=session_id,
                requires_review=True
            )

    async def _handle_appointment_booking(self, user_message: str, session_id: str, session_data) -> ChatResponse:
        """Handle appointment booking conversation flow"""
        logger.debug("Handling appointment booking flow")
        
        # Check if user wants to cancel
        if self.appointment_system.is_cancel_intent(user_message):
            logger.info("User wants to cancel appointment booking")
            response_text, updated_state = self.appointment_system.cancel_booking(session_data.appointment_state)
            
            # Update session
            session_data.appointment_state = updated_state
            self.session_manager.update_session(session_id, session_data)
            
            # Add AI response to history
            self.session_manager.add_message_to_history(session_id, "ai", response_text)
            
            return ChatResponse(
                response=response_text,
                escalation_type=EscalationType.NONE,
                human_escalation=False,
                appointment_escalation=False,
                session_id=session_id,
                requires_review=False
            )
        
        # Process the answer
        response_text, updated_state, is_complete = self.appointment_system.process_answer(
            user_message, session_data.appointment_state
        )
        
        # Update session
        session_data.appointment_state = updated_state
        self.session_manager.update_session(session_id, session_data)
        
        # Add AI response to history
        self.session_manager.add_message_to_history(session_id, "ai", response_text)
        
        # Determine escalation type based on completion
        escalation_type = EscalationType.NONE if is_complete else EscalationType.APPOINTMENT
        
        return ChatResponse(
            response=response_text,
            escalation_type=escalation_type,
            human_escalation=False,
            appointment_escalation=not is_complete,  # Still in appointment mode if not complete
            session_id=session_id,
            requires_review=False
        )

    async def _generate_ai_response(self, message: str, org_type: OrganizationType, session_id: str) -> str:
        """Generate AI response using LangChain ChatOpenAI with conversation history"""
        logger.debug(f"Generating AI response for org type: {org_type}, session: {session_id}")
        
        try:
            # Get conversation history BEFORE adding current message
            history = self.session_manager.get_conversation_history(session_id)
            logger.debug(f"Retrieved {len(history)} messages from history")
            
            # Get system prompt based on organization type
            system_prompt = get_system_prompt(org_type)
            logger.debug(f"Using system prompt for org type: {org_type}")
            
            # Build messages for OpenAI API
            messages = [SystemMessage(content=system_prompt)]
            
            # Add conversation history (limit to last 10 messages to avoid token limits)
            recent_history = history[-10:] if len(history) > 10 else history
            
            for msg in recent_history:
                if msg["type"] == "human":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["type"] == "ai":
                    # Skip adding AI messages to avoid confusion
                    pass
            
            # Add current message (only once!)
            messages.append(HumanMessage(content=message))
            
            logger.debug(f"Sending {len(messages)} messages to LangChain ChatOpenAI")
            logger.debug(f"System prompt: {system_prompt[:100]}...")
            logger.debug(f"User message: {message}")
            
            # Call LangChain ChatOpenAI
            response = await self.llm.ainvoke(messages)
            
            ai_response = response.content.strip()
            logger.debug(f"Received response from LangChain: '{ai_response[:100]}...'")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"LangChain ChatOpenAI error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to generate AI response: {str(e)}")

    def get_session_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        logger.debug(f"Getting history for session: {session_id}")
        return self.session_manager.get_conversation_history(session_id)

    def clear_session_memory(self, session_id: str) -> bool:
        """Clear conversation history for a session"""
        logger.debug(f"Clearing memory for session: {session_id}")
        return self.session_manager.clear_session(session_id)