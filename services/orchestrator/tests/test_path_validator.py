"""
Tests for PathValidator utility class.

Tests comprehensive path validation functionality including
traversal attack prevention, boundary checking, and sanitization.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from eco_api.security.path_validator import (
    PathValidator, PathValidationError, SecurityLevel, ValidationResult
)


class TestPathValidator:
    """Test cases for PathValidator class."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            yield workspace
    
    @pytest.fixture
    def validator(self, temp_workspace):
        """Create a PathValidator instance for testing."""
        return PathValidator(temp_workspace)
    
    def test_init_valid_workspace(self, temp_workspace):
        """Test PathValidator initialization with valid workspace."""
        validator = PathValidator(temp_workspace)
        assert validator.workspace_root == temp_workspace.resolve()
        assert validator.security_level == SecurityLevel.STRICT
    
    def test_init_nonexistent_workspace(self):
        """Test PathValidator initialization with nonexistent workspace."""
        with pytest.raises(PathValidationError, match="Workspace root does not exist"):
            PathValidator("/nonexistent/path")
    
    def test_init_file_as_workspace(self, temp_workspace):
        """Test PathValidator initialization with file as workspace."""
        file_path = temp_workspace / "file.txt"
        file_path.write_text("test")
        
        with pytest.raises(PathValidationError, match="Workspace root is not a directory"):
            PathValidator(file_path)
    
    def test_validate_empty_path(self, validator):
        """Test validation of empty path."""
        result = validator.validate_path("")
        assert not result.is_valid
        assert "Path cannot be empty" in result.errors
    
    def test_validate_null_bytes(self, validator):
        """Test validation of path with null bytes."""
        result = validator.validate_path("test\x00file.txt")
        assert not result.is_valid
        assert "Path contains null bytes" in result.errors
    
    def test_validate_long_path(self, validator):
        """Test validation of excessively long path."""
        long_path = "a" * 300
        result = validator.validate_path(long_path)
        assert not result.is_valid
        assert "Path too long" in result.errors[0]
    
    def test_validate_traversal_patterns(self, validator):
        """Test detection of path traversal patterns."""
        traversal_paths = [
            "../etc/passwd",
            "..\\windows\\system32",
            "test/../../../etc/passwd",
            "%2e%2e%2f",
            "%2e%2e%5c",
            "...//etc/passwd"
        ]
        
        for path in traversal_paths:
            result = validator.validate_path(path)
            assert not result.is_valid, f"Should reject traversal path: {path}"
    
    def test_validate_valid_paths(self, validator, temp_workspace):
        """Test validation of valid paths."""
        # Create test files
        test_file = temp_workspace / "test.txt"
        test_file.write_text("test")
        
        test_dir = temp_workspace / "subdir"
        test_dir.mkdir()
        
        valid_paths = [
            "test.txt",
            "subdir",
            "subdir/newfile.txt",
            "./test.txt",
            "valid-file-name.md"
        ]
        
        for path in valid_paths:
            result = validator.validate_path(path, allow_creation=True)
            assert result.is_valid, f"Should accept valid path: {path}, errors: {result.errors}"
    
    def test_sanitize_path_basic(self, validator):
        """Test basic path sanitization."""
        test_cases = [
            ("normal/path.txt", "normal/path.txt"),
            ("path\\with\\backslashes", "path/with/backslashes"),
            ("path/../traversal", "path/traversal"),
            ("path//double//slashes", "path/double/slashes"),
            ("  /leading/trailing/  ", "leading/trailing"),
        ]
        
        for input_path, expected in test_cases:
            result = validator.sanitize_path(input_path)
            assert result == expected, f"Sanitization failed for {input_path}"
    
    def test_sanitize_path_url_encoding(self, validator):
        """Test sanitization of URL encoded paths."""
        test_cases = [
            ("%2e%2e%2f", ""),  # ../
            ("test%2ffile.txt", "test/file.txt"),
            ("%252e%252e%252f", ""),  # Double encoded ../
        ]
        
        for input_path, expected in test_cases:
            result = validator.sanitize_path(input_path)
            assert result == expected, f"URL decoding failed for {input_path}"
    
    def test_sanitize_path_security_levels(self, temp_workspace):
        """Test sanitization with different security levels."""
        strict_validator = PathValidator(temp_workspace, SecurityLevel.STRICT)
        moderate_validator = PathValidator(temp_workspace, SecurityLevel.MODERATE)
        
        test_path = "file with spaces & symbols!.txt"
        
        strict_result = strict_validator.sanitize_path(test_path)
        moderate_result = moderate_validator.sanitize_path(test_path)
        
        # Strict should remove more characters
        assert len(strict_result) <= len(moderate_result)
        assert " " not in strict_result  # Spaces removed in strict mode
    
    def test_secure_join_valid(self, validator):
        """Test secure path joining with valid components."""
        result = validator.secure_join("dir1", "dir2", "file.txt")
        assert result == "dir1/dir2/file.txt"
    
    def test_secure_join_traversal_attempt(self, validator):
        """Test secure path joining rejects traversal attempts."""
        with pytest.raises(PathValidationError):
            validator.secure_join("dir1", "../etc", "passwd")
        
        with pytest.raises(PathValidationError):
            validator.secure_join("dir1", "/absolute/path", "file.txt")
    
    def test_secure_join_empty_parts(self, validator):
        """Test secure path joining with empty parts."""
        result = validator.secure_join("dir1", "", "file.txt", "")
        assert result == "dir1/file.txt"
    
    def test_secure_join_no_parts(self, validator):
        """Test secure path joining with no parts."""
        with pytest.raises(PathValidationError, match="No path parts provided"):
            validator.secure_join()
    
    def test_is_path_traversal_attempt(self, validator):
        """Test traversal attempt detection."""
        traversal_paths = [
            "../etc/passwd",
            "..\\windows",
            "test/../../../root",
            "%2e%2e%2f",
            "normal/../path"
        ]
        
        safe_paths = [
            "normal/path.txt",
            "file.txt",
            "dir/subdir/file.txt"
        ]
        
        for path in traversal_paths:
            assert validator.is_path_traversal_attempt(path), f"Should detect traversal: {path}"
        
        for path in safe_paths:
            assert not validator.is_path_traversal_attempt(path), f"Should not detect traversal: {path}"
    
    def test_get_safe_path_valid(self, validator, temp_workspace):
        """Test getting safe path for valid input."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("test")
        
        safe_path = validator.get_safe_path("test.txt")
        assert safe_path == test_file.resolve()
        assert safe_path.is_absolute()
    
    def test_get_safe_path_invalid(self, validator):
        """Test getting safe path for invalid input."""
        with pytest.raises(PathValidationError):
            validator.get_safe_path("../etc/passwd")
    
    def test_get_safe_path_outside_workspace(self, validator, temp_workspace):
        """Test getting safe path for path outside workspace."""
        # Test with a relative path that goes outside workspace
        with pytest.raises(PathValidationError, match="Invalid path"):
            validator.get_safe_path("../outside.txt")
    
    def test_boundary_checking(self, validator, temp_workspace):
        """Test workspace boundary checking."""
        # Valid paths within workspace
        valid_paths = [
            "file.txt",
            "subdir/file.txt",
            "./file.txt"
        ]
        
        for path in valid_paths:
            result = validator.validate_path(path, allow_creation=True)
            assert result.is_valid, f"Should accept path within workspace: {path}"
        
        # Invalid paths outside workspace
        invalid_paths = [
            "../outside.txt",
            "/absolute/path.txt",
            str(temp_workspace.parent / "outside.txt")
        ]
        
        for path in invalid_paths:
            result = validator.validate_path(path)
            assert not result.is_valid, f"Should reject path outside workspace: {path}"
    
    def test_file_extension_validation(self, temp_workspace):
        """Test file extension validation."""
        # Test with allowed extensions
        validator = PathValidator(
            temp_workspace,
            allowed_extensions=['.txt', '.md', '.json']
        )
        
        result = validator.validate_path("file.txt", allow_creation=True)
        assert result.is_valid
        
        result = validator.validate_path("file.exe", allow_creation=True)
        assert not result.is_valid
        assert "File extension not allowed" in result.errors[0]
    
    def test_dangerous_extensions(self, validator):
        """Test detection of dangerous file extensions."""
        dangerous_files = [
            "malware.exe",
            "script.bat",
            "virus.scr",
            "trojan.dll"
        ]
        
        for file_path in dangerous_files:
            result = validator.validate_path(file_path, allow_creation=True)
            # In strict mode, should reject or warn about dangerous extensions
            assert not result.is_valid or len(result.warnings) > 0
    
    def test_reserved_names(self, validator):
        """Test detection of reserved system names."""
        reserved_names = [
            "con.txt",
            "prn.log",
            "aux.dat",
            "nul.tmp",
            "com1.txt",
            "lpt1.log"
        ]
        
        for name in reserved_names:
            result = validator.validate_path(name, allow_creation=True)
            assert not result.is_valid, f"Should reject reserved name: {name}"
            assert "Reserved system name" in result.errors[0]
    
    def test_path_component_length(self, temp_workspace):
        """Test path component length validation."""
        validator = PathValidator(temp_workspace, max_component_length=10)
        
        # Valid component length
        result = validator.validate_path("short.txt", allow_creation=True)
        assert result.is_valid
        
        # Invalid component length
        long_component = "a" * 15 + ".txt"
        result = validator.validate_path(long_component, allow_creation=True)
        assert not result.is_valid
        assert "Path component too long" in result.errors[0]
    
    def test_security_levels(self, temp_workspace):
        """Test different security levels."""
        test_path = "file with spaces & symbols.txt"
        
        # Strict mode
        strict_validator = PathValidator(temp_workspace, SecurityLevel.STRICT)
        strict_result = strict_validator.validate_path(test_path, allow_creation=True)
        
        # Moderate mode
        moderate_validator = PathValidator(temp_workspace, SecurityLevel.MODERATE)
        moderate_result = moderate_validator.validate_path(test_path, allow_creation=True)
        
        # Permissive mode
        permissive_validator = PathValidator(temp_workspace, SecurityLevel.PERMISSIVE)
        permissive_result = permissive_validator.validate_path(test_path, allow_creation=True)
        
        # Strict should be most restrictive
        if not strict_result.is_valid:
            # If strict rejects, moderate might accept with warnings
            assert len(moderate_result.warnings) >= len(strict_result.warnings)
    
    def test_hidden_files(self, validator):
        """Test handling of hidden files and directories."""
        hidden_paths = [
            ".hidden",
            ".git/config",
            "dir/.hidden_file.txt"
        ]
        
        for path in hidden_paths:
            result = validator.validate_path(path, allow_creation=True)
            # Should at least generate warnings for hidden files in strict mode
            if validator.security_level == SecurityLevel.STRICT:
                assert len(result.warnings) > 0 or not result.is_valid
    
    def test_restricted_directories(self, validator):
        """Test detection of restricted directory names."""
        restricted_paths = [
            "system32/file.txt",
            "etc/passwd",
            "windows/system.ini",
            "root/.bashrc"
        ]
        
        for path in restricted_paths:
            result = validator.validate_path(path, allow_creation=True)
            # Should reject or warn about restricted directories
            assert not result.is_valid or len(result.warnings) > 0
    
    def test_validation_result_structure(self, validator):
        """Test ValidationResult structure and content."""
        # Valid path
        result = validator.validate_path("valid.txt", allow_creation=True)
        assert isinstance(result, ValidationResult)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        
        if result.is_valid:
            assert result.sanitized_path is not None
        
        # Invalid path
        result = validator.validate_path("../invalid")
        assert not result.is_valid
        assert len(result.errors) > 0
        assert result.sanitized_path is None
    
    def test_edge_cases(self, validator):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            None,  # None input
            "",    # Empty string
            " ",   # Whitespace only
            ".",   # Current directory
            "..",  # Parent directory
            "/",   # Root directory
            "\\",  # Windows root
        ]
        
        for case in edge_cases:
            try:
                result = validator.validate_path(case) if case is not None else None
                if result:
                    # Should either be invalid or handle gracefully
                    assert isinstance(result, ValidationResult)
            except (TypeError, ValueError):
                # Expected for None input
                pass
    
    @patch('urllib.parse.unquote')
    def test_url_decoding_error_handling(self, mock_unquote, validator):
        """Test URL decoding error handling."""
        mock_unquote.side_effect = Exception("Decoding error")
        
        # Should handle decoding errors gracefully
        result = validator.sanitize_path("%2e%2e%2f")
        assert isinstance(result, str)  # Should return something, not crash
    
    def test_concurrent_validation(self, validator, temp_workspace):
        """Test thread safety of path validation."""
        import threading
        import time
        
        results = []
        errors = []
        
        def validate_path_worker(path_suffix):
            try:
                path = f"test_{path_suffix}.txt"
                result = validator.validate_path(path, allow_creation=True)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=validate_path_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Concurrent validation errors: {errors}"
        assert len(results) == 10
        assert all(result.is_valid for result in results)