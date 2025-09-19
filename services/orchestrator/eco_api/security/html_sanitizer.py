"""
HTML sanitization utility for XSS prevention.

This module provides comprehensive HTML sanitization capabilities to prevent
cross-site scripting (XSS) attacks by escaping dangerous characters and
detecting potentially malicious content patterns.

Requirements addressed:
- 3.1: HTML character escaping for <, >, &, ", ' characters
- 3.2: Comprehensive user input sanitization methods
- 3.3: Script content detection and neutralization
"""

import re
import html
from typing import Dict, Any, List, Union, Optional
from dataclasses import dataclass
from enum import Enum


class SanitizationLevel(str, Enum):
    """Levels of HTML sanitization."""
    BASIC = "basic"          # Basic HTML escaping
    STRICT = "strict"        # Strict sanitization with script detection
    PARANOID = "paranoid"    # Maximum security, strips most HTML-like content


@dataclass
class SanitizationResult:
    """Result of HTML sanitization operation."""
    sanitized_content: str
    original_content: str
    threats_detected: List[str]
    sanitization_level: SanitizationLevel
    is_safe: bool


class HTMLSanitizer:
    """
    HTML sanitization utility class for XSS prevention.
    
    Provides comprehensive sanitization of user input to prevent cross-site
    scripting attacks while maintaining content readability.
    """
    
    # HTML characters that need escaping
    HTML_ESCAPE_TABLE = {
        '<': '&lt;',
        '>': '&gt;',
        '&': '&amp;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
        '`': '&#x60;',
        '=': '&#x3D;'
    }
    
    # Dangerous script patterns
    SCRIPT_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'data:text/html',
        r'data:application/javascript',
        r'on\w+\s*=',  # Event handlers like onclick, onload, etc.
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'expression\s*\(',
        r'url\s*\(',
        r'@import',
        r'<\s*\/?\s*[a-zA-Z]'  # Any HTML-like tags
    ]
    
    # Suspicious content patterns
    SUSPICIOUS_PATTERNS = [
        r'alert\s*\(',
        r'confirm\s*\(',
        r'prompt\s*\(',
        r'eval\s*\(',
        r'setTimeout\s*\(',
        r'setInterval\s*\(',
        r'document\.',
        r'window\.',
        r'location\.',
        r'cookie',
        r'localStorage',
        r'sessionStorage',
        r'constructor\.',
        r'prototype\.',
        r'__proto__'
    ]
    
    def __init__(self, default_level: SanitizationLevel = SanitizationLevel.STRICT):
        """
        Initialize the HTML sanitizer.
        
        Args:
            default_level: Default sanitization level to use
        """
        self.default_level = default_level
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        self.compiled_script_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) 
            for pattern in self.SCRIPT_PATTERNS
        ]
        self.compiled_suspicious_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.SUSPICIOUS_PATTERNS
        ]
    
    def escape_html(self, content: str) -> str:
        """
        Escape HTML characters in content.
        
        Requirements: 3.1 - HTML character escaping for <, >, &, ", ' characters
        
        Args:
            content: Content to escape
            
        Returns:
            HTML-escaped content
        """
        if not isinstance(content, str):
            content = str(content)
        
        # Use html.escape for basic escaping, then add our additional escapes
        escaped = html.escape(content, quote=True)
        
        # Additional character escaping for enhanced security
        for char, escape_seq in self.HTML_ESCAPE_TABLE.items():
            if char not in ['<', '>', '&', '"', "'"]:  # Already handled by html.escape
                escaped = escaped.replace(char, escape_seq)
        
        return escaped
    
    def sanitize_user_input(
        self, 
        input_data: Union[str, Dict[str, Any], List[Any]], 
        level: Optional[SanitizationLevel] = None
    ) -> Union[str, Dict[str, Any], List[Any]]:
        """
        Sanitize user input data comprehensively.
        
        Requirements: 3.2 - Comprehensive user input sanitization methods
        
        Args:
            input_data: Input data to sanitize (string, dict, or list)
            level: Sanitization level to use
            
        Returns:
            Sanitized input data
        """
        if level is None:
            level = self.default_level
        
        if isinstance(input_data, str):
            return self._sanitize_string(input_data, level)
        elif isinstance(input_data, dict):
            return self._sanitize_dict(input_data, level)
        elif isinstance(input_data, list):
            return self._sanitize_list(input_data, level)
        else:
            # For other types, convert to string and sanitize
            return self._sanitize_string(str(input_data), level)
    
    def _sanitize_string(self, content: str, level: SanitizationLevel) -> str:
        """
        Sanitize a string based on the specified level.
        
        Args:
            content: String content to sanitize
            level: Sanitization level
            
        Returns:
            Sanitized string
        """
        if not content:
            return content
        
        if level == SanitizationLevel.BASIC:
            return self.escape_html(content)
        
        elif level == SanitizationLevel.STRICT:
            # First neutralize script content before escaping
            sanitized = self._neutralize_scripts(content)
            
            # Then escape HTML
            sanitized = self.escape_html(sanitized)
            
            return sanitized
        
        elif level == SanitizationLevel.PARANOID:
            # Maximum security - neutralize scripts and suspicious content first
            sanitized = self._neutralize_scripts(content)
            sanitized = self._strip_suspicious_content(sanitized)
            
            # Then escape HTML
            sanitized = self.escape_html(sanitized)
            
            return sanitized
        
        return content
    
    def _sanitize_dict(self, data: Dict[str, Any], level: SanitizationLevel) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values.
        
        Args:
            data: Dictionary to sanitize
            level: Sanitization level
            
        Returns:
            Dictionary with sanitized values
        """
        sanitized = {}
        for key, value in data.items():
            # Sanitize the key as well
            sanitized_key = self._sanitize_string(str(key), level)
            sanitized[sanitized_key] = self.sanitize_user_input(value, level)
        return sanitized
    
    def _sanitize_list(self, data: List[Any], level: SanitizationLevel) -> List[Any]:
        """
        Recursively sanitize list items.
        
        Args:
            data: List to sanitize
            level: Sanitization level
            
        Returns:
            List with sanitized items
        """
        return [self.sanitize_user_input(item, level) for item in data]
    
    def is_script_content(self, content: str) -> bool:
        """
        Detect if content contains script-like patterns.
        
        Requirements: 3.3 - Script content detection and neutralization
        
        Args:
            content: Content to check
            
        Returns:
            True if script content is detected
        """
        if not isinstance(content, str):
            content = str(content)
        
        # Check against compiled script patterns
        for pattern in self.compiled_script_patterns:
            if pattern.search(content):
                return True
        
        return False
    
    def detect_threats(self, content: str) -> List[str]:
        """
        Detect potential security threats in content.
        
        Args:
            content: Content to analyze
            
        Returns:
            List of detected threat types
        """
        threats = []
        
        if not isinstance(content, str):
            content = str(content)
        
        # Check for script patterns
        for i, pattern in enumerate(self.compiled_script_patterns):
            if pattern.search(content):
                threat_name = self._get_threat_name_for_script_pattern(i)
                threats.append(threat_name)
        
        # Check for suspicious patterns
        for i, pattern in enumerate(self.compiled_suspicious_patterns):
            if pattern.search(content):
                threat_name = self._get_threat_name_for_suspicious_pattern(i)
                threats.append(threat_name)
        
        return list(set(threats))  # Remove duplicates
    
    def _get_threat_name_for_script_pattern(self, pattern_index: int) -> str:
        """Get human-readable threat name for script pattern."""
        threat_names = [
            "Script Tag",
            "JavaScript Protocol",
            "VBScript Protocol", 
            "HTML Data URI",
            "JavaScript Data URI",
            "Event Handler",
            "IFrame Tag",
            "Object Tag",
            "Embed Tag",
            "Link Tag",
            "Meta Tag",
            "Style Tag",
            "CSS Expression",
            "CSS URL",
            "CSS Import",
            "HTML Tag"
        ]
        
        if pattern_index < len(threat_names):
            return threat_names[pattern_index]
        return f"Script Pattern {pattern_index}"
    
    def _get_threat_name_for_suspicious_pattern(self, pattern_index: int) -> str:
        """Get human-readable threat name for suspicious pattern."""
        threat_names = [
            "Alert Function",
            "Confirm Function",
            "Prompt Function",
            "Eval Function",
            "SetTimeout Function",
            "SetInterval Function",
            "Document Object",
            "Window Object",
            "Location Object",
            "Cookie Access",
            "LocalStorage Access",
            "SessionStorage Access",
            "Constructor Access",
            "Prototype Access",
            "Proto Access"
        ]
        
        if pattern_index < len(threat_names):
            return threat_names[pattern_index]
        return f"Suspicious Pattern {pattern_index}"
    
    def _neutralize_scripts(self, content: str) -> str:
        """
        Neutralize script content by replacing dangerous patterns.
        
        Args:
            content: Content to neutralize
            
        Returns:
            Content with neutralized scripts
        """
        neutralized = content
        
        # Replace script patterns with safe alternatives
        for pattern in self.compiled_script_patterns:
            neutralized = pattern.sub('[SCRIPT_REMOVED]', neutralized)
        
        return neutralized
    
    def _strip_suspicious_content(self, content: str) -> str:
        """
        Strip suspicious content patterns.
        
        Args:
            content: Content to clean
            
        Returns:
            Content with suspicious patterns removed
        """
        cleaned = content
        
        # Replace suspicious patterns
        for pattern in self.compiled_suspicious_patterns:
            cleaned = pattern.sub('[SUSPICIOUS_CONTENT_REMOVED]', cleaned)
        
        return cleaned
    
    def sanitize_with_result(
        self, 
        content: str, 
        level: Optional[SanitizationLevel] = None
    ) -> SanitizationResult:
        """
        Sanitize content and return detailed result.
        
        Args:
            content: Content to sanitize
            level: Sanitization level to use
            
        Returns:
            SanitizationResult with detailed information
        """
        if level is None:
            level = self.default_level
        
        original_content = content
        threats_detected = self.detect_threats(content)
        sanitized_content = self._sanitize_string(content, level)
        is_safe = len(threats_detected) == 0
        
        return SanitizationResult(
            sanitized_content=sanitized_content,
            original_content=original_content,
            threats_detected=threats_detected,
            sanitization_level=level,
            is_safe=is_safe
        )
    
    def create_safe_template_content(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create template-safe content by sanitizing all values.
        
        Requirements: 3.1, 3.2, 3.3 - Template-safe content processing functions
        
        Args:
            template_data: Template data dictionary
            
        Returns:
            Dictionary with sanitized template data
        """
        return self.sanitize_user_input(template_data, SanitizationLevel.STRICT)
    
    def validate_safe_content(self, content: str) -> bool:
        """
        Validate that content is safe for use.
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is considered safe
        """
        threats = self.detect_threats(content)
        return len(threats) == 0


# Global sanitizer instance for convenience
default_sanitizer = HTMLSanitizer()

# Convenience functions
def escape_html(content: str) -> str:
    """Convenience function for HTML escaping."""
    return default_sanitizer.escape_html(content)

def sanitize_user_input(input_data: Union[str, Dict[str, Any], List[Any]]) -> Union[str, Dict[str, Any], List[Any]]:
    """Convenience function for user input sanitization."""
    return default_sanitizer.sanitize_user_input(input_data)

def is_script_content(content: str) -> bool:
    """Convenience function for script detection."""
    return default_sanitizer.is_script_content(content)

def create_safe_template_content(template_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for template-safe content creation."""
    return default_sanitizer.create_safe_template_content(template_data)