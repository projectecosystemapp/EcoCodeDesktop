"""
Tests for the specs router endpoints.

This module tests the FastAPI endpoints for spec-driven workflow management,
including creation, retrieval, document management, and task execution.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from eco_api.main import app
from eco_api.specs.models import WorkflowPhase, WorkflowStatus, TaskStatus


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_workflow_orchestrator():
    """Create a mock workflow orchestrator."""
    mock = Mock()
    
    # Mock workflow state
    mock_state = Mock()
    mock_state.spec_id = "test-feature"
    mock_state.current_phase = WorkflowPhase.REQUIREMENTS
    mock_state.status = WorkflowStatus.DRAFT
    mock_state.created_at = datetime.utcnow()
    mock_state.updated_at = datetime.utcnow()
    mock_state.approvals = {"requirements": "pending"}
    mock_state.metadata = {"feature_idea": "Test feature"}
    
    # Mock file operation result
    mock_result = Mock()
    mock_result.success = True
    mock_result.message = "Success"
    mock_result.path = "/test/path"
    
    # Configure mock methods
    mock.create_spec_workflow.return_value = (mock_state, mock_result)
    mock.get_workflow_state.return_value = mock_state
    mock.list_workflows.return_value = []
    
    return mock


class TestSpecsRouter:
    """Test cases for the specs router endpoints."""
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_create_spec_success(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test successful spec creation."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        response = client.post("/specs", json={
            "feature_idea": "A new test feature",
            "feature_name": "test-feature"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "test-feature"
        assert data["feature_name"] == "test-feature"
        assert data["current_phase"] == "requirements"
        assert data["status"] == "draft"
        assert data["progress"] == 0.0
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_create_spec_invalid_request(self, mock_get_orchestrator, client):
        """Test spec creation with invalid request."""
        response = client.post("/specs", json={
            "feature_idea": ""  # Too short
        })
        
        assert response.status_code == 422  # Validation error
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_list_specs_success(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test successful spec listing."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        response = client.get("/specs")
        
        assert response.status_code == 200
        data = response.json()
        assert "specs" in data
        assert "total_count" in data
        assert isinstance(data["specs"], list)
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_get_spec_success(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test successful spec retrieval."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        # Mock file manager
        mock_file_manager = Mock()
        mock_doc = Mock()
        mock_doc.content = "# Test Requirements"
        mock_result = Mock()
        mock_result.success = True
        mock_file_manager.load_document.return_value = (mock_doc, mock_result)
        mock_workflow_orchestrator.file_manager = mock_file_manager
        
        response = client.get("/specs/test-feature")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-feature"
        assert data["feature_name"] == "test-feature"
        assert "documents" in data
        assert "approvals" in data
        assert "metadata" in data
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_get_spec_not_found(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test spec retrieval when spec not found."""
        mock_workflow_orchestrator.get_workflow_state.return_value = None
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        response = client.get("/specs/nonexistent")
        
        assert response.status_code == 404
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_update_requirements_success(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test successful requirements update."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        # Mock file manager
        mock_file_manager = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_file_manager.save_document.return_value = mock_result
        mock_workflow_orchestrator.file_manager = mock_file_manager
        
        response = client.put("/specs/test-feature/requirements", json={
            "content": "# Updated Requirements\n\nNew content here."
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "checksum" in data
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_execute_task_placeholder(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test task execution (placeholder implementation)."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        response = client.post("/specs/test-feature/tasks/1.1/execute", json={
            "task_description": "Test task"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "1.1"
        assert "execution_log" in data
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_get_progress_success(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test successful progress retrieval."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        response = client.get("/specs/test-feature/progress")
        
        assert response.status_code == 200
        data = response.json()
        assert data["spec_id"] == "test-feature"
        assert "total_tasks" in data
        assert "progress_percentage" in data
        assert "current_phase" in data
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_approve_phase_success(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test successful phase approval."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        # Mock approval result
        from eco_api.specs.models import ValidationResult
        mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[])
        mock_workflow_orchestrator.approve_phase.return_value = (mock_workflow_orchestrator.get_workflow_state.return_value, mock_validation)
        
        response = client.post("/specs/test-feature/approve/requirements", json={
            "approved": True,
            "feedback": "Looks good!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["phase"] == "requirements"
        assert data["approved"] is True
    
    @patch('eco_api.specs.router.get_workflow_orchestrator')
    def test_get_workflow_status_success(self, mock_get_orchestrator, client, mock_workflow_orchestrator):
        """Test successful workflow status retrieval."""
        mock_get_orchestrator.return_value = mock_workflow_orchestrator
        
        response = client.get("/specs/test-feature/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["spec_id"] == "test-feature"
        assert data["current_phase"] == "requirements"
        assert data["status"] == "draft"
        assert "approvals" in data
        assert "valid_transitions" in data


if __name__ == "__main__":
    pytest.main([__file__])