import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from com.mhire.app.services.chatbot_services.ai_chatbot.ai_chatbot_router import router as chatbot_router
from com.mhire.app.services.twilio_services.twilio_sms.twilio_sms_router import router as twilio_sms_router
from com.mhire.app.common.network_responses import NetworkResponse, HTTPCode
from com.mhire.app.common.memory_log_handler import MemoryLogHandler

# Setup in-memory logging (no file logging)
memory_log_handler = MemoryLogHandler(max_logs=2000)  # Store up to 2000 logs in memory
memory_log_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers.clear()  # Remove any existing handlers
root_logger.addHandler(logging.StreamHandler())  # Console output
root_logger.addHandler(memory_log_handler)  # Memory storage

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Chatbot",
    description="AI-powered chatbot with escalation logic",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for Pydantic validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors using NetworkResponse format"""
    start_time = time.time()
    
    # Determine resource based on URL path
    resource = "validation_error"
    if "/chat/send" in str(request.url):
        resource = request.url.path
    elif "/chat" in str(request.url):
        resource = request.url.path
    elif "/webhooks" in str(request.url):
        resource = request.url.path
    
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    
    # Extract the first error for the main message
    first_error = exc.errors()[0] if exc.errors() else {}
    field_name = " -> ".join(str(loc) for loc in first_error.get("loc", [])[1:])  # Skip 'body'
    error_msg = first_error.get("msg", "Validation error")
    
    # Create user-friendly error message
    if first_error.get("type") == "enum":
        if "organization_type" in field_name:
            error_msg = "Invalid organization type. Must be 'SMB' or 'HRH'"
    elif first_error.get("type") == "missing":
        error_msg = f"Required field '{field_name}' is missing"
    elif first_error.get("type") == "string_too_short":
        error_msg = f"Field '{field_name}' cannot be empty"
    
    # Use NetworkResponse format
    network_response = NetworkResponse()
    return network_response.json_response(
        http_code=HTTPCode.UNPROCESSABLE_ENTITY,
        error_message=error_msg,
        resource=request.url.path,
        start_time=start_time
    )

# Register routers
app.include_router(chatbot_router)
app.include_router(twilio_sms_router)

logger.info("FastAPI application started successfully")

@app.get("/")
async def root():
    start_time = time.time()
    network_response = NetworkResponse()
    return network_response.success_response(
        http_code=HTTPCode.SUCCESS,
        message="API is running",
        data={"status": "active"},
        resource="/",
        start_time=start_time
    )

@app.get("/health")
async def health_check():
    start_time = time.time()
    network_response = NetworkResponse()
    return network_response.success_response(
        http_code=HTTPCode.SUCCESS,
        message="Service is healthy",
        data={"status": "healthy"},
        resource="/health",
        start_time=start_time
    )

@app.get("/logs")
async def get_application_logs(
    limit: int = 100,
    level: str = None
):
    """Get application logs from memory"""
    start_time = time.time()
    network_response = NetworkResponse()
    
    try:
        if level:
            logs = memory_log_handler.get_logs_by_level(level, limit)
        else:
            logs = memory_log_handler.get_logs(limit)
        
        data = {
            "logs": logs,
            "memory_info": memory_log_handler.get_memory_usage_info()
        }
        
        return network_response.success_response(
            http_code=HTTPCode.SUCCESS,
            message="Application logs retrieved successfully",
            data=data,
            resource="/logs",
            start_time=start_time
        )
    except Exception as e:
        return network_response.json_response(
            http_code=HTTPCode.INTERNAL_SERVER_ERROR,
            error_message=f"Error retrieving logs: {str(e)}",
            resource="/logs",
            start_time=start_time
        )

@app.post("/logs/clear")
async def clear_application_logs():
    """Clear all application logs from memory"""
    start_time = time.time()
    network_response = NetworkResponse()
    
    try:
        memory_log_handler.clear_logs()
        return network_response.success_response(
            http_code=HTTPCode.SUCCESS,
            message="Application logs cleared successfully",
            data={"cleared": True},
            resource="/logs/clear",
            start_time=start_time
        )
    except Exception as e:
        return network_response.json_response(
            http_code=HTTPCode.INTERNAL_SERVER_ERROR,
            error_message=f"Error clearing logs: {str(e)}",
            resource="/logs/clear",
            start_time=start_time
        )