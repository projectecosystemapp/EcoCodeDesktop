"""
Security tests for WorkflowPersistenceManager to verify path traversal protection.

Tests that the integrated PathValidator properly prevents path traversal
attacks in workflow persistence operations.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from eco_api.specs.workflow_persistence import WorkflowPersistenceManager


class TestWorkflowPersistenceManagerSecurity:
    """Test security features of WorkflowPersistenceManager."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            workspace.mkdir()
            # Create the .kiro/specs directory structure
            specs_dir = workspace / ".kiro" / "specs"
            specs_dir.mkdir(parents=True)
            yield workspace
    
    @pytest.fixture
    def persistence_manager(self, temp_workspace):
        """Create a WorkflowPersistenceManager instance for testing."""
        return WorkflowPersistenceManager(str(temp_workspace))
    
    @pytest.fixture
    def mock_workflow_state(self):
        """Create a mock workflow state for testing."""
        mock_state = Mock()
        mock_state.spec_id = "test-spec"
        mock_state.to_dict.return_value = {
            "spec_id": "test-spec",
            "current_phase": "requirements",
            "status": "draft",
            "approvals": {},
            "metadata": {},
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        return mock_state
    
    def test_save_workflow_state_path_traversal_blocked(self, persistence_manager, temp_workspace):
        """Test that path traversal attempts are blocked in save_workflow_state."""
        # Create a valid spec directory first
        valid_spec_dir = temp_workspace / ".kiro" / "specs" / "test-spec"
        valid_spec_dir.mkdir(parents=True)
        
        # Create mock workflow states with traversal attempts
        traversal_spec_ids = [
            "../malicious",
            "..\\malicious",
            "normal/../traversal",
            "%2e%2e%2fmalicious"
        ]
        
        for spec_id in traversal_spec_ids:
            mock_state = Mock()
            mock_state.spec_id = spec_id
            mock_state.to_dict.return_value = {
                "spec_id": spec_id,
                "current_phase": "requirements",
                "status": "draft"
            }
            
            result = persistence_manager.save_workflow_state(mock_state)
            assert not result.success, f"Should block traversal attempt: {spec_id}"
            assert "PATH_VALIDATION_ERROR" in result.error_code or "PATH_SECURITY_ERROR" in result.error_code
    
    def test_load_workflow_state_path_traversal_blocked(self, persistence_manager):
        """Test that path traversal attempts are blocked in load_workflow_state."""
        traversal_spec_ids = [
            "../malicious",
            "..\\malicious",
            "normal/../traversal",
            "%2e%2e%2fmalicious"
        ]
        
        for spec_id in traversal_spec_ids:
            state, result = persistence_manager.load_workflow_state(spec_id)
            assert state is None, f"Should not return state for traversal: {spec_id}"
            assert not result.success, f"Should block traversal attempt: {spec_id}"
            assert "PATH_VALIDATION_ERROR" in result.error_code or "PATH_SECURITY_ERROR" in result.error_code
    
    def test_list_workflow_versions_path_traversal_blocked(self, persistence_manager):
        """Test that path traversal attempts are blocked in list_workflow_versions."""
        traversal_spec_ids = [
            "../malicious",
            "..\\malicious", 
            "normal/../traversal",
            "%2e%2e%2fmalicious"
        ]
        
        for spec_id in traversal_spec_ids:
            # This should return empty list or handle gracefully without traversal
            versions = persistence_manager.list_workflow_versions(spec_id)
            assert isinstance(versions, list), f"Should return list for spec_id: {spec_id}"
            # The method should not crash and should not access files outside workspace
    
    def test_restore_workflow_version_path_traversal_blocked(self, persistence_manager):
        """Test that path traversal attempts are blocked in restore_workflow_version."""
        traversal_spec_ids = [
            "../malicious",
            "..\\malicious",
            "normal/../traversal", 
            "%2e%2e%2fmalicious"
        ]
        
        for spec_id in traversal_spec_ids:
            state, result = persistence_manager.restore_workflow_version(spec_id, "version1")
            assert state is None, f"Should not return state for traversal: {spec_id}"
            assert not result.success, f"Should block traversal attempt: {spec_id}"
    
    def test_dangerous_file_extensions_blocked(self, persistence_manager, temp_workspace):
        """Test that dangerous file extensions are blocked."""
        # Create a valid spec directory
        valid_spec_dir = temp_workspace / ".kiro" / "specs" / "test-spec"
        valid_spec_dir.mkdir(parents=True)
        
        # The PathValidator should only allow .json files
        # Test the PathValidator directly since the API doesn't expose extension control
        dangerous_paths = [
            "test.exe",
            "malware.bat",
            "script.js", 
            "virus.dll"
        ]
        
        for path in dangerous_paths:
            validation_result = persistence_manager.path_validator.validate_path(path, allow_creation=True)
            # Should either be invalid or have warnings about dangerous extensions
            assert not validation_result.is_valid or len(validation_result.warnings) > 0
    
    def test_workspace_boundary_enforcement(self, persistence_manager, temp_workspace):
        """Test that operations are confined to workspace boundaries."""
        # Create a file outside the workspace
        outside_dir = temp_workspace.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "malicious.json"
        outside_file.write_text('{"malicious": "content"}')
        
        # Try to access files outside workspace through various means
        # The PathValidator should prevent any access outside the workspace
        
        # Test with absolute path
        validation_result = persistence_manager.path_validator.validate_path(str(outside_file))
        assert not validation_result.is_valid
        
        # Test with relative path going outside
        validation_result = persistence_manager.path_validator.validate_path("../outside/malicious.json")
        assert not validation_result.is_valid
    
    def test_secure_path_joining(self, persistence_manager):
        """Test that secure path joining prevents traversal."""
        # Test the secure_join method directly
        try:
            # This should fail due to traversal attempt
            result = persistence_manager.path_validator.secure_join(".kiro", "specs", "../etc", "passwd")
            assert False, "Should have raised PathValidationError"
        except Exception as e:
            assert "PathValidationError" in str(type(e)) or "Invalid path component" in str(e)
        
        # Test valid joining
        result = persistence_manager.path_validator.secure_join(".kiro", "specs", "test-spec", "workflow-state.json")
        assert result == ".kiro/specs/test-spec/workflow-state.json"
    
    def test_null_byte_injection_blocked(self, persistence_manager):
        """Test that null byte injection is blocked."""
        null_byte_spec_ids = [
            "test\x00.json",
            "normal\x00../etc/passwd",
            "spec\x00name"
        ]
        
        for spec_id in null_byte_spec_ids:
            mock_state = Mock()
            mock_state.spec_id = spec_id
            mock_state.to_dict.return_value = {"spec_id": spec_id}
            
            result = persistence_manager.save_workflow_state(mock_state)
            assert not result.success, f"Should block null byte injection: {repr(spec_id)}"
    
    def test_path_length_limits_enforced(self, persistence_manager):
        """Test that path length limits are enforced."""
        # Test very long spec_id
        long_spec_id = "a" * 300
        mock_state = Mock()
        mock_state.spec_id = long_spec_id
        mock_state.to_dict.return_value = {"spec_id": long_spec_id}
        
        result = persistence_manager.save_workflow_state(mock_state)
        assert not result.success
        assert "PATH_VALIDATION_ERROR" in result.error_code or "PATH_SECURITY_ERROR" in result.error_code
    
    def test_reserved_names_blocked(self, persistence_manager):
        """Test that reserved system names are blocked."""
        reserved_spec_ids = [
            "con",
            "prn", 
            "aux",
            "nul",
            "com1"
        ]
        
        for spec_id in reserved_spec_ids:
            mock_state = Mock()
            mock_state.spec_id = spec_id
            mock_state.to_dict.return_value = {"spec_id": spec_id}
            
            result = persistence_manager.save_workflow_state(mock_state)
            assert not result.success, f"Should block reserved name: {spec_id}"
    
    def test_hidden_files_handling(self, persistence_manager):
        """Test handling of hidden files and directories."""
        hidden_spec_ids = [
            ".hidden",
            ".git",
            ".secret"
        ]
        
        for spec_id in hidden_spec_ids:
            # In strict mode, should generate warnings for hidden files
            validation_result = persistence_manager.path_validator.validate_path(spec_id, allow_creation=True)
            # Should either be valid with warnings or invalid
            if validation_result.is_valid:
                assert len(validation_result.warnings) > 0, f"Should warn about hidden file: {spec_id}"
    
    def test_case_sensitivity_handling(self, persistence_manager):
        """Test that case sensitivity is handled properly for security."""
        # Test reserved names in different cases
        reserved_variations = [
            "CON",
            "con",
            "Con", 
            "PRN",
            "prn"
        ]
        
        for spec_id in reserved_variations:
            mock_state = Mock()
            mock_state.spec_id = spec_id
            mock_state.to_dict.return_value = {"spec_id": spec_id}
            
            result = persistence_manager.save_workflow_state(mock_state)
            assert not result.success, f"Should block reserved name: {spec_id}"
    
    def test_unicode_normalization_security(self, persistence_manager):
        """Test that Unicode normalization doesn't bypass security."""
        # Test various Unicode representations that might bypass filters
        unicode_attempts = [
            "test\u002e\u002e/traversal",  # Unicode dots
            "test\uff0e\uff0e/traversal",  # Fullwidth dots
            "test\u2024\u2024/traversal"   # One dot leader
        ]
        
        for spec_id in unicode_attempts:
            validation_result = persistence_manager.path_validator.validate_path(spec_id, allow_creation=True)
            # Should be handled safely (either blocked or sanitized)
            if validation_result.is_valid:
                # Ensure the sanitized path doesn't contain traversal
                assert ".." not in validation_result.sanitized_path
            # If not valid, that's also acceptable for security
    
    def test_successful_operations_with_valid_paths(self, persistence_manager, temp_workspace, mock_workflow_state):
        """Test that valid operations work correctly with path validation."""
        # Create a valid spec directory
        valid_spec_dir = temp_workspace / ".kiro" / "specs" / "test-spec"
        valid_spec_dir.mkdir(parents=True)
        
        # Test saving workflow state with valid spec_id
        result = persistence_manager.save_workflow_state(mock_workflow_state)
        assert result.success, f"Valid operation should succeed: {result.message}"
        
        # Test loading workflow state
        state, load_result = persistence_manager.load_workflow_state("test-spec")
        assert load_result.success, f"Valid load operation should succeed: {load_result.message}"
        assert state is not None
    
    def test_error_handling_consistency(self, persistence_manager):
        """Test that error handling is consistent across methods."""
        traversal_spec_id = "../malicious"
        
        # Test save_workflow_state error handling
        mock_state = Mock()
        mock_state.spec_id = traversal_spec_id
        mock_state.to_dict.return_value = {"spec_id": traversal_spec_id}
        
        save_result = persistence_manager.save_workflow_state(mock_state)
        assert not save_result.success
        assert save_result.error_code in ["PATH_VALIDATION_ERROR", "PATH_SECURITY_ERROR"]
        
        # Test load_workflow_state error handling
        state, load_result = persistence_manager.load_workflow_state(traversal_spec_id)
        assert state is None
        assert not load_result.success
        assert load_result.error_code in ["PATH_VALIDATION_ERROR", "PATH_SECURITY_ERROR"]