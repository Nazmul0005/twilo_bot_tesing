import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from com.mhire.app.services.twilio_services.twilio_sms.twilio_sms_schema import WebhookLogEntry, MessageStatus

logger = logging.getLogger(__name__)

class WebhookLogManager:
    """Manages webhook logs in memory"""
    
    def __init__(self):
        self.webhook_logs: List[Dict[str, Any]] = []
        logger.debug("WebhookLogManager initialized")
    
    def add_webhook_log(
        self,
        message_sid: str,
        status: MessageStatus,
        from_number: str,
        to_number: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Add a webhook log entry"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message_sid": message_sid,
            "status": status.value,
            "from_number": from_number,
            "to_number": to_number,
            "error_code": error_code,
            "error_message": error_message
        }
        
        self.webhook_logs.append(log_entry)
        
        # Keep only last 1000 logs to prevent memory issues
        if len(self.webhook_logs) > 1000:
            self.webhook_logs = self.webhook_logs[-1000:]
        
        logger.debug(f"Added webhook log for message {message_sid} with status {status.value}")
    
    def get_all_logs(self) -> List[WebhookLogEntry]:
        """Get all webhook logs"""
        return [
            WebhookLogEntry(
                timestamp=log["timestamp"],
                message_sid=log["message_sid"],
                status=MessageStatus(log["status"]),
                from_number=log["from_number"],
                to_number=log["to_number"],
                error_code=log.get("error_code"),
                error_message=log.get("error_message")
            )
            for log in self.webhook_logs
        ]
    
    def get_logs_by_status(self, status: MessageStatus) -> List[WebhookLogEntry]:
        """Get logs filtered by status"""
        filtered_logs = [log for log in self.webhook_logs if log["status"] == status.value]
        return [
            WebhookLogEntry(
                timestamp=log["timestamp"],
                message_sid=log["message_sid"],
                status=MessageStatus(log["status"]),
                from_number=log["from_number"],
                to_number=log["to_number"],
                error_code=log.get("error_code"),
                error_message=log.get("error_message")
            )
            for log in filtered_logs
        ]
    
    def get_logs_by_number(self, phone_number: str) -> List[WebhookLogEntry]:
        """Get logs for a specific phone number (from or to)"""
        filtered_logs = [
            log for log in self.webhook_logs 
            if log["from_number"] == phone_number or log["to_number"] == phone_number
        ]
        return [
            WebhookLogEntry(
                timestamp=log["timestamp"],
                message_sid=log["message_sid"],
                status=MessageStatus(log["status"]),
                from_number=log["from_number"],
                to_number=log["to_number"],
                error_code=log.get("error_code"),
                error_message=log.get("error_message")
            )
            for log in filtered_logs
        ]
    
    def get_recent_logs(self, limit: int = 50) -> List[WebhookLogEntry]:
        """Get most recent webhook logs"""
        logger.debug(f"Getting recent logs with limit {limit}, total logs: {len(self.webhook_logs)}")
        
        # Get the most recent logs (last N entries)
        if len(self.webhook_logs) <= limit:
            recent_logs = self.webhook_logs
        else:
            recent_logs = self.webhook_logs[-limit:]
        
        logger.debug(f"Selected {len(recent_logs)} logs for return")
        
        # Convert to WebhookLogEntry objects, most recent first
        result = [
            WebhookLogEntry(
                timestamp=log["timestamp"],
                message_sid=log["message_sid"],
                status=MessageStatus(log["status"]),
                from_number=log["from_number"],
                to_number=log["to_number"],
                error_code=log.get("error_code"),
                error_message=log.get("error_message")
            )
            for log in reversed(recent_logs)  # Most recent first
        ]
        
        logger.debug(f"Returning {len(result)} webhook log entries")
        return result
    
    def clear_logs(self):
        """Clear all webhook logs"""
        self.webhook_logs.clear()
        logger.debug("Cleared all webhook logs")
    
    def get_log_count(self) -> int:
        """Get total number of logs"""
        return len(self.webhook_logs)