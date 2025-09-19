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
]
