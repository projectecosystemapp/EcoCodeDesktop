"""
Security dashboard API for monitoring security health and events.

This module provides REST API endpoints for accessing security monitoring
data, managing security rules, and controlling security responses.

Requirements addressed:
- Implement security dashboard for monitoring security health
- Add security metrics collection and reporting
- Create automated response mechanisms for security events
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC, timedelta
import logging

from .security_monitor import (
    SecurityMonitor,
    SecurityRule,
    SecurityAlert,
    ThreatLevel,
    ResponseAction,
    get_security_monitor
)
from .security_logger import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    get_security_logger
)

logger = logging.getLogger(__name__)

# Create router for security dashboard endpoints
security_dashboard_router = APIRouter(prefix="/security", tags=["security"])


def get_monitor() -> SecurityMonitor:
    """Dependency to get security monitor instance."""
    monitor = get_security_monitor()
    if not monitor:
        raise HTTPException(status_code=503, detail="Security monitoring not initialized")
    return monitor


@security_dashboard_router.get("/dashboard")
async def get_security_dashboard(monitor: SecurityMonitor = Depends(get_monitor)) -> Dict[str, Any]:
    """
    Get comprehensive security dashboard data.
    
    Returns:
        Dictionary containing security metrics, alerts, and system status
    """
    try:
        dashboard_data = monitor.get_security_dashboard_data()
        return {
            "status": "success",
            "data": dashboard_data,
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


@security_dashboard_router.get("/metrics")
async def get_security_metrics(
    hours: int = Query(24, ge=1, le=168, description="Hours of metrics to retrieve"),
    monitor: SecurityMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Get security metrics for the specified time period.
    
    Args:
        hours: Number of hours of metrics to retrieve (1-168)
        
    Returns:
        Security metrics data
    """
    try:
        dashboard_data = monitor.get_security_dashboard_data()
        
        # Filter metrics history based on requested hours
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        filtered_metrics = [
            metric for metric in dashboard_data['metrics_history']
            if datetime.fromisoformat(metric['timestamp']) >= cutoff_time
        ]
        
        return {
            "status": "success",
            "data": {
                "current_metrics": dashboard_data['current_metrics'],
                "metrics_history": filtered_metrics,
                "period_hours": hours
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting security metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security metrics")


@security_dashboard_router.get("/alerts")
async def get_security_alerts(
    status: Optional[str] = Query(None, description="Filter by alert status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of alerts to return"),
    monitor: SecurityMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Get security alerts.
    
    Args:
        status: Optional status filter (active, resolved)
        limit: Maximum number of alerts to return
        
    Returns:
        List of security alerts
    """
    try:
        dashboard_data = monitor.get_security_dashboard_data()
        alerts = dashboard_data['active_alerts']
        
        # Filter by status if specified
        if status:
            alerts = [alert for alert in alerts if alert.get('status') == status]
        
        # Limit results
        alerts = alerts[:limit]
        
        return {
            "status": "success",
            "data": {
                "alerts": alerts,
                "total_count": len(alerts),
                "filtered_by_status": status
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting security alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security alerts")


@security_dashboard_router.get("/events")
async def get_security_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to search back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return")
) -> Dict[str, Any]:
    """
    Search security events with filters.
    
    Args:
        event_type: Filter by event type
        severity: Filter by severity level
        source_ip: Filter by source IP address
        user_id: Filter by user ID
        hours: Hours to search back
        limit: Maximum number of events to return
        
    Returns:
        List of matching security events
    """
    try:
        security_logger = get_security_logger()
        if not security_logger:
            raise HTTPException(status_code=503, detail="Security logging not initialized")
        
        # Convert string parameters to enums if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = SecurityEventType(event_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
        
        severity_enum = None
        if severity:
            try:
                severity_enum = SecuritySeverity(severity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        # Search events
        events = security_logger.search_events(
            event_type=event_type_enum,
            severity=severity_enum,
            source_ip=source_ip,
            user_id=user_id,
            hours_back=hours,
            limit=limit
        )
        
        # Convert events to dictionaries
        event_dicts = [event.to_dict() for event in events]
        
        return {
            "status": "success",
            "data": {
                "events": event_dicts,
                "total_count": len(event_dicts),
                "filters": {
                    "event_type": event_type,
                    "severity": severity,
                    "source_ip": source_ip,
                    "user_id": user_id,
                    "hours_back": hours
                }
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching security events: {e}")
        raise HTTPException(status_code=500, detail="Failed to search security events")


@security_dashboard_router.get("/rules")
async def get_security_rules(monitor: SecurityMonitor = Depends(get_monitor)) -> Dict[str, Any]:
    """
    Get all security monitoring rules.
    
    Returns:
        List of security rules
    """
    try:
        dashboard_data = monitor.get_security_dashboard_data()
        rules = dashboard_data['security_rules']
        
        return {
            "status": "success",
            "data": {
                "rules": rules,
                "total_count": len(rules)
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting security rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security rules")


@security_dashboard_router.post("/rules/{rule_id}/enable")
async def enable_security_rule(
    rule_id: str,
    monitor: SecurityMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Enable a security monitoring rule.
    
    Args:
        rule_id: ID of the rule to enable
        
    Returns:
        Success status
    """
    try:
        if rule_id not in monitor.security_rules:
            raise HTTPException(status_code=404, detail=f"Security rule not found: {rule_id}")
        
        monitor.security_rules[rule_id].enabled = True
        logger.info(f"Enabled security rule: {rule_id}")
        
        return {
            "status": "success",
            "message": f"Security rule {rule_id} enabled",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling security rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable security rule")


@security_dashboard_router.post("/rules/{rule_id}/disable")
async def disable_security_rule(
    rule_id: str,
    monitor: SecurityMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Disable a security monitoring rule.
    
    Args:
        rule_id: ID of the rule to disable
        
    Returns:
        Success status
    """
    try:
        if rule_id not in monitor.security_rules:
            raise HTTPException(status_code=404, detail=f"Security rule not found: {rule_id}")
        
        monitor.security_rules[rule_id].enabled = False
        logger.info(f"Disabled security rule: {rule_id}")
        
        return {
            "status": "success",
            "message": f"Security rule {rule_id} disabled",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling security rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable security rule")


@security_dashboard_router.post("/alerts/{alert_id}/resolve")
async def resolve_security_alert(
    alert_id: str,
    monitor: SecurityMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Resolve a security alert.
    
    Args:
        alert_id: ID of the alert to resolve
        
    Returns:
        Success status
    """
    try:
        success = monitor.resolve_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Security alert not found: {alert_id}")
        
        return {
            "status": "success",
            "message": f"Security alert {alert_id} resolved",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving security alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve security alert")


@security_dashboard_router.post("/unblock/ip/{ip_address}")
async def unblock_ip_address(
    ip_address: str,
    monitor: SecurityMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Unblock an IP address.
    
    Args:
        ip_address: IP address to unblock
        
    Returns:
        Success status
    """
    try:
        success = monitor.unblock_ip(ip_address)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"IP address not blocked: {ip_address}")
        
        return {
            "status": "success",
            "message": f"IP address {ip_address} unblocked",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking IP {ip_address}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock IP address")


@security_dashboard_router.post("/unblock/user/{user_id}")
async def unblock_user_id(
    user_id: str,
    monitor: SecurityMonitor = Depends(get_monitor)
) -> Dict[str, Any]:
    """
    Unblock a user.
    
    Args:
        user_id: User ID to unblock
        
    Returns:
        Success status
    """
    try:
        success = monitor.unblock_user(user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"User not blocked: {user_id}")
        
        return {
            "status": "success",
            "message": f"User {user_id} unblocked",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock user")


@security_dashboard_router.get("/status")
async def get_security_status(monitor: SecurityMonitor = Depends(get_monitor)) -> Dict[str, Any]:
    """
    Get overall security system status.
    
    Returns:
        Security system status information
    """
    try:
        dashboard_data = monitor.get_security_dashboard_data()
        system_status = dashboard_data['system_status']
        current_metrics = dashboard_data['current_metrics']
        
        return {
            "status": "success",
            "data": {
                "system_status": system_status,
                "threat_level": current_metrics['threat_level'],
                "total_events": current_metrics['total_events'],
                "active_alerts": len(dashboard_data['active_alerts']),
                "blocked_ips": len(dashboard_data['blocked_ips']),
                "blocked_users": len(dashboard_data['blocked_users']),
                "monitoring_active": system_status['monitoring_active']
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting security status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security status")


@security_dashboard_router.get("/health")
async def security_health_check() -> Dict[str, Any]:
    """
    Health check endpoint for security monitoring system.
    
    Returns:
        Health status of security components
    """
    try:
        monitor = get_security_monitor()
        security_logger = get_security_logger()
        
        health_status = {
            "security_monitor": "healthy" if monitor and monitor.is_monitoring else "unhealthy",
            "security_logger": "healthy" if security_logger else "unhealthy",
            "overall_status": "healthy"
        }
        
        # Determine overall status
        if health_status["security_monitor"] == "unhealthy" or health_status["security_logger"] == "unhealthy":
            health_status["overall_status"] = "degraded"
        
        return {
            "status": "success",
            "data": health_status,
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in security health check: {e}")
        return {
            "status": "error",
            "data": {
                "security_monitor": "error",
                "security_logger": "error",
                "overall_status": "unhealthy",
                "error": str(e)
            },
            "timestamp": datetime.now(UTC).isoformat()
        }