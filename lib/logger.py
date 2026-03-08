import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Paths
JARVIS_ROOT = Path(os.environ.get("JARVIS_ROOT", Path(__file__).resolve().parent.parent))
LOGS_DIR = JARVIS_ROOT / "logs"
SYSTEM_LOG_FILE = LOGS_DIR / "system.jsonl"

class JSONLFormatter(logging.Formatter):
    """
    Format log records as JSON lines for structured ingestion.
    Each line is a valid JSON object.
    """
    def format(self, record: logging.LogRecord) -> str:
        """
        Formats a log record into a JSON string.
        
        Args:
            record: The log record to format.
            
        Returns:
            A JSON string representing the log record.
        """
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        # Include exception info if any
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Include extra context if passed via 'extra'
        if hasattr(record, "context"):
            log_obj["context"] = record.context
            
        return json.dumps(log_obj)

def get_logger(name: str) -> logging.Logger:
    """
    Get a structured JSON logger for the given component.
    Writes to JARVIS_ROOT/logs/system.jsonl.
    
    Args:
        name: The name of the component or module to log for.
        
    Returns:
        A logging.Logger instance configured with a JSONL formatter.
    """
    logger = logging.getLogger(name)
    
    # If already configured, return it
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # File handler (JSONL)
    file_handler = logging.FileHandler(SYSTEM_LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setFormatter(JSONLFormatter())
    logger.addHandler(file_handler)
    
    # Prevent propagation to root logger (avoids duplicate console output if root is configured)
    logger.propagate = False
    
    return logger

# Convenience singleton for the CLI or quick scripts
system_logger = get_logger("system")
