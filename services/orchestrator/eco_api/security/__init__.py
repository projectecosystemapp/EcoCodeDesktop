"""Security utilities for EcoCode."""

from .crypto import WorkspaceCipher, build_cipher, derive_key, generate_salt
from .html_sanitizer import (
    HTMLSanitizer, 
    SanitizationLevel, 
    SanitizationResult,
    escape_html,
    sanitize_user_input,
    is_script_content,
    create_safe_template_content
)
from .path_validator import (
    PathValidator,
    ValidationResult,
    SecurityLevel,
    PathValidationError
)
from .authorization_validator import (
    AuthorizationValidator,
    UserContext,
    Permission,
    Role,
    AuthorizationEvent,
    AuthorizationResult,
    create_default_validator,
    create_admin_context,
    create_developer_context
)
from .security_logger import (
    SecurityEventLogger,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityEventStatus,
    SecurityLogConfig,
    initialize_security_logging,
    get_security_logger,
    log_security_event,
    create_url_validation_event,
    create_path_traversal_event,
    create_xss_attempt_event,
    create_authorization_failure_event
)
from .security_monitor import (
    SecurityMonitor,
    SecurityRule,
    SecurityAlert,
    SecurityMetrics,
    ThreatLevel,
    ResponseAction,
    initialize_security_monitoring,
    get_security_monitor,
    process_security_event
)
from .security_dashboard import security_dashboard_router
from .security_init import (
    initialize_security_system,
    shutdown_security_system,
    get_security_system_status,
    create_default_security_config,
    quick_setup_security
)

__all__ = [
    "WorkspaceCipher",
    "build_cipher",
    "derive_key",
    "generate_salt",
    "HTMLSanitizer",
    "SanitizationLevel",
    "SanitizationResult",
    "escape_html",
    "sanitize_user_input",
    "is_script_content",
    "create_safe_template_content",
    "AuthorizationValidator",
    "UserContext",
    "Permission",
    "Role",
    "AuthorizationEvent",
    "AuthorizationResult",
    "create_default_validator",
    "create_admin_context",
    "create_developer_context",
    "PathValidator",
    "ValidationResult",
    "SecurityLevel",
    "PathValidationError",
    "SecurityEventLogger",
    "SecurityEvent",
    "SecurityEventType",
    "SecuritySeverity",
    "SecurityEventStatus",
    "SecurityLogConfig",
    "initialize_security_logging",
    "get_security_logger",
    "log_security_event",
    "create_url_validation_event",
    "create_path_traversal_event",
    "create_xss_attempt_event",
    "create_authorization_failure_event",
    "SecurityMonitor",
    "SecurityRule",
    "SecurityAlert",
    "SecurityMetrics",
    "ThreatLevel",
    "ResponseAction",
    "initialize_security_monitoring",
    "get_security_monitor",
    "process_security_event",
    "security_dashboard_router",
    "initialize_security_system",
    "shutdown_security_system",
    "get_security_system_status",
    "create_default_security_config",
    "quick_setup_security",
]
