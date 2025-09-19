"""
Security tests for FileSystemManager to verify path traversal protection.

Tests that the integrated PathValidator properly prevents path traversal
attacks in file operations.
"""

import pytest
import tempfile
from pathlib import Path

from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.models import DocumentType


class TestFileSystemManagerSecurity:
    """Test security features of FileSystemManager."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            yield workspace
    
    @pytest.fixture
    def file_manager(self, temp_workspace):
        """Create a FileSystemManager instance for testing."""
        return FileSystemManager(str(temp_workspace))
    
    def test_create_spec_directory_path_traversal_blocked(self, file_manager):
        """Test that path traversal attempts are blocked in create_spec_directory."""
        traversal_names = [
            "../malicious",
            "..\\malicious",
            "normal/../traversal",
            "%2e%2e%2fmalicious",
            "test/../../etc/passwd"
        ]
        
        for name in traversal_names:
            result = file_manager.create_spec_directory(name)
            assert not result.success, f"Should block traversal attempt: {name}"
            assert "PATH_VALIDATION_ERROR" in result.error_code or "INVALID_FEATURE_NAME" in result.error_code
    
    def test_save_document_path_traversal_blocked(self, file_manager, temp_workspace):
        """Test that path traversal attempts are blocked in save_document."""
        # First create a valid spec directory
        valid_name = "test-spec"
        create_result = file_manager.create_spec_directory(valid_name)
        assert create_result.success
        
        # Try to save documents with traversal attempts
        traversal_names = [
            "../malicious",
            "..\\malicious", 
            "normal/../traversal",
            "%2e%2e%2fmalicious"
        ]
        
        for name in traversal_names:
            result = file_manager.save_document(name, DocumentType.REQUIREMENTS, "# Test content")
            assert not result.success, f"Should block traversal attempt: {name}"
            assert "PATH_VALIDATION_ERROR" in result.error_code or "PATH_SECURITY_ERROR" in result.error_code
    
    def test_load_document_path_traversal_blocked(self, file_manager):
        """Test that path traversal attempts are blocked in load_document."""
        traversal_names = [
            "../malicious",
            "..\\malicious",
            "normal/../traversal", 
            "%2e%2e%2fmalicious"
        ]
        
        for name in traversal_names:
            document, result = file_manager.load_document(name, DocumentType.REQUIREMENTS)
            assert document is None, f"Should not return document for traversal: {name}"
            assert not result.success, f"Should block traversal attempt: {name}"
            assert "PATH_VALIDATION_ERROR" in result.error_code or "PATH_SECURITY_ERROR" in result.error_code
    
    def test_validate_spec_structure_path_traversal_blocked(self, file_manager):
        """Test that path traversal attempts are blocked in validate_spec_structure."""
        traversal_names = [
            "../malicious",
            "..\\malicious",
            "normal/../traversal",
            "%2e%2e%2fmalicious"
        ]
        
        for name in traversal_names:
            result = file_manager.validate_spec_structure(name)
            assert not result.is_valid, f"Should block traversal attempt: {name}"
            assert any("PATH_VALIDATION_ERROR" in error.code or "VALIDATION_ERROR" in error.code for error in result.errors)
    
    def test_dangerous_file_extensions_blocked(self, file_manager, temp_workspace):
        """Test that dangerous file extensions are blocked."""
        # Create a valid spec directory
        valid_name = "test-spec"
        create_result = file_manager.create_spec_directory(valid_name)
        assert create_result.success
        
        # The PathValidator should only allow .md and .json files
        # Try to create files with dangerous extensions by manipulating the document type
        # This tests the extension validation in the PathValidator
        
        # Since we can't directly test with dangerous extensions through the normal API
        # (as DocumentType controls the extension), we test the PathValidator directly
        dangerous_paths = [
            "test.exe",
            "malware.bat", 
            "script.js",
            "virus.dll"
        ]
        
        for path in dangerous_paths:
            validation_result = file_manager.path_validator.validate_path(path, allow_creation=True)
            # Should either be invalid or have warnings about dangerous extensions
            assert not validation_result.is_valid or len(validation_result.warnings) > 0
    
    def test_restricted_directory_names_blocked(self, file_manager):
        """Test that restricted directory names are blocked."""
        restricted_names = [
            "system32",
            "windows", 
            "etc",
            "root",
            "bin"
        ]
        
        for name in restricted_names:
            result = file_manager.create_spec_directory(name)
            # Should either fail validation or generate warnings
            if result.success:
                # Check if PathValidator generated warnings
                validation_result = file_manager.path_validator.validate_path(name, allow_creation=True)
                assert len(validation_result.warnings) > 0 or not validation_result.is_valid
            else:
                assert "PATH_VALIDATION_ERROR" in result.error_code or "INVALID_FEATURE_NAME" in result.error_code or "PATH_SECURITY_ERROR" in result.error_code
    
    def test_path_length_limits_enforced(self, file_manager):
        """Test that path length limits are enforced."""
        # Test very long feature name
        long_name = "a" * 300
        result = file_manager.create_spec_directory(long_name)
        assert not result.success
        assert "PATH_VALIDATION_ERROR" in result.error_code or "INVALID_FEATURE_NAME" in result.error_code
    
    def test_null_byte_injection_blocked(self, file_manager):
        """Test that null byte injection is blocked."""
        null_byte_names = [
            "test\x00.txt",
            "normal\x00../etc/passwd",
            "file\x00name"
        ]
        
        for name in null_byte_names:
            result = file_manager.create_spec_directory(name)
            assert not result.success, f"Should block null byte injection: {repr(name)}"
    
    def test_workspace_boundary_enforcement(self, file_manager, temp_workspace):
        """Test that operations are confined to workspace boundaries."""
        # Create a file outside the workspace
        outside_dir = temp_workspace.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "malicious.txt"
        outside_file.write_text("malicious content")
        
        # Try to access files outside workspace through various means
        # The PathValidator should prevent any access outside the workspace
        
        # Test with absolute path
        validation_result = file_manager.path_validator.validate_path(str(outside_file))
        assert not validation_result.is_valid
        
        # Test with relative path going outside
        validation_result = file_manager.path_validator.validate_path("../outside/malicious.txt")
        assert not validation_result.is_valid
    
    def test_secure_path_joining(self, file_manager):
        """Test that secure path joining prevents traversal."""
        # Test the secure_join method directly
        try:
            # This should fail due to traversal attempt
            result = file_manager.path_validator.secure_join("specs", "../etc", "passwd")
            assert False, "Should have raised PathValidationError"
        except Exception as e:
            assert "PathValidationError" in str(type(e)) or "Invalid path component" in str(e)
        
        # Test valid joining
        result = file_manager.path_validator.secure_join("specs", "test-feature", "requirements.md")
        assert result == "specs/test-feature/requirements.md"
    
    def test_hidden_files_handling(self, file_manager):
        """Test handling of hidden files and directories."""
        hidden_names = [
            ".hidden",
            ".git",
            ".secret"
        ]
        
        for name in hidden_names:
            # In strict mode, should generate warnings for hidden files
            validation_result = file_manager.path_validator.validate_path(name, allow_creation=True)
            # Should either be valid with warnings or invalid
            if validation_result.is_valid:
                assert len(validation_result.warnings) > 0, f"Should warn about hidden file: {name}"
    
    def test_case_sensitivity_handling(self, file_manager):
        """Test that case sensitivity is handled properly for security."""
        # Test reserved names in different cases
        reserved_variations = [
            "CON",
            "con", 
            "Con",
            "PRN",
            "prn"
        ]
        
        for name in reserved_variations:
            result = file_manager.create_spec_directory(name)
            assert not result.success, f"Should block reserved name: {name}"
    
    def test_unicode_normalization_security(self, file_manager):
        """Test that Unicode normalization doesn't bypass security."""
        # Test various Unicode representations that might bypass filters
        unicode_attempts = [
            "test\u002e\u002e/traversal",  # Unicode dots
            "test\uff0e\uff0e/traversal",  # Fullwidth dots
            "test\u2024\u2024/traversal"   # One dot leader
        ]
        
        for attempt in unicode_attempts:
            validation_result = file_manager.path_validator.validate_path(attempt, allow_creation=True)
            # Should be handled safely (either blocked or sanitized)
            if validation_result.is_valid:
                # Ensure the sanitized path doesn't contain traversal
                assert ".." not in validation_result.sanitized_path
            # If not valid, that's also acceptable for security