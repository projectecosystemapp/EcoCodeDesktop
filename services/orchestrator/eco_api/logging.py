import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

LOG_FORMAT = '%(asctime)s %(levelname)s [%(name)s] %(funcName)s:%(lineno)d %(message)s'
SIMPLE_FORMAT = '%(asctime)s %(levelname)s %(message)s'


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_structured_logging: bool = False,
) -> None:
    """Configure logging for production use with file rotation and structured logging."""
    
    # Determine log level from environment
    env_level = os.getenv('ECOCODE_LOG_LEVEL', 'INFO').upper()
    if env_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        level = getattr(logging, env_level)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with appropriate format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if enable_structured_logging:
        console_formatter = StructuredFormatter()
    else:
        console_formatter = logging.Formatter(LOG_FORMAT)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        if enable_structured_logging:
            file_formatter = StructuredFormatter()
        else:
            file_formatter = logging.Formatter(LOG_FORMAT)
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_spec_loggers(level)
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {logging.getLevelName(level)}")
    if log_file:
        logger.info(f"Log file: {log_file}")


def configure_spec_loggers(level: int) -> None:
    """Configure specific loggers for spec-driven workflow components."""
    
    # Spec workflow loggers
    spec_loggers = [
        'eco_api.specs.workflow_orchestrator',
        'eco_api.specs.generators',
        'eco_api.specs.task_execution_engine',
        'eco_api.specs.research_service',
        'eco_api.specs.file_manager',
        'eco_api.specs.error_recovery',
        'eco_api.specs.validation_framework',
    ]
    
    for logger_name in spec_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Set more verbose logging for critical components in debug mode
    if level == logging.DEBUG:
        logging.getLogger('eco_api.specs.task_execution_engine').setLevel(logging.DEBUG)
        logging.getLogger('eco_api.specs.workflow_orchestrator').setLevel(logging.DEBUG)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for production logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone
        
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'spec_id'):
            log_entry['spec_id'] = record.spec_id
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id
        if hasattr(record, 'phase'):
            log_entry['phase'] = record.phase
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        return json.dumps(log_entry, ensure_ascii=False)


def get_spec_logger(name: str) -> logging.Logger:
    """Get a logger configured for spec workflow operations."""
    return logging.getLogger(f'eco_api.specs.{name}')


def log_spec_operation(
    logger: logging.Logger,
    operation: str,
    spec_id: Optional[str] = None,
    task_id: Optional[str] = None,
    phase: Optional[str] = None,
    level: int = logging.INFO,
    **kwargs
) -> None:
    """Log a spec operation with structured context."""
    extra = {}
    if spec_id:
        extra['spec_id'] = spec_id
    if task_id:
        extra['task_id'] = task_id
    if phase:
        extra['phase'] = phase
    
    # Add any additional context
    extra.update(kwargs)
    
    logger.log(level, operation, extra=extra)

