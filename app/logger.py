import logging
import logging.config
import os
import json
from datetime import datetime

def setup_logger(name: str = None) -> logging.Logger:
    """
    Set up and return a logger instance.
    
    Args:
        name: Logger name (usually __name__ from the calling module)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    
    # Default configuration
    log_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': os.getenv('LOG_FILE', 'logs/app.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'root': {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'handlers': ['console', 'file']
        }
    }
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_config['handlers']['file']['filename'])
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Apply configuration
    logging.config.dictConfig(log_config)
    
    # Return logger
    return logging.getLogger(name)

# Create a default logger instance for the module
logger = setup_logger(__name__)