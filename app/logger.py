import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(name: str = "api", log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers if logger is already configured
    if logger.handlers:
        return logger

    # Log to stdout
    handler = logging.StreamHandler(sys.stdout)
    
    # Format log entries as JSON in production
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to the root logger to avoid duplicate log outputs in Uvicorn
    logger.propagate = False
    
    return logger

# Initialize default application logger
logger = setup_logger()
