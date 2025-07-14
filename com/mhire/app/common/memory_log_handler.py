import logging
from collections import deque
from typing import List, Dict
from datetime import datetime

class MemoryLogHandler(logging.Handler):
    """Custom logging handler that stores logs in memory with automatic cleanup"""
    
    def __init__(self, max_logs: int = 1000):
        super().__init__()
        self.max_logs = max_logs
        self.logs = deque(maxlen=max_logs)  # Automatically removes old logs when full
        
    def emit(self, record):
        """Store log record in memory"""
        try:
            # Format the log message
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "function": record.funcName,
                "line": record.lineno,
                "message": self.format(record)
            }
            
            self.logs.append(log_entry)
            
        except Exception:
            # Don't let logging errors break the application
            pass
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent logs"""
        if limit >= len(self.logs):
            return list(self.logs)
        else:
            # Get the most recent logs
            return list(self.logs)[-limit:]
    
    def get_logs_by_level(self, level: str, limit: int = 100) -> List[Dict]:
        """Get logs filtered by level"""
        filtered = [log for log in self.logs if log["level"] == level.upper()]
        return filtered[-limit:] if limit < len(filtered) else filtered
    
    def clear_logs(self):
        """Clear all logs"""
        self.logs.clear()
    
    def get_log_count(self) -> int:
        """Get total number of logs in memory"""
        return len(self.logs)
    
    def get_memory_usage_info(self) -> Dict:
        """Get information about memory usage"""
        return {
            "current_logs": len(self.logs),
            "max_logs": self.max_logs,
            "memory_usage_percent": (len(self.logs) / self.max_logs) * 100
        }