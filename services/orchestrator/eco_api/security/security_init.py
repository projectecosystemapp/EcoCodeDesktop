"""
Security system initialization module.

This module provides initialization functions for the complete security
monitoring and logging system, including configuration setup and
integration with the main application.

Requirements addressed:
- Initialize security event logging system
- Setup runtime security monitoring
- Configure security dashboard and alerting
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .security_logger import (
    SecurityLogConfig,
    initialize_security_logging,
    get_security_logger
)
from .security_monitor import (
    initialize_security_monitoring,
    get_security_monitor
)


logger = logging.getLogger(__name__)


async def initialize_security_system(
    workspace_root: str = ".",
    config: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Initialize the complete security monitoring and logging system.
    
    Args:
        workspace_root: Root directory of the workspace
        config: Optional configuration dictionary
        
    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        # Default configuration
        default_config = {
            "logging": {
                "log_directory": Path(workspace_root) / ".kiro" / "logs" / "security",
                "max_log_size": 50 * 1024 * 1024,  # 50MB
                "backup_count": 10,
                "retention_days": 90,
                "enable_email_alerts": False,
                "email_config": None,
                "alert_cooldown_minutes": 15,
                "critical_alert_recipients": [],
                "high_alert_recipients": [],
                "enable_structured_logging": True,
                "log_level": logging.INFO
            },
            "monitoring": {
                "monitoring_interval": 60,
                "metrics_retention_hours": 24,
                "max_events_in_memory": 10000,
                "auto_start": True
            }
        }
        
        # Merge with provided config
        if config:
            default_config.update(config)
        
        # Initialize security logging
        log_config = SecurityLogConfig(**default_config["logging"])
        # Ensure log directory exists
        log_config.log_directory.mkdir(parents=True, exist_ok=True)
        security_logger = initialize_security_logging(log_config)
        
        if not security_logger:
            logger.error("Failed to initialize security logging")
            return False
        
        logger.info("Security logging initialized successfully")
        
        # Initialize security monitoring
        monitor_config = default_config["monitoring"]
        security_monitor = initialize_security_monitoring(
            workspace_root=workspace_root,
            monitoring_interval=monitor_config["monitoring_interval"],
            auto_start=monitor_config["auto_start"]
        )
        
        if not security_monitor:
            logger.error("Failed to initialize security monitoring")
            return False
        
        logger.info("Security monitoring initialized successfully")
        
        # Start monitoring if auto_start is enabled
        if monitor_config["auto_start"]:
            await security_monitor.start_monitoring()
            logger.info("Security monitoring started")
        else:
            logger.info("Security monitoring initialized but not started (auto_start=False)")
        
        # Log successful initialization
        logger.info("Security system initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize security system: {e}")
        return False


async def shutdown_security_system() -> None:
    """
    Shutdown the security monitoring and logging system gracefully.
    """
    try:
        # Stop security monitoring
        security_monitor = get_security_monitor()
        if security_monitor:
            await security_monitor.stop_monitoring()
            logger.info("Security monitoring stopped")
        
        # Close security logger
        security_logger = get_security_logger()
        if security_logger:
            security_logger.close()
            logger.info("Security logging closed")
        
        logger.info("Security system shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during security system shutdown: {e}")


def get_security_system_status() -> Dict[str, Any]:
    """
    Get the current status of the security system.
    
    Returns:
        Dictionary with security system status information
    """
    try:
        security_logger = get_security_logger()
        security_monitor = get_security_monitor()
        
        status = {
            "security_logging": {
                "initialized": security_logger is not None,
                "status": "active" if security_logger else "inactive"
            },
            "security_monitoring": {
                "initialized": security_monitor is not None,
                "status": "active" if security_monitor and security_monitor.is_monitoring else "inactive"
            },
            "overall_status": "healthy"
        }
        
        # Determine overall status
        if not security_logger or not security_monitor:
            status["overall_status"] = "degraded"
        elif not security_monitor.is_monitoring:
            status["overall_status"] = "monitoring_inactive"
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting security system status: {e}")
        return {
            "security_logging": {"initialized": False, "status": "error"},
            "security_monitoring": {"initialized": False, "status": "error"},
            "overall_status": "error",
            "error": str(e)
        }


def create_default_security_config(workspace_root: str) -> Dict[str, Any]:
    """
    Create a default security configuration for the workspace.
    
    Args:
        workspace_root: Root directory of the workspace
        
    Returns:
        Default security configuration dictionary
    """
    workspace_path = Path(workspace_root)
    
    return {
        "logging": {
            "log_directory": workspace_path / ".kiro" / "logs" / "security",
            "max_log_size": 50 * 1024 * 1024,  # 50MB
            "backup_count": 10,
            "retention_days": 90,
            "enable_email_alerts": False,
            "email_config": {
                "smtp_server": "localhost",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_address": "security@ecocode.local"
            },
            "alert_cooldown_minutes": 15,
            "critical_alert_recipients": [],
            "high_alert_recipients": [],
            "enable_structured_logging": True,
            "log_level": logging.INFO
        },
        "monitoring": {
            "monitoring_interval": 60,
            "metrics_retention_hours": 24,
            "max_events_in_memory": 10000,
            "auto_start": True
        }
    }


def save_security_config(config: Dict[str, Any], workspace_root: str) -> bool:
    """
    Save security configuration to file.
    
    Args:
        config: Security configuration to save
        workspace_root: Root directory of the workspace
        
    Returns:
        True if configuration was saved successfully
    """
    try:
        import json
        
        config_path = Path(workspace_root) / ".kiro" / "security_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, default=str)
        
        logger.info(f"Security configuration saved to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save security configuration: {e}")
        return False


def load_security_config(workspace_root: str) -> Optional[Dict[str, Any]]:
    """
    Load security configuration from file.
    
    Args:
        workspace_root: Root directory of the workspace
        
    Returns:
        Security configuration dictionary or None if not found
    """
    try:
        import json
        
        config_path = Path(workspace_root) / ".kiro" / "security_config.json"
        
        if not config_path.exists():
            logger.info("No security configuration file found, using defaults")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info(f"Security configuration loaded from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load security configuration: {e}")
        return None


# Convenience function for quick setup
async def quick_setup_security(workspace_root: str = ".") -> bool:
    """
    Quick setup of security system with default configuration.
    
    Args:
        workspace_root: Root directory of the workspace
        
    Returns:
        True if setup was successful
    """
    try:
        # Try to load existing config, otherwise use defaults
        config = load_security_config(workspace_root)
        if not config:
            config = create_default_security_config(workspace_root)
            save_security_config(config, workspace_root)
        
        # Initialize security system
        success = await initialize_security_system(workspace_root, config)
        
        if success:
            logger.info("Quick security setup completed successfully")
        else:
            logger.error("Quick security setup failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in quick security setup: {e}")
        return False