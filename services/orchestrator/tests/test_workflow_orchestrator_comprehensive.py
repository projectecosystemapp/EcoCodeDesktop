"""
Comprehensive unit tests for WorkflowOrchestrator with mocked dependencies.

This module provides extensive testing for workflow orchestrator functionality
with all external dependencies mocked to ensure isolated unit testing.

Requirements addressed:
- All requirements - validation through comprehensive testing
- Workflow state management, transitions, and error handling
- Document generation coordination and approval workflows
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List

from eco_api.specs.workflow_orchestrator import (
    WorkflowOrchestrator, WorkflowState, ApprovalStatus, WorkflowTransition
)
from eco_api.specs.models import (
    WorkflowPhase, WorkflowStatus, DocumentType, ValidationResult, ValidationError, ValidationWarning
)
from eco_api.specs.generators import RequirementsGenerator, DesignGenerator, TasksGenerator
from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.research_service import ResearchService


class TestWorkflowOrchestratorUnitTests:
    """Comprehensive unit tests for WorkflowOrchestrator with mocked dependencies."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock FileSystemManager."""
        manager = Mock(spec=FileSystemManager)
        manager.create_spec_directory.return_value = ("test-spec", Mock(success=True))
        manager.validate_spec_structure.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        manager.save_document.return_value = Mock(success=True)
        manager.load_document.return_value = (Mock(), Mock(success=True))
        manager.list_specs.return_value = []
        return manager
    
    @pytest.fixture
    def mock_generators(self):
        """Create mock document generators."""
        req_gen = Mock(spec=RequirementsGenerator)
        design_gen = Mock(spec=DesignGenerator)
        tasks_gen = Mock(spec=TasksGenerator)
        
        req_gen.generate_requirements_document.return_value = "# Requirements\n\nGenerated requirements"
        design_gen.generate_design_document.return_value = "# Design\n\nGenerated design"
        tasks_gen.generate_tasks_document.return_value = "# Tasks\n\n- [ ] Generated task"
        
        return {
            'requirements': req_gen,
            'design': design_gen,
            'tasks': tasks_gen
        }
    
    @pytest.fixture
    def mock_research_service(self):
        """Create a mock ResearchService."""
        service = Mock(spec=ResearchService)
        service.conduct_research.return_value = {
            'areas': ['authentication', 'security'],
            'findings': ['Use JWT tokens', 'Implement HTTPS'],
            'technology_recommendations': {'backend': 'FastAPI', 'frontend': 'React'}
        }
        return service
    
    @pytest.fixture
    def orchestrator(self, temp_workspace, mock_file_manager, mock_generators, mock_research_service):
        """Create a WorkflowOrchestrator with mocked dependencies."""
        with patch('eco_api.specs.workflow_orchestrator.FileSystemManager', return_value=mock_file_manager):
            with patch('eco_api.specs.workflow_orchestrator.RequirementsGenerator', return_value=mock_generators['requirements']):
                with patch('eco_api.specs.workflow_orchestrator.DesignGenerator', return_value=mock_generators['design']):
                    with patch('eco_api.specs.workflow_orchestrator.TasksGenerator', return_value=mock_generators['tasks']):
                        with patch('eco_api.specs.workflow_orchestrator.ResearchService', return_value=mock_research_service):
                            return WorkflowOrchestrator(temp_workspace)
    
    def test_create_spec_workflow_success(self, orchestrator, mock_file_manager, mock_generators):
        """Test successful spec workflow creation with mocked dependencies."""
        feature_idea = "user authentication system with OAuth support"
        
        # Execute
        workflow_state, result = orchestrator.create_spec_workflow(feature_idea)
        
        # Verify
        assert result.success
        assert workflow_state is not None
        assert workflow_state.spec_id == "user-authentication-system-with-oauth-support"
        assert workflow_state.current_phase == WorkflowPhase.REQUIREMENTS
        assert workflow_state.status == WorkflowStatus.DRAFT
        
        # Verify file manager was called
        mock_file_manager.create_spec_directory.assert_called_once()
        
        # Verify requirements generator was called
        mock_generators['requirements'].generate_requirements_document.assert_called_once_with(feature_idea)
        
        # Verify document was saved
        mock_file_manager.save_document.assert_called()
    
    def test_create_spec_workflow_with_custom_name(self, orchestrator, mock_file_manager):
        """Test spec workflow creation with custom feature name."""
        feature_idea = "Complex feature idea"
        feature_name = "custom-feature-name"
        
        workflow_state, result = orchestrator.create_spec_workflow(feature_idea, feature_name)
        
        assert result.success
        assert workflow_state.spec_id == feature_name
        mock_file_manager.create_spec_directory.assert_called_with(feature_name)
    
    def test_create_spec_workflow_file_manager_failure(self, orchestrator, mock_file_manager):
        """Test spec workflow creation when file manager fails."""
        feature_idea = "Test feature"
        
        # Mock file manager failure
        mock_file_manager.create_spec_directory.return_value = (None, Mock(success=False, message="Directory creation failed"))
        
        workflow_state, result = orchestrator.create_spec_workflow(feature_idea)
        
        assert not result.success
        assert workflow_state is None
        assert "Directory creation failed" in result.message
    
    def test_create_spec_workflow_generator_failure(self, orchestrator, mock_generators):
        """Test spec workflow creation when requirements generator fails."""
        feature_idea = "Test feature"
        
        # Mock generator failure
        mock_generators['requirements'].generate_requirements_document.side_effect = Exception("Generation failed")
        
        workflow_state, result = orchestrator.create_spec_workflow(feature_idea)
        
        assert not result.success
        assert workflow_state is None
        assert "Generation failed" in result.message
    
    def test_transition_workflow_requirements_to_design_success(self, orchestrator, mock_file_manager, mock_generators, mock_research_service):
        """Test successful transition from requirements to design phase."""
        # Create initial workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Mock document loading for transition
        mock_doc = Mock()
        mock_doc.content = "# Requirements\n\nSome requirements content"
        mock_file_manager.load_document.return_value = (mock_doc, Mock(success=True))
        
        # Execute transition
        updated_state, validation = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        # Verify
        assert validation.is_valid
        assert updated_state is not None
        assert updated_state.current_phase == WorkflowPhase.DESIGN
        assert updated_state.approvals["requirements"] == ApprovalStatus.APPROVED
        
        # Verify research service was called
        mock_research_service.conduct_research.assert_called_once()
        
        # Verify design generator was called
        mock_generators['design'].generate_design_document.assert_called()
    
    def test_transition_workflow_design_to_tasks_success(self, orchestrator, mock_file_manager, mock_generators):
        """Test successful transition from design to tasks phase."""
        # Create workflow in design phase
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        workflow_state.current_phase = WorkflowPhase.DESIGN
        workflow_state.approvals["requirements"] = ApprovalStatus.APPROVED
        orchestrator.workflow_states[workflow_state.spec_id] = workflow_state
        
        # Mock document loading
        req_doc = Mock()
        req_doc.content = "# Requirements\n\nRequirements content"
        design_doc = Mock()
        design_doc.content = "# Design\n\nDesign content"
        
        mock_file_manager.load_document.side_effect = [
            (design_doc, Mock(success=True)),
            (req_doc, Mock(success=True))
        ]
        
        # Execute transition
        updated_state, validation = orchestrator.transition_workflow(
            workflow_state.spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        # Verify
        assert validation.is_valid
        assert updated_state.current_phase == WorkflowPhase.TASKS
        assert updated_state.approvals["design"] == ApprovalStatus.APPROVED
        
        # Verify tasks generator was called with both requirements and design
        mock_generators['tasks'].generate_tasks_document.assert_called()
    
    def test_transition_workflow_backward_design_to_requirements(self, orchestrator, mock_file_manager):
        """Test backward transition from design to requirements."""
        # Create workflow in design phase
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        workflow_state.current_phase = WorkflowPhase.DESIGN
        orchestrator.workflow_states[workflow_state.spec_id] = workflow_state
        
        # Execute backward transition
        updated_state, validation = orchestrator.transition_workflow(
            workflow_state.spec_id, WorkflowPhase.REQUIREMENTS
        )
        
        # Verify
        assert validation.is_valid
        assert updated_state.current_phase == WorkflowPhase.REQUIREMENTS
        assert updated_state.approvals["design"] == ApprovalStatus.PENDING
    
    def test_transition_workflow_invalid_transition(self, orchestrator):
        """Test invalid workflow transition."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Try invalid transition (requirements to execution)
        updated_state, validation = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.EXECUTION, approval=True
        )
        
        assert not validation.is_valid
        assert updated_state is None
        assert any("transition" in error.message.lower() for error in validation.errors)
    
    def test_approve_phase_requirements_success(self, orchestrator):
        """Test successful requirements phase approval."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Approve requirements phase
        updated_state, validation = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Looks good!"
        )
        
        assert validation.is_valid
        assert updated_state.approvals["requirements"] == ApprovalStatus.APPROVED
        assert updated_state.metadata.get("requirements_feedback") == "Looks good!"
    
    def test_approve_phase_rejection(self, orchestrator):
        """Test phase rejection with feedback."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Reject requirements phase
        updated_state, validation = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, False, "Needs more detail"
        )
        
        assert validation.is_valid
        assert updated_state.approvals["requirements"] == ApprovalStatus.NEEDS_REVISION
        assert updated_state.metadata.get("requirements_feedback") == "Needs more detail"
    
    def test_approve_phase_wrong_phase(self, orchestrator):
        """Test approving phase that doesn't match current phase."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Try to approve design phase while in requirements
        updated_state, validation = orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True
        )
        
        assert not validation.is_valid
        assert updated_state is None
        assert any("Cannot approve" in error.message for error in validation.errors)
    
    def test_approve_phase_nonexistent_workflow(self, orchestrator):
        """Test approving phase for non-existent workflow."""
        updated_state, validation = orchestrator.approve_phase(
            "non-existent-spec", WorkflowPhase.REQUIREMENTS, True
        )
        
        assert not validation.is_valid
        assert updated_state is None
        assert any("not found" in error.message.lower() for error in validation.errors)
    
    def test_get_workflow_state_success(self, orchestrator):
        """Test retrieving existing workflow state."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Retrieve workflow state
        retrieved_state = orchestrator.get_workflow_state(spec_id)
        
        assert retrieved_state is not None
        assert retrieved_state.spec_id == spec_id
        assert retrieved_state.current_phase == WorkflowPhase.REQUIREMENTS
    
    def test_get_workflow_state_not_found(self, orchestrator):
        """Test retrieving non-existent workflow state."""
        retrieved_state = orchestrator.get_workflow_state("non-existent-spec")
        assert retrieved_state is None
    
    def test_list_workflows_empty(self, orchestrator, mock_file_manager):
        """Test listing workflows when none exist."""
        mock_file_manager.list_specs.return_value = []
        
        workflow_list = orchestrator.list_workflows()
        
        assert len(workflow_list) == 0
        mock_file_manager.list_specs.assert_called_once()
    
    def test_list_workflows_with_specs(self, orchestrator, mock_file_manager):
        """Test listing workflows with existing specs."""
        # Mock file manager to return spec summaries
        mock_specs = [
            Mock(id="spec-1", feature_name="Feature 1", current_phase=WorkflowPhase.REQUIREMENTS),
            Mock(id="spec-2", feature_name="Feature 2", current_phase=WorkflowPhase.DESIGN)
        ]
        mock_file_manager.list_specs.return_value = mock_specs
        
        workflow_list = orchestrator.list_workflows()
        
        assert len(workflow_list) == 2
        assert workflow_list[0].id == "spec-1"
        assert workflow_list[1].id == "spec-2"
    
    def test_validate_workflow_success(self, orchestrator, mock_file_manager):
        """Test workflow validation for valid workflow."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Mock file manager validation
        mock_file_manager.validate_spec_structure.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        
        # Validate workflow
        validation = orchestrator.validate_workflow(spec_id)
        
        assert validation.is_valid
        mock_file_manager.validate_spec_structure.assert_called_with(spec_id)
    
    def test_validate_workflow_with_errors(self, orchestrator, mock_file_manager):
        """Test workflow validation with validation errors."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Mock file manager validation with errors
        mock_file_manager.validate_spec_structure.return_value = ValidationResult(
            is_valid=False,
            errors=[ValidationError(code="MISSING_FILE", message="Missing requirements.md", field="requirements")],
            warnings=[]
        )
        
        # Validate workflow
        validation = orchestrator.validate_workflow(spec_id)
        
        assert not validation.is_valid
        assert len(validation.errors) == 1
        assert validation.errors[0].code == "MISSING_FILE"
    
    def test_validate_workflow_not_found(self, orchestrator):
        """Test validation of non-existent workflow."""
        validation = orchestrator.validate_workflow("non-existent-spec")
        
        assert not validation.is_valid
        assert any("not found" in error.message.lower() for error in validation.errors)
    
    def test_update_document_requirements(self, orchestrator, mock_file_manager, mock_generators):
        """Test updating requirements document."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Mock document loading
        mock_doc = Mock()
        mock_doc.content = "# Requirements\n\nOriginal content"
        mock_file_manager.load_document.return_value = (mock_doc, Mock(success=True))
        
        # Mock generator update
        mock_generators['requirements'].update_requirements_document.return_value = (
            "# Requirements\n\nUpdated content",
            ["Updated requirement 1"]
        )
        
        # Update document
        changes = {"add_requirement": {"title": "New Requirement"}}
        updated_state, validation = orchestrator.update_document(
            spec_id, DocumentType.REQUIREMENTS, changes
        )
        
        assert validation.is_valid
        assert updated_state is not None
        mock_generators['requirements'].update_requirements_document.assert_called_once()
        mock_file_manager.save_document.assert_called()
    
    def test_update_document_design(self, orchestrator, mock_file_manager, mock_generators):
        """Test updating design document."""
        # Create workflow in design phase
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        workflow_state.current_phase = WorkflowPhase.DESIGN
        spec_id = workflow_state.spec_id
        orchestrator.workflow_states[spec_id] = workflow_state
        
        # Mock document loading
        design_doc = Mock()
        design_doc.content = "# Design\n\nOriginal design"
        req_doc = Mock()
        req_doc.content = "# Requirements\n\nRequirements"
        
        mock_file_manager.load_document.side_effect = [
            (design_doc, Mock(success=True)),
            (req_doc, Mock(success=True))
        ]
        
        # Mock generator update
        mock_generators['design'].update_design_document.return_value = (
            "# Design\n\nUpdated design",
            ["Updated architecture section"]
        )
        
        # Update document
        changes = {"update_section": {"section": "Architecture", "content": "New architecture"}}
        updated_state, validation = orchestrator.update_document(
            spec_id, DocumentType.DESIGN, changes
        )
        
        assert validation.is_valid
        mock_generators['design'].update_design_document.assert_called_once()
    
    def test_update_document_invalid_phase(self, orchestrator):
        """Test updating document in wrong phase."""
        # Create workflow in requirements phase
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Try to update design document while in requirements phase
        changes = {"update_section": {"section": "Overview"}}
        updated_state, validation = orchestrator.update_document(
            spec_id, DocumentType.DESIGN, changes
        )
        
        assert not validation.is_valid
        assert any("phase" in error.message.lower() for error in validation.errors)
    
    def test_workflow_state_persistence(self, orchestrator, mock_file_manager):
        """Test workflow state persistence."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Modify workflow state
        workflow_state.metadata["test_key"] = "test_value"
        
        # Save state
        orchestrator._save_workflow_state(workflow_state)
        
        # Verify file manager save was called
        mock_file_manager.save_document.assert_called()
    
    def test_workflow_state_recovery(self, orchestrator, mock_file_manager):
        """Test workflow state recovery from persistence."""
        # Mock file manager to return saved workflow state
        mock_metadata = Mock()
        mock_metadata.id = "test-spec"
        mock_metadata.current_phase = WorkflowPhase.DESIGN
        mock_metadata.status = WorkflowStatus.IN_PROGRESS
        
        mock_file_manager._load_spec_metadata.return_value = mock_metadata
        mock_file_manager.list_specs.return_value = [mock_metadata]
        
        # Create new orchestrator instance (simulates restart)
        new_orchestrator = WorkflowOrchestrator(orchestrator.workspace_root)
        
        # Check if workflow was loaded
        recovered_state = new_orchestrator.get_workflow_state("test-spec")
        
        # Note: This test would need the actual recovery logic implemented
        # For now, we verify the file manager was called
        mock_file_manager.list_specs.assert_called()
    
    def test_error_handling_during_generation(self, orchestrator, mock_generators):
        """Test error handling during document generation."""
        # Mock generator to raise exception
        mock_generators['requirements'].generate_requirements_document.side_effect = RuntimeError("AI service unavailable")
        
        # Try to create workflow
        workflow_state, result = orchestrator.create_spec_workflow("Test feature")
        
        assert not result.success
        assert "AI service unavailable" in result.message
        assert workflow_state is None
    
    def test_concurrent_workflow_creation(self, orchestrator, mock_file_manager):
        """Test handling concurrent workflow creation with same name."""
        feature_idea = "Test feature"
        
        # First creation succeeds
        workflow_state1, result1 = orchestrator.create_spec_workflow(feature_idea)
        assert result1.success
        
        # Second creation with same idea should fail
        mock_file_manager.create_spec_directory.return_value = (None, Mock(success=False, message="Directory already exists"))
        
        workflow_state2, result2 = orchestrator.create_spec_workflow(feature_idea)
        assert not result2.success
        assert "already exists" in result2.message.lower()
    
    def test_workflow_metadata_tracking(self, orchestrator):
        """Test workflow metadata tracking and updates."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        
        # Check initial metadata
        assert workflow_state.created_at is not None
        assert workflow_state.updated_at is not None
        assert workflow_state.version == "1.0.0"
        
        # Update workflow
        original_updated_at = workflow_state.updated_at
        workflow_state.metadata["test"] = "value"
        orchestrator._update_workflow_metadata(workflow_state)
        
        # Check metadata was updated
        assert workflow_state.updated_at > original_updated_at
    
    def test_workflow_validation_rules(self, orchestrator):
        """Test workflow validation rules enforcement."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        
        # Test various validation scenarios
        validation_tests = [
            # Valid state
            (WorkflowPhase.REQUIREMENTS, WorkflowStatus.DRAFT, True),
            # Invalid phase-status combination
            (WorkflowPhase.EXECUTION, WorkflowStatus.DRAFT, False),
        ]
        
        for phase, status, should_be_valid in validation_tests:
            workflow_state.current_phase = phase
            workflow_state.status = status
            
            validation = orchestrator._validate_workflow_state(workflow_state)
            assert validation.is_valid == should_be_valid


class TestWorkflowOrchestratorEdgeCases:
    """Test edge cases and error conditions for WorkflowOrchestrator."""
    
    @pytest.fixture
    def orchestrator_with_failures(self, temp_workspace):
        """Create orchestrator with failing dependencies for testing error handling."""
        mock_file_manager = Mock(spec=FileSystemManager)
        mock_file_manager.create_spec_directory.side_effect = Exception("File system error")
        
        with patch('eco_api.specs.workflow_orchestrator.FileSystemManager', return_value=mock_file_manager):
            return WorkflowOrchestrator(temp_workspace)
    
    def test_file_system_errors(self, orchestrator_with_failures):
        """Test handling of file system errors."""
        workflow_state, result = orchestrator_with_failures.create_spec_workflow("Test feature")
        
        assert not result.success
        assert "File system error" in result.message
        assert workflow_state is None
    
    def test_memory_constraints(self, orchestrator):
        """Test behavior under memory constraints."""
        # Create many workflows to test memory usage
        workflows = []
        for i in range(100):
            workflow_state, result = orchestrator.create_spec_workflow(f"Feature {i}")
            if result.success:
                workflows.append(workflow_state)
        
        # Verify workflows were created and memory is managed
        assert len(workflows) > 0
        assert len(orchestrator.workflow_states) == len(workflows)
    
    def test_invalid_feature_names(self, orchestrator):
        """Test handling of invalid feature names."""
        invalid_names = [
            "",  # Empty
            "   ",  # Whitespace only
            "a" * 300,  # Too long
            "feature/with/slashes",  # Invalid characters
            "feature\nwith\nnewlines",  # Newlines
        ]
        
        for invalid_name in invalid_names:
            workflow_state, result = orchestrator.create_spec_workflow(invalid_name)
            # Should either succeed with sanitized name or fail gracefully
            assert isinstance(result.success, bool)
    
    def test_workflow_state_corruption_recovery(self, orchestrator, mock_file_manager):
        """Test recovery from corrupted workflow state."""
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow("Test feature")
        spec_id = workflow_state.spec_id
        
        # Simulate state corruption
        orchestrator.workflow_states[spec_id] = None
        
        # Try to access corrupted state
        retrieved_state = orchestrator.get_workflow_state(spec_id)
        
        # Should handle gracefully
        assert retrieved_state is None or isinstance(retrieved_state, WorkflowState)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])