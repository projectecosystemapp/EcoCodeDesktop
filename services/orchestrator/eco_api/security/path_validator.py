"""
Path validation utility for preventing path traversal attacks.

This module provides comprehensive path validation and sanitization
to prevent directory traversal vulnerabilities in file operations.

Requirements addressed:
- 2.1: Path resolution and boundary checking
- 2.2: Path sanitization for dangerous sequences
- 2.3: Secure path joining functionality
- 2.4: Validation against common traversal patterns
"""

import os
import re
from pathlib import Path, PurePath
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class PathValidationError(Exception):
    """Exception raised for path validation errors."""
    pass


class SecurityLevel(Enum):
    """Security levels for path validation."""
    STRICT = "strict"      # Most restrictive
    MODERATE = "moderate"  # Balanced security and usability
    PERMISSIVE = "permissive"  # Least restrictive


@dataclass
class ValidationResult:
    """Result of path validation."""
    is_valid: bool
    sanitized_path: Optional[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class PathValidator:
    """
    Comprehensive path validator for preventing path traversal attacks.
    
    Provides path resolution, boundary checking, sanitization, and validation
    against common traversal patterns to ensure secure file operations.
    """
    
    # Common path traversal patterns
    TRAVERSAL_PATTERNS = [
        r'\.\./',           # ../
        r'\.\.\.',          # ...
        r'\.\.\\',          # ..\
        r'%2e%2e%2f',       # URL encoded ../
        r'%2e%2e%5c',       # URL encoded ..\
        r'%252e%252e%252f', # Double URL encoded ../
        r'%c0%ae%c0%ae%c0%af',  # UTF-8 encoded ../
        r'\.\.%c0%af',      # Mixed encoding
        r'\.\.%255c',       # Mixed encoding
    ]
    
    # Dangerous path components
    DANGEROUS_COMPONENTS = [
        '..',
        '.',
        '~',
        '$',
    ]
    
    # Restricted directory names (case-insensitive)
    RESTRICTED_DIRS = {
        'system32', 'windows', 'winnt', 'boot', 'etc', 'proc', 'sys',
        'dev', 'root', 'home', 'users', 'program files', 'programdata',
        'appdata', 'temp', 'tmp', 'var', 'usr', 'bin', 'sbin', 'lib',
        'opt', 'mnt', 'media'
    }
    
    # File extensions that should be restricted
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js',
        '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg', '.msi', '.dll',
        '.so', '.dylib', '.sys', '.drv'
    }
    
    def __init__(
        self,
        workspace_root: Union[str, Path],
        security_level: SecurityLevel = SecurityLevel.STRICT,
        allowed_extensions: Optional[List[str]] = None,
        max_path_length: int = 260,
        max_component_length: int = 255
    ):
        """
        Initialize PathValidator.
        
        Args:
            workspace_root: Root directory that paths must stay within
            security_level: Security level for validation
            allowed_extensions: List of allowed file extensions (if None, all are allowed)
            max_path_length: Maximum allowed path length
            max_component_length: Maximum allowed path component length
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.security_level = security_level
        self.allowed_extensions = set(allowed_extensions or [])
        self.max_path_length = max_path_length
        self.max_component_length = max_component_length
        
        # Ensure workspace root exists
        if not self.workspace_root.exists():
            raise PathValidationError(f"Workspace root does not exist: {self.workspace_root}")
        
        if not self.workspace_root.is_dir():
            raise PathValidationError(f"Workspace root is not a directory: {self.workspace_root}")
    
    def validate_path(self, path: Union[str, Path], allow_creation: bool = False) -> ValidationResult:
        """
        Validate a path for security and correctness.
        
        Args:
            path: Path to validate
            allow_creation: Whether to allow paths that don't exist yet
            
        Returns:
            ValidationResult with validation status and sanitized path
        """
        errors = []
        warnings = []
        
        try:
            # Convert to string for initial processing
            path_str = str(path)
            
            # Basic validation
            if not path_str or not path_str.strip():
                errors.append("Path cannot be empty")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Check for null bytes
            if '\x00' in path_str:
                errors.append("Path contains null bytes")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Check path length
            if len(path_str) > self.max_path_length:
                errors.append(f"Path too long: {len(path_str)} > {self.max_path_length}")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Check for traversal patterns
            traversal_check = self._check_traversal_patterns(path_str)
            if not traversal_check.is_valid:
                errors.extend(traversal_check.errors)
                return ValidationResult(is_valid=False, errors=errors)
            
            # Sanitize the path
            sanitized = self.sanitize_path(path_str)
            if not sanitized:
                errors.append("Path sanitization resulted in empty path")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Convert to Path object for further validation
            try:
                path_obj = Path(sanitized)
            except (ValueError, OSError) as e:
                errors.append(f"Invalid path format: {str(e)}")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Resolve path and check boundaries
            boundary_check = self._check_path_boundaries(path_obj, allow_creation)
            errors.extend(boundary_check.errors)
            warnings.extend(boundary_check.warnings)
            
            # Check path components
            component_check = self._check_path_components(path_obj)
            errors.extend(component_check.errors)
            warnings.extend(component_check.warnings)
            
            # Check file extension if applicable
            if path_obj.suffix:
                extension_check = self._check_file_extension(path_obj.suffix)
                errors.extend(extension_check.errors)
                warnings.extend(extension_check.warnings)
            
            # Security level specific checks
            security_check = self._apply_security_level_checks(path_obj)
            errors.extend(security_check.errors)
            warnings.extend(security_check.warnings)
            
            is_valid = len(errors) == 0
            return ValidationResult(
                is_valid=is_valid,
                sanitized_path=str(path_obj) if is_valid else None,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            errors.append(f"Unexpected validation error: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors)
    
    def sanitize_path(self, path: str) -> str:
        """
        Sanitize a path by removing dangerous sequences.
        
        Args:
            path: Path to sanitize
            
        Returns:
            Sanitized path string
        """
        if not path:
            return ""
        
        # Normalize path separators
        sanitized = path.replace('\\', '/')
        
        # Remove URL encoding
        sanitized = self._decode_url_encoding(sanitized)
        
        # Remove dangerous sequences
        for pattern in self.TRAVERSAL_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Remove multiple consecutive slashes
        sanitized = re.sub(r'/+', '/', sanitized)
        
        # Remove leading/trailing whitespace and slashes
        sanitized = sanitized.strip().strip('/')
        
        # Remove dangerous characters based on security level
        if self.security_level == SecurityLevel.STRICT:
            # Remove all non-alphanumeric except safe characters
            sanitized = re.sub(r'[^a-zA-Z0-9._/-]', '', sanitized)
        elif self.security_level == SecurityLevel.MODERATE:
            # Remove most dangerous characters
            sanitized = re.sub(r'[<>:"|?*\x00-\x1f]', '', sanitized)
        
        return sanitized
    
    def secure_join(self, *path_parts: Union[str, Path]) -> str:
        """
        Securely join path components, preventing traversal.
        
        Args:
            *path_parts: Path components to join
            
        Returns:
            Securely joined path
            
        Raises:
            PathValidationError: If the resulting path is invalid
        """
        if not path_parts:
            raise PathValidationError("No path parts provided")
        
        # Sanitize each part
        sanitized_parts = []
        for part in path_parts:
            if not part:
                continue
            
            part_str = str(part)
            
            # Check for traversal attempts in individual parts BEFORE sanitization
            if '..' in part_str or part_str.startswith('/') or part_str.startswith('\\'):
                raise PathValidationError(f"Invalid path component: {part_str}")
            
            sanitized = self.sanitize_path(part_str)
            
            if not sanitized:
                continue
            
            sanitized_parts.append(sanitized)
        
        if not sanitized_parts:
            raise PathValidationError("All path parts were empty after sanitization")
        
        # Join parts
        joined = '/'.join(sanitized_parts)
        
        # Validate the final path
        result = self.validate_path(joined, allow_creation=True)
        if not result.is_valid:
            raise PathValidationError(f"Invalid joined path: {', '.join(result.errors)}")
        
        return result.sanitized_path
    
    def is_path_traversal_attempt(self, path: str) -> bool:
        """
        Check if a path contains traversal patterns.
        
        Args:
            path: Path to check
            
        Returns:
            True if path contains traversal patterns
        """
        if not path:
            return False
        
        # Check for common traversal patterns
        for pattern in self.TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        
        # Check for dangerous components
        path_parts = path.replace('\\', '/').split('/')
        for part in path_parts:
            if part in self.DANGEROUS_COMPONENTS:
                return True
        
        return False
    
    def get_safe_path(self, path: Union[str, Path], relative_to_workspace: bool = True) -> Path:
        """
        Get a safe, resolved path within workspace boundaries.
        
        Args:
            path: Input path
            relative_to_workspace: Whether to make path relative to workspace
            
        Returns:
            Safe, resolved Path object
            
        Raises:
            PathValidationError: If path is invalid or outside boundaries
        """
        result = self.validate_path(path, allow_creation=True)
        if not result.is_valid:
            raise PathValidationError(f"Invalid path: {', '.join(result.errors)}")
        
        safe_path = Path(result.sanitized_path)
        
        # Make absolute if relative to workspace
        if relative_to_workspace and not safe_path.is_absolute():
            safe_path = self.workspace_root / safe_path
        
        # Resolve to get canonical path
        try:
            resolved_path = safe_path.resolve()
        except (OSError, ValueError) as e:
            raise PathValidationError(f"Cannot resolve path: {str(e)}")
        
        # Final boundary check
        if not self._is_within_workspace(resolved_path):
            raise PathValidationError(f"Path outside workspace: {resolved_path}")
        
        return resolved_path
    
    def _check_traversal_patterns(self, path: str) -> ValidationResult:
        """Check for path traversal patterns."""
        errors = []
        
        for pattern in self.TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                errors.append(f"Path contains traversal pattern: {pattern}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    def _check_path_boundaries(self, path: Path, allow_creation: bool) -> ValidationResult:
        """Check if path stays within workspace boundaries."""
        errors = []
        warnings = []
        
        try:
            # Handle relative paths
            if not path.is_absolute():
                full_path = self.workspace_root / path
            else:
                full_path = path
            
            # Resolve to get canonical path
            try:
                resolved_path = full_path.resolve()
            except (OSError, ValueError) as e:
                errors.append(f"Cannot resolve path: {str(e)}")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Check if within workspace
            if not self._is_within_workspace(resolved_path):
                errors.append(f"Path outside workspace boundaries: {resolved_path}")
                return ValidationResult(is_valid=False, errors=errors)
            
            # Check if path exists (if required)
            if not allow_creation and not resolved_path.exists():
                errors.append(f"Path does not exist: {resolved_path}")
            
            # Check if parent directory exists for creation
            if allow_creation and not resolved_path.exists():
                parent = resolved_path.parent
                if not parent.exists():
                    warnings.append(f"Parent directory does not exist: {parent}")
        
        except Exception as e:
            errors.append(f"Error checking path boundaries: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _check_path_components(self, path: Path) -> ValidationResult:
        """Check individual path components for validity."""
        errors = []
        warnings = []
        
        for component in path.parts:
            # Check component length
            if len(component) > self.max_component_length:
                errors.append(f"Path component too long: {component}")
            
            # Check for dangerous components
            if component.lower() in self.RESTRICTED_DIRS:
                if self.security_level == SecurityLevel.STRICT:
                    errors.append(f"Restricted directory name: {component}")
                else:
                    warnings.append(f"Potentially restricted directory: {component}")
            
            # Check for hidden files/directories (starting with .)
            if component.startswith('.') and len(component) > 1:
                if self.security_level == SecurityLevel.STRICT:
                    warnings.append(f"Hidden file/directory: {component}")
            
            # Check for Windows reserved names
            reserved_names = {
                'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4',
                'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2',
                'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
            }
            if component.lower().split('.')[0] in reserved_names:
                errors.append(f"Reserved system name: {component}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _check_file_extension(self, extension: str) -> ValidationResult:
        """Check file extension for security."""
        errors = []
        warnings = []
        
        ext_lower = extension.lower()
        
        # Check against allowed extensions first (if specified)
        if self.allowed_extensions and ext_lower not in self.allowed_extensions:
            errors.append(f"File extension not allowed: {extension}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Check against dangerous extensions
        if ext_lower in self.DANGEROUS_EXTENSIONS:
            if self.security_level == SecurityLevel.STRICT:
                errors.append(f"Dangerous file extension: {extension}")
            else:
                warnings.append(f"Potentially dangerous extension: {extension}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _apply_security_level_checks(self, path: Path) -> ValidationResult:
        """Apply security level specific checks."""
        errors = []
        warnings = []
        
        if self.security_level == SecurityLevel.STRICT:
            # Strict mode: additional restrictions
            path_str = str(path)
            
            # No spaces in paths
            if ' ' in path_str:
                warnings.append("Path contains spaces (not recommended in strict mode)")
            
            # Only allow specific characters
            if not re.match(r'^[a-zA-Z0-9._/-]+$', path_str):
                warnings.append("Path contains non-standard characters")
            
            # Check for hidden files/directories (starting with .)
            for component in path.parts:
                if component.startswith('.') and len(component) > 1:
                    warnings.append(f"Hidden file/directory: {component}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _is_within_workspace(self, path: Path) -> bool:
        """Check if a resolved path is within the workspace."""
        try:
            # Both paths should be resolved
            workspace_resolved = self.workspace_root.resolve()
            path_resolved = path.resolve()
            
            # Check if path is under workspace
            try:
                path_resolved.relative_to(workspace_resolved)
                return True
            except ValueError:
                return False
        except (OSError, ValueError):
            return False
    
    def _decode_url_encoding(self, path: str) -> str:
        """Decode URL encoding in path."""
        import urllib.parse
        
        try:
            # Decode multiple times to handle double encoding
            decoded = path
            for _ in range(3):  # Max 3 iterations to prevent infinite loops
                new_decoded = urllib.parse.unquote(decoded)
                if new_decoded == decoded:
                    break
                decoded = new_decoded
            return decoded
        except Exception:
            # If decoding fails, return original
            return path