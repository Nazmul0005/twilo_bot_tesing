import time
import logging
from fastapi import APIRouter, HTTPException, Request, Query, Form
from fastapi.exceptions import RequestValidationError
from typing import Optional, List, Union
from com.mhire.app.common.network_responses import NetworkResponse, HTTPCode
from com.mhire.app.services.twilio_services.twilio_sms.twilio_sms_schema import (
    SMSRequest, SMSResponse, WebhookLogResponse, MessageStatus, OrganizationType
)
from com.mhire.app.services.twilio_services.twilio_sms.twilio_sms import TwilioSMSService
from com.mhire.app.services.twilio_services.sms_utils.webhook_log.webhook_log_manager import WebhookLogManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Twilio SMS"])
network_response = NetworkResponse()

# Initialize services
twilio_sms_service = TwilioSMSService()
webhook_log_manager = WebhookLogManager()

async def _detect_request_type(http_request: Request) -> str:
    """Detect if request is from Twilio webhook or manual API call"""
    content_type = http_request.headers.get("content-type", "").lower()
    user_agent = http_request.headers.get("user-agent", "").lower()
    
    # Twilio sends form data, manual API sends JSON
    if "application/x-www-form-urlencoded" in content_type:
        logger.debug("Detected Twilio webhook request (form data)")
        return "twilio_webhook"
    elif "application/json" in content_type:
        logger.debug("Detected manual API request (JSON)")
        return "manual_api"
    else:
        logger.debug(f"Unknown content type: {content_type}, defaulting to manual API")
        return "manual_api"

async def _parse_twilio_webhook(http_request: Request) -> SMSRequest:
    """Parse Twilio webhook form data into SMSRequest format"""
    try:
        # Get form data from Twilio webhook
        form_data = await http_request.form()
        
        # Extract Twilio webhook fields
        from_number = form_data.get("From", "")  # User's phone number
        message_body = form_data.get("Body", "")  # User's message
        to_number = form_data.get("To", "")  # Your Twilio number
        
        logger.debug(f"Twilio webhook data - From: {from_number}, To: {to_number}, Body: '{message_body}'")
        
        # Create SMSRequest object with default organization type
        sms_request = SMSRequest(
            mobile_number=from_number,  # User's number becomes the mobile_number
            message=message_body,       # User's message
            organization_type=OrganizationType.SMB  # Default to SMB
        )
        
        logger.info(f"Parsed Twilio webhook into SMSRequest: {from_number} -> '{message_body}'")
        return sms_request
        
    except Exception as e:
        logger.error(f"Error parsing Twilio webhook: {str(e)}")
        raise HTTPException(
            status_code=HTTPCode.BAD_REQUEST,
            detail=f"Invalid Twilio webhook format: {str(e)}"
        )

@router.post("/chat/send", response_model=dict)
async def send_sms_message(
    http_request: Request, 
    request: Optional[SMSRequest] = None,
    # # Twilio webhook form parameters
    # From: Optional[str] = Form(None),
    # Body: Optional[str] = Form(None),
    # To: Optional[str] = Form(None)
):
    """
    Unified endpoint for both manual API calls and Twilio webhook calls
    - Manual API: Send JSON with {mobile_number, message, organization_type}
    - Twilio Webhook: Receives form data from incoming SMS
    """
    start_time = time.time()
    
    try:
        # Detect request type
        request_type = await _detect_request_type(http_request)
        logger.info(f"=== SMS REQUEST START ({request_type.upper()}) ===")
        
        # Parse request based on type
        if request_type == "twilio_webhook":
            # Parse Twilio webhook form data
            parsed_request = await _parse_twilio_webhook(http_request)
            logger.info(f"Twilio Webhook - From: {parsed_request.mobile_number}, Message: '{parsed_request.message}'")
        else:
            # Use provided JSON request for manual API
            if not request:
                logger.warning("Manual API call missing JSON request body")
                return network_response.json_response(
                    http_code=HTTPCode.BAD_REQUEST,
                    error_message="JSON request body required for manual API calls",
                    resource=http_request.url.path,
                    start_time=start_time
                )
            parsed_request = request
            logger.info(f"Manual API - Mobile: {parsed_request.mobile_number}, Message: '{parsed_request.message}', Org: {parsed_request.organization_type}")
        
        # Enhanced validation
        if not parsed_request.mobile_number or not parsed_request.mobile_number.strip():
            logger.warning("Empty mobile number received")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Mobile number is required",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        # Validate mobile number format (basic check)
        mobile_clean = ''.join(char for char in parsed_request.mobile_number if char.isdigit() or char == '+')
        if len(mobile_clean) < 10 or len(mobile_clean) > 15:
            logger.warning(f"Invalid mobile number format: {parsed_request.mobile_number}")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Invalid mobile number format. Please provide a valid phone number.",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        if not parsed_request.message or not parsed_request.message.strip():
            logger.warning("Empty message received")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Message content is required",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        # Check message length for SMS limits
        if len(parsed_request.message) > 1600:  # SMS limit
            logger.warning(f"Message too long for SMS: {len(parsed_request.message)} characters")
            return network_response.json_response(
                http_code=HTTPCode.PAYLOAD_TOO_LARGE,
                error_message="Message is too long for SMS. Maximum 1600 characters allowed.",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        # Validate organization type
        if not parsed_request.organization_type:
            logger.warning("Missing organization type")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Organization type is required",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        logger.debug("Processing SMS request through service...")
        
        # Process through chatbot and send SMS
        if request_type == "twilio_webhook":
            # For Twilio webhook, process incoming message and send response
            result = await twilio_sms_service.send_sms(
                mobile_number=parsed_request.mobile_number,
                message=parsed_request.message,
                organization_type=parsed_request.organization_type
            )
        else:
            # For manual API, same processing
            result = await twilio_sms_service.send_sms(
                mobile_number=parsed_request.mobile_number,
                message=parsed_request.message,
                organization_type=parsed_request.organization_type
            )
        
        logger.info(f"SMS processing completed for {parsed_request.mobile_number}")
        logger.info(f"Mobile Session ID: {result['mobile_session_id']}")
        logger.info(f"Twilio Message SID: {result['twilio_message_sid']}")
        logger.info(f"Chatbot Response: '{result['chatbot_response'][:100] if result['chatbot_response'] else 'None'}...'")
        
        # Log webhook entry for tracking - SUCCESS only (errors are handled by HTTPException)
        webhook_log_manager.add_webhook_log(
            message_sid=result["twilio_message_sid"],
            status=result["twilio_status"],
            from_number=twilio_sms_service.config.twilio_phone_number or "Unknown",
            to_number=parsed_request.mobile_number,
            error_code=None,
            error_message=None
        )
        
        # Create response data - clean structure
        response_data = {
            "mobile_session_id": result["mobile_session_id"],
            "twilio_message_sid": result["twilio_message_sid"],
            "twilio_status": result["twilio_status"].value if result["twilio_status"] else None,
            "chatbot_response": result["chatbot_response"],
            "escalation_type": result["escalation_type"],
            "escalation_message": result["escalation_message"],
            "appointment_booking": result["appointment_booking"],
            "appointment_details": result["appointment_details"]
        }
        
        logger.info(f"SMS sent successfully to {parsed_request.mobile_number}")
        logger.info(f"=== SMS REQUEST END ({request_type.upper()}) ===")
        
        # For Twilio webhook, return simple response (Twilio doesn't need complex JSON)
        if request_type == "twilio_webhook":
            return {"status": "success", "message": "SMS processed successfully"}
        else:
            # For manual API, return full response
            return network_response.success_response(
                http_code=HTTPCode.SUCCESS,
                message="SMS sent successfully",
                data=response_data,
                resource=http_request.url.path,
                start_time=start_time
            )
            
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        logger.info(f"=== SMS REQUEST END (HTTP ERROR) ===")
        
        # Log validation errors to webhook logs
        webhook_log_manager.add_webhook_log(
            message_sid=f"HTTP_ERROR_{int(time.time())}",
            status=MessageStatus.FAILED,
            from_number="System",
            to_number=parsed_request.mobile_number if 'parsed_request' in locals() and hasattr(parsed_request, 'mobile_number') else "Unknown",
            error_code="HTTP_ERROR",
            error_message=he.detail
        )
        
        return network_response.json_response(
            http_code=he.status_code,
            error_message=he.detail,
            resource=http_request.url.path,
            start_time=start_time
        )
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        logger.info(f"=== SMS REQUEST END (VALIDATION ERROR) ===")
        
        # Log validation errors to webhook logs
        webhook_log_manager.add_webhook_log(
            message_sid=f"VALUE_ERROR_{int(time.time())}",
            status=MessageStatus.FAILED,
            from_number="System",
            to_number=parsed_request.mobile_number if 'parsed_request' in locals() and hasattr(parsed_request, 'mobile_number') else "Unknown",
            error_code="VALUE_ERROR",
            error_message=str(ve)
        )
        
        return network_response.json_response(
            http_code=HTTPCode.UNPROCESSABLE_ENTITY,
            error_message=f"Validation error: {str(ve)}",
            resource=http_request.url.path,
            start_time=start_time
        )
    
    except ConnectionError as ce:
        logger.error(f"Connection error (Twilio API): {str(ce)}")
        logger.info(f"=== SMS REQUEST END (CONNECTION ERROR) ===")
        
        webhook_log_manager.add_webhook_log(
            message_sid=f"CONNECTION_ERROR_{int(time.time())}",
            status=MessageStatus.FAILED,
            from_number="System",
            to_number=parsed_request.mobile_number if 'parsed_request' in locals() and hasattr(parsed_request, 'mobile_number') else "Unknown",
            error_code="CONNECTION_ERROR",
            error_message="Failed to connect to SMS service"
        )
        
        return network_response.json_response(
            http_code=HTTPCode.SERVICE_UNAVAILABLE,
            error_message="SMS service is temporarily unavailable. Please try again later.",
            resource=http_request.url.path,
            start_time=start_time
        )
    
    except TimeoutError as te:
        logger.error(f"Timeout error: {str(te)}")
        logger.info(f"=== SMS REQUEST END (TIMEOUT ERROR) ===")
        
        webhook_log_manager.add_webhook_log(
            message_sid=f"TIMEOUT_ERROR_{int(time.time())}",
            status=MessageStatus.FAILED,
            from_number="System",
            to_number=parsed_request.mobile_number if 'parsed_request' in locals() and hasattr(parsed_request, 'mobile_number') else "Unknown",
            error_code="TIMEOUT_ERROR",
            error_message="Request timed out"
        )
        
        return network_response.json_response(
            http_code=HTTPCode.GATEWAY_TIMEOUT,
            error_message="Request timed out. Please try again later.",
            resource=http_request.url.path,
            start_time=start_time
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in send_sms_message: {str(e)}", exc_info=True)
        logger.info(f"=== SMS REQUEST END (SYSTEM ERROR) ===")
        
        # Log system errors to webhook logs
        webhook_log_manager.add_webhook_log(
            message_sid=f"SYSTEM_ERROR_{int(time.time())}",
            status=MessageStatus.FAILED,
            from_number="System",
            to_number=parsed_request.mobile_number if 'parsed_request' in locals() and hasattr(parsed_request, 'mobile_number') else "Unknown",
            error_code="SYSTEM_ERROR",
            error_message=str(e)
        )
        
        return network_response.json_response(
            http_code=HTTPCode.INTERNAL_SERVER_ERROR,
            error_message="An unexpected error occurred. Please try again later.",
            resource=http_request.url.path,
            start_time=start_time
        )

@router.get("/webhooks/visit-logged", response_model=dict)
async def get_webhook_logs(
    http_request: Request,
    limit: Optional[int] = Query(50, description="Number of recent logs to retrieve", ge=1, le=1000)
):
    """
    Get webhook logs for SMS message tracking
    This endpoint retrieves the most recent webhook logs with a limit.
    """
    start_time = time.time()
    
    logger.info(f"=== WEBHOOK LOGS REQUEST START ===")
    logger.info(f"Limit: {limit}")
    
    try:
        # Validate limit parameter
        if limit <= 0:
            logger.warning(f"Invalid limit value: {limit}")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Limit must be a positive integer",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        if limit > 1000:
            logger.warning(f"Limit too high: {limit}")
            return network_response.json_response(
                http_code=HTTPCode.BAD_REQUEST,
                error_message="Limit cannot exceed 1000",
                resource=http_request.url.path,
                start_time=start_time
            )
        
        logger.debug("Retrieving webhook logs...")
        
        # Get recent logs with limit
        logs = webhook_log_manager.get_recent_logs(limit)
        
        # Convert logs to dict format
        logs_data = []
        for log in logs:
            try:
                logs_data.append({
                    "timestamp": log.timestamp,
                    "message_sid": log.message_sid,
                    "status": log.status.value,
                    "from_number": log.from_number,
                    "to_number": log.to_number,
                    "error_code": log.error_code,
                    "error_message": log.error_message
                })
            except Exception as log_error:
                logger.warning(f"Error processing log entry: {log_error}")
                # Skip corrupted log entries
                continue
        
        response_data = {
            "total_logs": webhook_log_manager.get_log_count(),
            "logs": logs_data
        }
        
        logger.info(f"Retrieved {len(logs_data)} webhook logs")
        logger.info(f"=== WEBHOOK LOGS REQUEST END ===")
        
        return network_response.success_response(
            http_code=HTTPCode.SUCCESS,
            message=f"Retrieved {len(logs_data)} webhook logs",
            data=response_data,
            resource=http_request.url.path,
            start_time=start_time
        )
        
    except HTTPException as he:
        logger.error(f"HTTP Exception in webhook logs: {he.detail}")
        logger.info(f"=== WEBHOOK LOGS REQUEST END (HTTP ERROR) ===")
        
        return network_response.json_response(
            http_code=he.status_code,
            error_message=he.detail,
            resource=http_request.url.path,
            start_time=start_time
        )
    
    except MemoryError as me:
        logger.error(f"Memory error retrieving webhook logs: {str(me)}")
        logger.info(f"=== WEBHOOK LOGS REQUEST END (MEMORY ERROR) ===")
        return network_response.json_response(
            http_code=HTTPCode.INTERNAL_SERVER_ERROR,
            error_message="Server is experiencing high load. Please try again with a smaller limit.",
            resource=http_request.url.path,
            start_time=start_time
        )
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving webhook logs: {str(e)}", exc_info=True)
        logger.info(f"=== WEBHOOK LOGS REQUEST END (SYSTEM ERROR) ===")
        return network_response.json_response(
            http_code=HTTPCode.INTERNAL_SERVER_ERROR,
            error_message="An unexpected error occurred while retrieving logs. Please try again later.",
            resource=http_request.url.path,
            start_time=start_time
        )