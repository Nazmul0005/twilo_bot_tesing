import time
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from com.mhire.app.common.network_responses import NetworkResponse, HTTPCode
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot_schema import ChatRequest, ChatResponse
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot import AIChatbot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["AI Chatbot"])
network_response = NetworkResponse()

# Initialize chatbot instance
logger.debug("Initializing chatbot instance...")
chatbot_instance = AIChatbot()
logger.info("Chatbot instance initialized successfully")

@router.post("/chat", response_model=dict)
async def chat_endpoint(http_request: Request, request: ChatRequest):
    """
    Main chat endpoint for AI chatbot
    
    Request body:
    - message: str (required)
    - organization_type: str (optional, defaults to SMB)
    - session_id: str (optional, generates new one if not provided)
    """
    start_time = time.time()
    
    logger.info(f"=== CHAT REQUEST START ===")
    logger.info(f"Message: '{request.message}'")
    logger.info(f"Organization Type: {request.organization_type}")
    logger.info(f"Session ID: {request.session_id}")
    
    try:
        # Enhanced validation
        if not request.message or not request.message.strip():
            logger.warning("Empty message received")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Message cannot be empty",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        # Check message length
        if len(request.message) > 4000:  # Reasonable limit for chat messages
            logger.warning(f"Message too long: {len(request.message)} characters")
            return network_response.json_response(
                http_code=HTTPCode.PAYLOAD_TOO_LARGE,
                error_message="Message is too long. Maximum 4000 characters allowed.",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        # Validate organization type
        if not request.organization_type:
            logger.warning("Missing organization type")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Organization type is required",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        logger.debug("Processing message with chatbot instance...")
        
        # Process the message
        response: ChatResponse = await chatbot_instance.process_message(request)
        
        logger.info(f"Generated response for session {response.session_id}")
        logger.info(f"Escalation Type: {response.escalation_type}")
        logger.info(f"Response: '{response.response[:100]}...'")
        
        # Convert response to dict for API response (removed tags and appointment_questions)
        response_data = {
            "response": response.response,
            "escalation_type": response.escalation_type,
            "human_escalation": response.human_escalation,
            "appointment_escalation": response.appointment_escalation,
            "session_id": response.session_id,
            "requires_review": response.requires_review
        }
        
        logger.debug("Returning successful response")
        logger.info(f"=== CHAT REQUEST END ===")
        
        return network_response.success_response(
            http_code=HTTPCode.SUCCESS,
            message="Chat response generated successfully",
            data=response_data,
            resource=http_request.url.path,
            start_time=start_time
        )
        
    # RequestValidationError is now handled globally in main.py
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        logger.info(f"=== CHAT REQUEST END (HTTP ERROR) ===")
        
        return network_response.json_response(
            http_code=he.status_code,
            error_message=he.detail,
            resource=http_request.url.path,
            start_time=start_time
        )
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        logger.info(f"=== CHAT REQUEST END (VALIDATION ERROR) ===")
        return network_response.json_response(
            http_code=HTTPCode.UNPROCESSABLE_ENTITY,
            error_message=f"Validation error: {str(ve)}",
            resource=http_request.url.path,
            start_time=start_time
        )
    
    except ConnectionError as ce:
        logger.error(f"Connection error (likely OpenAI API): {str(ce)}")
        logger.info(f"=== CHAT REQUEST END (CONNECTION ERROR) ===")
        return network_response.json_response(
            http_code=HTTPCode.SERVICE_UNAVAILABLE,
            error_message="AI service is temporarily unavailable. Please try again later.",
            resource=http_request.url.path,
            start_time=start_time
        )
    
    except TimeoutError as te:
        logger.error(f"Timeout error: {str(te)}")
        logger.info(f"=== CHAT REQUEST END (TIMEOUT ERROR) ===")
        return network_response.json_response(
            http_code=HTTPCode.GATEWAY_TIMEOUT,
            error_message="Request timed out. Please try again with a shorter message.",
            resource=http_request.url.path,
            start_time=start_time
        )
    
    except MemoryError as me:
        logger.error(f"Memory error: {str(me)}")
        logger.info(f"=== CHAT REQUEST END (MEMORY ERROR) ===")
        return network_response.json_response(
            http_code=HTTPCode.INTERNAL_SERVER_ERROR,
            error_message="Server is experiencing high load. Please try again later.",
            resource=http_request.url.path,
            start_time=start_time
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        logger.info(f"=== CHAT REQUEST END (SYSTEM ERROR) ===")
        return network_response.json_response(
            http_code=HTTPCode.INTERNAL_SERVER_ERROR,
            error_message="An unexpected error occurred. Please try again later.",
            resource=http_request.url.path,
            start_time=start_time
        )