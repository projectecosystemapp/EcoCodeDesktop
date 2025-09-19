"""
Runtime security monitoring system for real-time threat detection and response.

This module provides real-time security violation detection, automated response
mechanisms, security metrics collection, and monitoring dashboard capabilities.

Requirements addressed:
- Implement real-time security violation detection
- Create automated response mechanisms for security events
- Add security metrics collection and reporting
- Implement security dashboard for monitoring security health
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

from .security_logger import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityEventStatus,
    get_security_logger
)


class ThreatLevel(str, Enum):
    """Threat level classifications."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ResponseAction(str, Enum):
    """Automated response actions."""
    LOG_ONLY = "log_only"
    RATE_LIMIT = "rate_limit"
    BLOCK_IP = "block_ip"
    BLOCK_USER = "block_user"
    ALERT_ADMIN = "alert_admin"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


@dataclass
class SecurityMetrics:
    """Security metrics data structure."""
    timestamp: datetime
    total_events: int = 0
    events_by_type: Dict[SecurityEventType, int] = field(default_factory=dict)
    events_by_severity: Dict[SecuritySeverity, int] = field(default_factory=dict)
    unique_source_ips: Set[str] = field(default_factory=set)
    unique_users: Set[str] = field(default_factory=set)
    threat_level: ThreatLevel = ThreatLevel.MINIMAL
    response_actions_taken: List[ResponseAction] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_events': self.total_events,
            'events_by_type': {k.value: v for k, v in self.events_by_type.items()},
            'events_by_severity': {k.value: v for k, v in self.events_by_severity.items()},
            'unique_source_ips': len(self.unique_source_ips),
            'unique_users': len(self.unique_users),
            'threat_level': self.threat_level.value,
            'response_actions_taken': [action.value for action in self.response_actions_taken]
        }


@dataclass
class SecurityRule:
    """Security monitoring rule."""
    rule_id: str
    name: str
    description: str
    event_types: List[SecurityEventType]
    severity_threshold: SecuritySeverity
    time_window_minutes: int
    max_events: int
    response_actions: List[ResponseAction]
    enabled: bool = True
    
    def matches_event(self, event: SecurityEvent) -> bool:
        """Check if event matches this rule."""
        if not self.enabled:
            return False
        
        return (
            event.event_type in self.event_types and
            self._severity_meets_threshold(event.severity)
        )
    
    def _severity_meets_threshold(self, severity: SecuritySeverity) -> bool:
        """Check if severity meets the threshold."""
        severity_order = {
            SecuritySeverity.LOW: 1,
            SecuritySeverity.MEDIUM: 2,
            SecuritySeverity.HIGH: 3,
            SecuritySeverity.CRITICAL: 4
        }
        
        return severity_order.get(severity, 0) >= severity_order.get(self.severity_threshold, 0)


@dataclass
class SecurityAlert:
    """Security alert data structure."""
    alert_id: str
    rule_id: str
    rule_name: str
    triggered_at: datetime
    events: List[SecurityEvent]
    threat_level: ThreatLevel
    response_actions: List[ResponseAction]
    status: str = "active"
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'triggered_at': self.triggered_at.isoformat(),
            'event_count': len(self.events),
            'threat_level': self.threat_level.value,
            'response_actions': [action.value for action in self.response_actions],
            'status': self.status,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class SecurityMonitor:
    """
    Real-time security monitoring system.
    
    Provides continuous monitoring of security events, automated threat detection,
    response mechanisms, and security metrics collection.
    """
    
    def __init__(
        self,
        workspace_root: str = ".",
        monitoring_interval: int = 60,
        metrics_retention_hours: int = 24,
        max_events_in_memory: int = 10000
    ):
        """
        Initialize the security monitor.
        
        Args:
            workspace_root: Root directory of the workspace
            monitoring_interval: Monitoring interval in seconds
            metrics_retention_hours: How long to retain metrics
            max_events_in_memory: Maximum events to keep in memory
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.monitoring_interval = monitoring_interval
        self.metrics_retention_hours = metrics_retention_hours
        self.max_events_in_memory = max_events_in_memory
        
        # Event storage
        self.recent_events: deque = deque(maxlen=max_events_in_memory)
        self.events_by_ip: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.events_by_user: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=metrics_retention_hours * 60 // monitoring_interval)
        self.current_metrics = SecurityMetrics(timestamp=datetime.now(UTC))
        
        # Security rules
        self.security_rules: Dict[str, SecurityRule] = {}
        self.active_alerts: Dict[str, SecurityAlert] = {}
        
        # Blocked entities
        self.blocked_ips: Set[str] = set()
        self.blocked_users: Set[str] = set()
        self.rate_limited_ips: Dict[str, datetime] = {}
        self.rate_limited_users: Dict[str, datetime] = {}
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="security-monitor")
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> None:
        """Initialize default security monitoring rules."""
        
        # High-frequency attack detection
        self.add_rule(SecurityRule(
            rule_id="high_frequency_attacks",
            name="High Frequency Attack Detection",
            description="Detect high frequency security events from same source",
            event_types=[
                SecurityEventType.PATH_TRAVERSAL_ATTEMPT,
                SecurityEventType.XSS_ATTEMPT,
                SecurityEventType.AUTHORIZATION_FAILURE,
                SecurityEventType.AUTHENTICATION_FAILURE
            ],
            severity_threshold=SecuritySeverity.MEDIUM,
            time_window_minutes=5,
            max_events=10,
            response_actions=[ResponseAction.RATE_LIMIT, ResponseAction.ALERT_ADMIN]
        ))
        
        # Critical event detection
        self.add_rule(SecurityRule(
            rule_id="critical_events",
            name="Critical Security Events",
            description="Immediate response to critical security events",
            event_types=[
                SecurityEventType.PRIVILEGE_ESCALATION,
                SecurityEventType.DATA_EXFILTRATION_ATTEMPT,
                SecurityEventType.INJECTION_ATTEMPT
            ],
            severity_threshold=SecuritySeverity.CRITICAL,
            time_window_minutes=1,
            max_events=1,
            response_actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT_ADMIN]
        ))
        
        # Brute force detection
        self.add_rule(SecurityRule(
            rule_id="brute_force_detection",
            name="Brute Force Attack Detection",
            description="Detect brute force authentication attempts",
            event_types=[SecurityEventType.AUTHENTICATION_FAILURE],
            severity_threshold=SecuritySeverity.LOW,
            time_window_minutes=10,
            max_events=5,
            response_actions=[ResponseAction.RATE_LIMIT, ResponseAction.ALERT_ADMIN]
        ))
        
        # Path traversal detection
        self.add_rule(SecurityRule(
            rule_id="path_traversal_detection",
            name="Path Traversal Attack Detection",
            description="Detect repeated path traversal attempts",
            event_types=[SecurityEventType.PATH_TRAVERSAL_ATTEMPT],
            severity_threshold=SecuritySeverity.MEDIUM,
            time_window_minutes=5,
            max_events=3,
            response_actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT_ADMIN]
        ))
    
    def add_rule(self, rule: SecurityRule) -> None:
        """
        Add a security monitoring rule.
        
        Args:
            rule: Security rule to add
        """
        with self._lock:
            self.security_rules[rule.rule_id] = rule
            self.logger.info(f"Added security rule: {rule.name} ({rule.rule_id})")
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a security monitoring rule.
        
        Args:
            rule_id: ID of rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        with self._lock:
            if rule_id in self.security_rules:
                del self.security_rules[rule_id]
                self.logger.info(f"Removed security rule: {rule_id}")
                return True
            return False
    
    def process_security_event(self, event: SecurityEvent) -> None:
        """
        Process a security event for monitoring and response.
        
        Args:
            event: Security event to process
        """
        try:
            with self._lock:
                # Store event
                self.recent_events.append(event)
                
                if event.source_ip:
                    self.events_by_ip[event.source_ip].append(event)
                
                if event.user_id:
                    self.events_by_user[event.user_id].append(event)
                
                # Update current metrics
                self._update_metrics(event)
                
                # Check if event should be blocked
                if self._should_block_event(event):
                    self.logger.warning(f"Blocked event from {event.source_ip or event.user_id}: {event.event_type}")
                    return
                
                # Check security rules
                self._check_security_rules(event)
        
        except Exception as e:
            self.logger.error(f"Error processing security event: {e}")
    
    def _update_metrics(self, event: SecurityEvent) -> None:
        """Update current security metrics with new event."""
        self.current_metrics.total_events += 1
        
        # Update event type counts
        if event.event_type not in self.current_metrics.events_by_type:
            self.current_metrics.events_by_type[event.event_type] = 0
        self.current_metrics.events_by_type[event.event_type] += 1
        
        # Update severity counts
        if event.severity not in self.current_metrics.events_by_severity:
            self.current_metrics.events_by_severity[event.severity] = 0
        self.current_metrics.events_by_severity[event.severity] += 1
        
        # Update unique counts
        if event.source_ip:
            self.current_metrics.unique_source_ips.add(event.source_ip)
        if event.user_id:
            self.current_metrics.unique_users.add(event.user_id)
        
        # Update threat level
        self.current_metrics.threat_level = self._calculate_threat_level()
    
    def _calculate_threat_level(self) -> ThreatLevel:
        """Calculate current threat level based on recent events."""
        if not self.current_metrics.total_events:
            return ThreatLevel.MINIMAL
        
        # Count critical and high severity events
        critical_count = self.current_metrics.events_by_severity.get(SecuritySeverity.CRITICAL, 0)
        high_count = self.current_metrics.events_by_severity.get(SecuritySeverity.HIGH, 0)
        
        # Calculate threat level
        if critical_count > 0:
            return ThreatLevel.CRITICAL
        elif high_count >= 5:
            return ThreatLevel.HIGH
        elif high_count >= 2 or self.current_metrics.total_events >= 20:
            return ThreatLevel.MODERATE
        elif self.current_metrics.total_events >= 5:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.MINIMAL
    
    def _should_block_event(self, event: SecurityEvent) -> bool:
        """Check if event should be blocked based on current blocks/limits."""
        # Check IP blocks
        if event.source_ip and event.source_ip in self.blocked_ips:
            return True
        
        # Check user blocks
        if event.user_id and event.user_id in self.blocked_users:
            return True
        
        # Check rate limits
        if event.source_ip and event.source_ip in self.rate_limited_ips:
            limit_time = self.rate_limited_ips[event.source_ip]
            if datetime.now(UTC) < limit_time:
                return True
            else:
                # Rate limit expired
                del self.rate_limited_ips[event.source_ip]
        
        if event.user_id and event.user_id in self.rate_limited_users:
            limit_time = self.rate_limited_users[event.user_id]
            if datetime.now(UTC) < limit_time:
                return True
            else:
                # Rate limit expired
                del self.rate_limited_users[event.user_id]
        
        return False
    
    def _check_security_rules(self, event: SecurityEvent) -> None:
        """Check security rules against the event."""
        for rule in self.security_rules.values():
            if rule.matches_event(event):
                self._evaluate_rule(rule, event)
    
    def _evaluate_rule(self, rule: SecurityRule, triggering_event: SecurityEvent) -> None:
        """
        Evaluate a security rule and take action if threshold is met.
        
        Args:
            rule: Security rule to evaluate
            triggering_event: Event that triggered the rule
        """
        try:
            # Get recent events that match this rule
            cutoff_time = datetime.now(UTC) - timedelta(minutes=rule.time_window_minutes)
            
            matching_events = []
            for event in self.recent_events:
                if (event.timestamp >= cutoff_time and 
                    rule.matches_event(event) and
                    (not triggering_event.source_ip or event.source_ip == triggering_event.source_ip) and
                    (not triggering_event.user_id or event.user_id == triggering_event.user_id)):
                    matching_events.append(event)
            
            # Check if threshold is exceeded
            if len(matching_events) >= rule.max_events:
                self._trigger_rule_response(rule, matching_events, triggering_event)
        
        except Exception as e:
            self.logger.error(f"Error evaluating security rule {rule.rule_id}: {e}")
    
    def _trigger_rule_response(
        self, 
        rule: SecurityRule, 
        matching_events: List[SecurityEvent], 
        triggering_event: SecurityEvent
    ) -> None:
        """
        Trigger response actions for a security rule.
        
        Args:
            rule: Security rule that was triggered
            matching_events: Events that matched the rule
            triggering_event: Event that triggered the response
        """
        try:
            # Create alert
            alert = SecurityAlert(
                alert_id=f"alert_{rule.rule_id}_{int(time.time())}",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                triggered_at=datetime.now(UTC),
                events=matching_events,
                threat_level=self._calculate_threat_level(),
                response_actions=rule.response_actions
            )
            
            self.active_alerts[alert.alert_id] = alert
            
            # Execute response actions
            for action in rule.response_actions:
                self._execute_response_action(action, triggering_event, alert)
            
            self.logger.warning(f"Security rule triggered: {rule.name} - Alert: {alert.alert_id}")
        
        except Exception as e:
            self.logger.error(f"Error triggering rule response for {rule.rule_id}: {e}")
    
    def _execute_response_action(
        self, 
        action: ResponseAction, 
        event: SecurityEvent, 
        alert: SecurityAlert
    ) -> None:
        """
        Execute a specific response action.
        
        Args:
            action: Response action to execute
            event: Triggering event
            alert: Associated alert
        """
        try:
            if action == ResponseAction.LOG_ONLY:
                self.logger.info(f"Security alert logged: {alert.alert_id}")
            
            elif action == ResponseAction.RATE_LIMIT:
                if event.source_ip:
                    self.rate_limited_ips[event.source_ip] = datetime.now(UTC) + timedelta(minutes=15)
                    self.logger.warning(f"Rate limited IP: {event.source_ip}")
                
                if event.user_id:
                    self.rate_limited_users[event.user_id] = datetime.now(UTC) + timedelta(minutes=15)
                    self.logger.warning(f"Rate limited user: {event.user_id}")
            
            elif action == ResponseAction.BLOCK_IP:
                if event.source_ip:
                    self.blocked_ips.add(event.source_ip)
                    self.logger.error(f"Blocked IP: {event.source_ip}")
            
            elif action == ResponseAction.BLOCK_USER:
                if event.user_id:
                    self.blocked_users.add(event.user_id)
                    self.logger.error(f"Blocked user: {event.user_id}")
            
            elif action == ResponseAction.ALERT_ADMIN:
                self._send_admin_alert(alert)
            
            elif action == ResponseAction.EMERGENCY_SHUTDOWN:
                self.logger.critical("EMERGENCY SHUTDOWN TRIGGERED")
                # In a real implementation, this would trigger system shutdown
            
            # Record action taken
            self.current_metrics.response_actions_taken.append(action)
        
        except Exception as e:
            self.logger.error(f"Error executing response action {action}: {e}")
    
    def _send_admin_alert(self, alert: SecurityAlert) -> None:
        """
        Send alert to administrators.
        
        Args:
            alert: Alert to send
        """
        # This would integrate with your notification system
        self.logger.critical(f"ADMIN ALERT: {alert.rule_name} - {alert.alert_id}")
        
        # In a real implementation, you would send emails, Slack messages, etc.
        alert_data = alert.to_dict()
        self.logger.critical(f"Alert details: {json.dumps(alert_data, indent=2)}")
    
    async def start_monitoring(self) -> None:
        """Start the security monitoring system."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Security monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop the security monitoring system."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self._executor.shutdown(wait=True)
        self.logger.info("Security monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Update metrics
                self._update_periodic_metrics()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Check system health
                self._check_system_health()
                
                await asyncio.sleep(self.monitoring_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    def _update_periodic_metrics(self) -> None:
        """Update periodic metrics and reset counters."""
        with self._lock:
            # Save current metrics to history
            self.metrics_history.append(self.current_metrics)
            
            # Reset current metrics
            self.current_metrics = SecurityMetrics(timestamp=datetime.now(UTC))
    
    def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=self.metrics_retention_hours)
        
        # Clean up rate limits
        expired_ips = [ip for ip, limit_time in self.rate_limited_ips.items() if limit_time < datetime.now(UTC)]
        for ip in expired_ips:
            del self.rate_limited_ips[ip]
        
        expired_users = [user for user, limit_time in self.rate_limited_users.items() if limit_time < datetime.now(UTC)]
        for user in expired_users:
            del self.rate_limited_users[user]
        
        # Clean up resolved alerts
        resolved_alerts = [alert_id for alert_id, alert in self.active_alerts.items() 
                          if alert.resolved_at and alert.resolved_at < cutoff_time]
        for alert_id in resolved_alerts:
            del self.active_alerts[alert_id]
    
    def _check_system_health(self) -> None:
        """Check overall system security health."""
        threat_level = self._calculate_threat_level()
        
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self.logger.warning(f"System threat level: {threat_level.value}")
        
        # Check for anomalies
        if len(self.blocked_ips) > 100:
            self.logger.warning(f"High number of blocked IPs: {len(self.blocked_ips)}")
        
        if len(self.active_alerts) > 50:
            self.logger.warning(f"High number of active alerts: {len(self.active_alerts)}")
    
    def get_security_dashboard_data(self) -> Dict[str, Any]:
        """
        Get security dashboard data for monitoring interface.
        
        Returns:
            Dictionary with security dashboard data
        """
        with self._lock:
            return {
                'current_metrics': self.current_metrics.to_dict(),
                'metrics_history': [metrics.to_dict() for metrics in list(self.metrics_history)[-24:]],
                'active_alerts': [alert.to_dict() for alert in self.active_alerts.values()],
                'blocked_ips': list(self.blocked_ips),
                'blocked_users': list(self.blocked_users),
                'rate_limited_ips': len(self.rate_limited_ips),
                'rate_limited_users': len(self.rate_limited_users),
                'security_rules': {
                    rule_id: {
                        'name': rule.name,
                        'description': rule.description,
                        'enabled': rule.enabled,
                        'event_types': [et.value for et in rule.event_types],
                        'severity_threshold': rule.severity_threshold.value,
                        'time_window_minutes': rule.time_window_minutes,
                        'max_events': rule.max_events
                    }
                    for rule_id, rule in self.security_rules.items()
                },
                'system_status': {
                    'monitoring_active': self.is_monitoring,
                    'threat_level': self.current_metrics.threat_level.value,
                    'last_updated': datetime.now(UTC).isoformat()
                }
            }
    
    def unblock_ip(self, ip_address: str) -> bool:
        """
        Unblock an IP address.
        
        Args:
            ip_address: IP address to unblock
            
        Returns:
            True if IP was unblocked, False if not found
        """
        with self._lock:
            if ip_address in self.blocked_ips:
                self.blocked_ips.remove(ip_address)
                self.logger.info(f"Unblocked IP: {ip_address}")
                return True
            return False
    
    def unblock_user(self, user_id: str) -> bool:
        """
        Unblock a user.
        
        Args:
            user_id: User ID to unblock
            
        Returns:
            True if user was unblocked, False if not found
        """
        with self._lock:
            if user_id in self.blocked_users:
                self.blocked_users.remove(user_id)
                self.logger.info(f"Unblocked user: {user_id}")
                return True
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an active alert.
        
        Args:
            alert_id: Alert ID to resolve
            
        Returns:
            True if alert was resolved, False if not found
        """
        with self._lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].status = "resolved"
                self.active_alerts[alert_id].resolved_at = datetime.now(UTC)
                self.logger.info(f"Resolved alert: {alert_id}")
                return True
            return False


# Global security monitor instance
_security_monitor: Optional[SecurityMonitor] = None


def initialize_security_monitoring(
    workspace_root: str = ".",
    monitoring_interval: int = 60,
    auto_start: bool = True
) -> SecurityMonitor:
    """
    Initialize the global security monitor.
    
    Args:
        workspace_root: Root directory of the workspace
        monitoring_interval: Monitoring interval in seconds
        auto_start: Whether to automatically start monitoring
        
    Returns:
        Initialized SecurityMonitor instance
    """
    global _security_monitor
    _security_monitor = SecurityMonitor(
        workspace_root=workspace_root,
        monitoring_interval=monitoring_interval
    )
    
    if auto_start:
        asyncio.create_task(_security_monitor.start_monitoring())
    
    return _security_monitor


def get_security_monitor() -> Optional[SecurityMonitor]:
    """Get the global security monitor instance."""
    return _security_monitor


def process_security_event(event: SecurityEvent) -> None:
    """
    Process a security event using the global monitor.
    
    Args:
        event: Security event to process
    """
    if _security_monitor:
        _security_monitor.process_security_event(event)
    else:
        # Fallback logging if monitor not available
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Security monitor not available, cannot process event: {event.event_id}")