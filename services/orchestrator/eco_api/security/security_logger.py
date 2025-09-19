"""
Security event logging system for centralized security monitoring.

This module provides comprehensive security event collection, structured logging,
log rotation, retention policies, and alerting for critical security violations.

Requirements addressed:
- Create centralized security event collection
- Add structured logging for all security violations
- Implement log rotation and retention policies
- Create security event alerting for critical violations
"""

import json
import logging
import logging.handlers
import os
import smtplib
import time
from datetime import datetime, UTC, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from threading import Lock
import asyncio
from concurrent.futures import ThreadPoolExecutor


class SecurityEventType(str, Enum):
    """Types of security events."""
    URL_VALIDATION_FAILURE = "url_validation_failure"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"
    XSS_ATTEMPT = "xss_attempt"
    AUTHORIZATION_FAILURE = "authorization_failure"
    AUTHENTICATION_FAILURE = "authentication_failure"
    SUSPICIOUS_FILE_ACCESS = "suspicious_file_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    MALFORMED_REQUEST = "malformed_request"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration_attempt"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    INJECTION_ATTEMPT = "injection_attempt"


class SecuritySeverity(str, Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventStatus(str, Enum):
    """Security event status."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_id: str
    event_type: SecurityEventType
    severity: SecuritySeverity
    timestamp: datetime
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    blocked_content: Optional[str] = None
    threat_indicators: List[str] = field(default_factory=list)
    additional_context: Dict[str, Any] = field(default_factory=dict)
    status: SecurityEventStatus = SecurityEventStatus.DETECTED
    response_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and serialization."""
        data = asdict(self)
        # Convert datetime to ISO format
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityEvent':
        """Create SecurityEvent from dictionary."""
        # Remove log-specific fields that aren't part of SecurityEvent
        clean_data = data.copy()
        clean_data.pop('log_timestamp', None)
        clean_data.pop('log_level', None)
        clean_data.pop('logger_name', None)
        
        # If data is nested under 'security_event', extract it
        if 'security_event' in clean_data:
            clean_data = clean_data['security_event']
        
        # Convert timestamp back to datetime
        if isinstance(clean_data.get('timestamp'), str):
            clean_data['timestamp'] = datetime.fromisoformat(clean_data['timestamp'])
        
        # Convert enums
        if isinstance(clean_data.get('event_type'), str):
            clean_data['event_type'] = SecurityEventType(clean_data['event_type'])
        if isinstance(clean_data.get('severity'), str):
            clean_data['severity'] = SecuritySeverity(clean_data['severity'])
        if isinstance(clean_data.get('status'), str):
            clean_data['status'] = SecurityEventStatus(clean_data['status'])
        
        return cls(**clean_data)


@dataclass
class SecurityLogConfig:
    """Configuration for security logging."""
    log_directory: Path
    max_log_size: int = 50 * 1024 * 1024  # 50MB
    backup_count: int = 10
    retention_days: int = 90
    enable_email_alerts: bool = False
    email_config: Optional[Dict[str, str]] = None
    alert_cooldown_minutes: int = 15
    critical_alert_recipients: List[str] = field(default_factory=list)
    high_alert_recipients: List[str] = field(default_factory=list)
    enable_structured_logging: bool = True
    log_level: int = logging.INFO


class SecurityEventLogger:
    """
    Centralized security event logging system.
    
    Provides structured logging, alerting, and monitoring for security events
    with configurable retention policies and alert mechanisms.
    """
    
    def __init__(self, config: SecurityLogConfig):
        """
        Initialize the security event logger.
        
        Args:
            config: Security logging configuration
        """
        self.config = config
        self.logger = self._setup_logger()
        self.alert_logger = self._setup_alert_logger()
        self._alert_lock = Lock()
        self._last_alert_times: Dict[str, datetime] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="security-alert")
        
        # Create log directory
        self.config.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup log rotation and cleanup
        self._setup_log_rotation()
        
        # Initialize event counters for monitoring
        self._event_counters: Dict[SecurityEventType, int] = {}
        self._severity_counters: Dict[SecuritySeverity, int] = {}
    
    def _setup_logger(self) -> logging.Logger:
        """Setup the main security logger."""
        logger = logging.getLogger("security_events")
        logger.setLevel(self.config.log_level)
        
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Setup rotating file handler
        log_file = self.config.log_directory / "security_events.log"
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.max_log_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        
        if self.config.enable_structured_logging:
            formatter = SecurityEventFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_alert_logger(self) -> logging.Logger:
        """Setup the security alert logger."""
        logger = logging.getLogger("security_alerts")
        logger.setLevel(logging.WARNING)
        
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Setup alert log file
        alert_log_file = self.config.log_directory / "security_alerts.log"
        handler = logging.handlers.RotatingFileHandler(
            alert_log_file,
            maxBytes=self.config.max_log_size // 2,
            backupCount=5,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY ALERT - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_log_rotation(self) -> None:
        """Setup log rotation and cleanup policies."""
        # Schedule cleanup of old logs
        self._cleanup_old_logs()
    
    def _cleanup_old_logs(self) -> None:
        """Clean up logs older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
            
            for log_file in self.config.log_directory.glob("*.log*"):
                try:
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        log_file.unlink()
                        self.logger.info(f"Cleaned up old log file: {log_file}")
                except (OSError, ValueError) as e:
                    self.logger.warning(f"Error cleaning up log file {log_file}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error during log cleanup: {e}")
    
    def log_security_event(self, event: SecurityEvent) -> None:
        """
        Log a security event with appropriate handling based on severity.
        
        Args:
            event: Security event to log
        """
        try:
            # Update counters
            self._update_counters(event)
            
            # Log the event
            log_level = self._get_log_level_for_severity(event.severity)
            self.logger.log(log_level, event.to_json())
            
            # Handle alerts for high severity events
            if event.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                self._handle_security_alert(event)
            
            # Log to alert logger for medium and above
            if event.severity in [SecuritySeverity.MEDIUM, SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                self.alert_logger.warning(f"Security Event: {event.event_type.value} - {event.severity.value}")
        
        except Exception as e:
            # Fallback logging to ensure security events are never lost
            fallback_logger = logging.getLogger("security_fallback")
            fallback_logger.error(f"Error logging security event: {e}")
            fallback_logger.error(f"Original event: {event.to_json()}")
    
    def _update_counters(self, event: SecurityEvent) -> None:
        """Update event counters for monitoring."""
        self._event_counters[event.event_type] = self._event_counters.get(event.event_type, 0) + 1
        self._severity_counters[event.severity] = self._severity_counters.get(event.severity, 0) + 1
    
    def _get_log_level_for_severity(self, severity: SecuritySeverity) -> int:
        """Get appropriate log level for security severity."""
        severity_levels = {
            SecuritySeverity.LOW: logging.INFO,
            SecuritySeverity.MEDIUM: logging.WARNING,
            SecuritySeverity.HIGH: logging.ERROR,
            SecuritySeverity.CRITICAL: logging.CRITICAL
        }
        return severity_levels.get(severity, logging.WARNING)
    
    def _handle_security_alert(self, event: SecurityEvent) -> None:
        """
        Handle security alerts for high severity events.
        
        Args:
            event: Security event that triggered the alert
        """
        try:
            # Check alert cooldown
            alert_key = f"{event.event_type.value}_{event.source_ip or 'unknown'}"
            
            with self._alert_lock:
                last_alert = self._last_alert_times.get(alert_key)
                now = datetime.now(UTC)
                
                if last_alert and (now - last_alert).total_seconds() < (self.config.alert_cooldown_minutes * 60):
                    # Skip alert due to cooldown
                    return
                
                self._last_alert_times[alert_key] = now
            
            # Send alert asynchronously
            if self.config.enable_email_alerts and self.config.email_config:
                self._executor.submit(self._send_email_alert, event)
            
            # Log the alert
            self.alert_logger.critical(f"SECURITY ALERT: {event.to_json()}")
        
        except Exception as e:
            self.logger.error(f"Error handling security alert: {e}")
    
    def _send_email_alert(self, event: SecurityEvent) -> None:
        """
        Send email alert for security event.
        
        Args:
            event: Security event to alert about
        """
        try:
            if not self.config.email_config:
                return
            
            # Determine recipients based on severity
            recipients = []
            if event.severity == SecuritySeverity.CRITICAL:
                recipients.extend(self.config.critical_alert_recipients)
            if event.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                recipients.extend(self.config.high_alert_recipients)
            
            if not recipients:
                return
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_config.get('from_address', 'security@ecocode.local')
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"Security Alert: {event.event_type.value} ({event.severity.value})"
            
            # Email body
            body = self._create_alert_email_body(event)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            smtp_server = self.config.email_config.get('smtp_server')
            smtp_port = int(self.config.email_config.get('smtp_port', 587))
            username = self.config.email_config.get('username')
            password = self.config.email_config.get('password')
            
            if smtp_server and username and password:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
                
                self.logger.info(f"Security alert email sent for event {event.event_id}")
        
        except Exception as e:
            self.logger.error(f"Error sending security alert email: {e}")
    
    def _create_alert_email_body(self, event: SecurityEvent) -> str:
        """Create HTML email body for security alert."""
        return f"""
        <html>
        <body>
            <h2 style="color: red;">Security Alert</h2>
            <p><strong>Event Type:</strong> {event.event_type.value}</p>
            <p><strong>Severity:</strong> {event.severity.value}</p>
            <p><strong>Timestamp:</strong> {event.timestamp.isoformat()}</p>
            <p><strong>Event ID:</strong> {event.event_id}</p>
            
            {f'<p><strong>Source IP:</strong> {event.source_ip}</p>' if event.source_ip else ''}
            {f'<p><strong>User ID:</strong> {event.user_id}</p>' if event.user_id else ''}
            {f'<p><strong>Resource:</strong> {event.resource}</p>' if event.resource else ''}
            {f'<p><strong>Action:</strong> {event.action}</p>' if event.action else ''}
            
            {f'<p><strong>Threat Indicators:</strong></p><ul>{"".join(f"<li>{indicator}</li>" for indicator in event.threat_indicators)}</ul>' if event.threat_indicators else ''}
            
            {f'<p><strong>Blocked Content:</strong></p><pre style="background-color: #f0f0f0; padding: 10px;">{event.blocked_content}</pre>' if event.blocked_content else ''}
            
            <p><strong>Additional Context:</strong></p>
            <pre style="background-color: #f0f0f0; padding: 10px;">{json.dumps(event.additional_context, indent=2)}</pre>
            
            <p><em>This is an automated security alert from EcoCode Security Monitoring System.</em></p>
        </body>
        </html>
        """
    
    def get_event_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get security event statistics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with event statistics
        """
        return {
            'event_type_counts': dict(self._event_counters),
            'severity_counts': dict(self._severity_counters),
            'total_events': sum(self._event_counters.values()),
            'period_hours': hours,
            'timestamp': datetime.now(UTC).isoformat()
        }
    
    def search_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecuritySeverity] = None,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        hours_back: int = 24,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """
        Search security events based on criteria.
        
        Args:
            event_type: Filter by event type
            severity: Filter by severity
            source_ip: Filter by source IP
            user_id: Filter by user ID
            hours_back: Hours to search back
            limit: Maximum number of events to return
            
        Returns:
            List of matching security events
        """
        # This is a simplified implementation
        # In production, you might want to use a proper database
        events = []
        
        try:
            log_file = self.config.log_directory / "security_events.log"
            if not log_file.exists():
                return events
            
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours_back)
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        if line.strip():
                            event_data = json.loads(line.strip())
                            event = SecurityEvent.from_dict(event_data)
                            
                            # Apply filters
                            if event.timestamp < cutoff_time:
                                continue
                            if event_type and event.event_type != event_type:
                                continue
                            if severity and event.severity != severity:
                                continue
                            if source_ip and event.source_ip != source_ip:
                                continue
                            if user_id and event.user_id != user_id:
                                continue
                            
                            events.append(event)
                            
                            if len(events) >= limit:
                                break
                    
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        except Exception as e:
            self.logger.error(f"Error searching events: {e}")
        
        return events
    
    def close(self) -> None:
        """Close the security logger and cleanup resources."""
        try:
            self._executor.shutdown(wait=True)
            
            # Close handlers
            for handler in self.logger.handlers:
                handler.close()
            for handler in self.alert_logger.handlers:
                handler.close()
        
        except Exception as e:
            logging.getLogger(__name__).error(f"Error closing security logger: {e}")


class SecurityEventFormatter(logging.Formatter):
    """Custom formatter for security events."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        try:
            # Try to parse the message as JSON (for SecurityEvent objects)
            event_data = json.loads(record.getMessage())
            
            # Add logging metadata
            log_entry = {
                'log_timestamp': datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
                'log_level': record.levelname,
                'logger_name': record.name,
                'security_event': event_data
            }
            
            return json.dumps(log_entry, ensure_ascii=False)
        
        except json.JSONDecodeError:
            # Fallback to regular formatting
            return super().format(record)


# Global security logger instance
_security_logger: Optional[SecurityEventLogger] = None


def initialize_security_logging(config: SecurityLogConfig) -> SecurityEventLogger:
    """
    Initialize the global security logger.
    
    Args:
        config: Security logging configuration
        
    Returns:
        Initialized SecurityEventLogger instance
    """
    global _security_logger
    _security_logger = SecurityEventLogger(config)
    return _security_logger


def get_security_logger() -> Optional[SecurityEventLogger]:
    """Get the global security logger instance."""
    return _security_logger


def log_security_event(event: SecurityEvent) -> None:
    """
    Log a security event using the global logger.
    
    Args:
        event: Security event to log
    """
    if _security_logger:
        _security_logger.log_security_event(event)
    else:
        # Fallback logging
        fallback_logger = logging.getLogger("security_fallback")
        fallback_logger.warning(f"Security logger not initialized. Event: {event.to_json()}")


# Convenience functions for creating common security events
def create_url_validation_event(
    blocked_url: str,
    source_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    threat_indicators: Optional[List[str]] = None
) -> SecurityEvent:
    """Create a URL validation failure event."""
    return SecurityEvent(
        event_id=f"url_{int(time.time() * 1000000)}",
        event_type=SecurityEventType.URL_VALIDATION_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        timestamp=datetime.now(UTC),
        source_ip=source_ip,
        user_id=user_id,
        action="url_validation",
        blocked_content=blocked_url,
        threat_indicators=threat_indicators or []
    )


def create_path_traversal_event(
    attempted_path: str,
    source_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    threat_indicators: Optional[List[str]] = None
) -> SecurityEvent:
    """Create a path traversal attempt event."""
    return SecurityEvent(
        event_id=f"path_{int(time.time() * 1000000)}",
        event_type=SecurityEventType.PATH_TRAVERSAL_ATTEMPT,
        severity=SecuritySeverity.HIGH,
        timestamp=datetime.now(UTC),
        source_ip=source_ip,
        user_id=user_id,
        action="file_access",
        blocked_content=attempted_path,
        threat_indicators=threat_indicators or []
    )


def create_xss_attempt_event(
    malicious_content: str,
    source_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    threat_indicators: Optional[List[str]] = None
) -> SecurityEvent:
    """Create an XSS attempt event."""
    return SecurityEvent(
        event_id=f"xss_{int(time.time() * 1000000)}",
        event_type=SecurityEventType.XSS_ATTEMPT,
        severity=SecuritySeverity.HIGH,
        timestamp=datetime.now(UTC),
        source_ip=source_ip,
        user_id=user_id,
        action="content_submission",
        blocked_content=malicious_content,
        threat_indicators=threat_indicators or []
    )


def create_authorization_failure_event(
    operation: str,
    resource: Optional[str] = None,
    source_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> SecurityEvent:
    """Create an authorization failure event."""
    return SecurityEvent(
        event_id=f"auth_{int(time.time() * 1000000)}",
        event_type=SecurityEventType.AUTHORIZATION_FAILURE,
        severity=SecuritySeverity.MEDIUM,
        timestamp=datetime.now(UTC),
        source_ip=source_ip,
        user_id=user_id,
        resource=resource,
        action=operation,
        additional_context=additional_context or {}
    )