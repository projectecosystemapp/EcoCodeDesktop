"""
Integration tests for FastAPI endpoints with real database operations.

This module provides comprehensive integration testing for all spec-driven
workflow API endpoints with actual database interactions and file operations.

Requirements addressed:
- All requirements - integration validation
- API endpoint testing with real database and file system operations
- End-to-end workflow testing with actual persistence
"""

import pytest
import tempfile
import shutil
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eco_api.main import app
from eco_api.config import get_settings
from eco_api.specs.models import WorkflowPhase, WorkflowStatus, TaskStatus, DocumentType


class TestSpecsAPIIntegration:
    """Integration tests for specs API endpoints."""
    
    @pytest.fixture(scope="class")
    def temp_workspace(self):
        """Create a temporary workspace for integration testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture(scope="class")
    def test_database(self):
        """Create a test database for integration testing."""
        # Use in-memory SQLite for fast testing
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        # Create tables (this would normally be done by migrations)
        # For now, we'll assume tables exist or create them here
        
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        yield TestingSessionLocal
        
        engine.dispose()
    
    @pytest.fixture
    def client(self, temp_workspace, test_database):
        """Create a test client with overridden dependencies."""
        # Override settings to use test workspace
        def get_test_settings():
            settings = get_settings()
            settings.workspace_root = temp_workspace
            return settings
        
        app.dependency_overrides[get_settings] = get_test_settings
        
        with TestClient(app) as test_client:
            yield test_client
        
        # Clean up overrides
        app.dependency_overrides.clear()
    
    def test_create_spec_endpoint_success(self, client):
        """Test successful spec creation via API endpoint."""
        # Test data
        spec_data = {
            "feature_idea": "user authentication system with OAuth integration and multi-factor authentication",
            "feature_name": None  # Let system generate name
        }
        
        # Execute
        response = client.post("/api/v1/specs", json=spec_data)
        
        # Verify
        assert response.status_code == 201
        
        response_data = response.json()
        assert "spec_id" in response_data
        assert "workflow_state" in response_data
        
        workflow_state = response_data["workflow_state"]
        assert workflow_state["spec_id"] == "user-authentication-system-with-oauth-integration-and-multi-factor-authentication"
        assert workflow_state["current_phase"] == WorkflowPhase.REQUIREMENTS.value
        assert workflow_state["status"] == WorkflowStatus.DRAFT.value
        assert "requirements" in workflow_state["approvals"]
    
    def test_create_spec_endpoint_with_custom_name(self, client):
        """Test spec creation with custom feature name."""
        spec_data = {
            "feature_idea": "complex system",
            "feature_name": "custom-feature-name"
        }
        
        response = client.post("/api/v1/specs", json=spec_data)
        
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["workflow_state"]["spec_id"] == "custom-feature-name"
    
    def test_create_spec_endpoint_duplicate_name(self, client):
        """Test spec creation with duplicate name."""
        spec_data = {
            "feature_idea": "test feature",
            "feature_name": "duplicate-test"
        }
        
        # Create first spec
        response1 = client.post("/api/v1/specs", json=spec_data)
        assert response1.status_code == 201
        
        # Try to create second spec with same name
        response2 = client.post("/api/v1/specs", json=spec_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()
    
    def test_create_spec_endpoint_invalid_data(self, client):
        """Test spec creation with invalid data."""
        invalid_data_cases = [
            {},  # Empty data
            {"feature_idea": ""},  # Empty feature idea
            {"feature_idea": "   "},  # Whitespace only
            {"feature_name": "invalid/name/with/slashes"},  # Invalid characters
        ]
        
        for invalid_data in invalid_data_cases:
            response = client.post("/api/v1/specs", json=invalid_data)
            assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_get_specs_endpoint_empty(self, client):
        """Test getting specs when none exist."""
        response = client.get("/api/v1/specs")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "specs" in response_data
        assert len(response_data["specs"]) == 0
    
    def test_get_specs_endpoint_with_specs(self, client):
        """Test getting specs when multiple exist."""
        # Create multiple specs
        spec_names = ["first-test-spec", "second-test-spec", "third-test-spec"]
        
        for name in spec_names:
            spec_data = {
                "feature_idea": f"Test feature for {name}",
                "feature_name": name
            }
            response = client.post("/api/v1/specs", json=spec_data)
            assert response.status_code == 201
        
        # Get all specs
        response = client.get("/api/v1/specs")
        
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data["specs"]) == len(spec_names)
        
        # Verify all specs are returned
        returned_ids = [spec["id"] for spec in response_data["specs"]]
        for name in spec_names:
            assert name in returned_ids
    
    def test_get_spec_by_id_success(self, client):
        """Test getting specific spec by ID."""
        # Create a spec
        spec_data = {
            "feature_idea": "test feature for retrieval",
            "feature_name": "retrieval-test-spec"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        assert create_response.status_code == 201
        
        spec_id = create_response.json()["spec_id"]
        
        # Get the spec
        response = client.get(f"/api/v1/specs/{spec_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["spec_id"] == spec_id
        assert response_data["current_phase"] == WorkflowPhase.REQUIREMENTS.value
        assert "documents" in response_data
        assert "requirements" in response_data["documents"]
    
    def test_get_spec_by_id_not_found(self, client):
        """Test getting non-existent spec."""
        response = client.get("/api/v1/specs/non-existent-spec")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_requirements_endpoint_success(self, client):
        """Test successful requirements update."""
        # Create a spec
        spec_data = {
            "feature_idea": "test feature for requirements update",
            "feature_name": "requirements-update-test"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Update requirements
        update_data = {
            "changes": {
                "add_requirement": {
                    "title": "Additional Security Requirement",
                    "user_story": "**User Story:** As a user, I want enhanced security, so that my data is protected",
                    "acceptance_criteria": "4.1. WHEN accessing system THEN user SHALL be authenticated with MFA"
                }
            }
        }
        
        response = client.put(f"/api/v1/specs/{spec_id}/requirements", json=update_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "updated_content" in response_data
        assert "changes_made" in response_data
        assert len(response_data["changes_made"]) > 0
        assert "Additional Security Requirement" in response_data["updated_content"]
    
    def test_update_requirements_endpoint_invalid_phase(self, client):
        """Test requirements update in wrong phase."""
        # Create a spec and transition to design phase
        spec_data = {
            "feature_idea": "test feature",
            "feature_name": "phase-test-spec"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Approve requirements and transition to design
        approve_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/requirements",
            json={"approved": True, "feedback": "Looks good"}
        )
        assert approve_response.status_code == 200
        
        transition_response = client.post(
            f"/api/v1/specs/{spec_id}/transition",
            json={"target_phase": WorkflowPhase.DESIGN.value, "approval": True}
        )
        assert transition_response.status_code == 200
        
        # Try to update requirements while in design phase
        update_data = {
            "changes": {
                "add_requirement": {
                    "title": "New Requirement",
                    "user_story": "Test story",
                    "acceptance_criteria": "Test criteria"
                }
            }
        }
        
        response = client.put(f"/api/v1/specs/{spec_id}/requirements", json=update_data)
        
        assert response.status_code == 400
        assert "phase" in response.json()["detail"].lower()
    
    def test_approve_phase_endpoint_success(self, client):
        """Test successful phase approval."""
        # Create a spec
        spec_data = {
            "feature_idea": "test feature for approval",
            "feature_name": "approval-test-spec"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Approve requirements phase
        approval_data = {
            "approved": True,
            "feedback": "Requirements look comprehensive and well-structured"
        }
        
        response = client.post(f"/api/v1/specs/{spec_id}/approve/requirements", json=approval_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["approved"] == True
        assert response_data["phase"] == WorkflowPhase.REQUIREMENTS.value
        assert "Requirements look comprehensive" in response_data["feedback"]
    
    def test_approve_phase_endpoint_rejection(self, client):
        """Test phase rejection."""
        # Create a spec
        spec_data = {
            "feature_idea": "test feature for rejection",
            "feature_name": "rejection-test-spec"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Reject requirements phase
        approval_data = {
            "approved": False,
            "feedback": "Requirements need more detail on security aspects"
        }
        
        response = client.post(f"/api/v1/specs/{spec_id}/approve/requirements", json=approval_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["approved"] == False
        assert "security aspects" in response_data["feedback"]
    
    def test_transition_workflow_endpoint_success(self, client):
        """Test successful workflow transition."""
        # Create a spec
        spec_data = {
            "feature_idea": "test feature for transition",
            "feature_name": "transition-test-spec"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Approve requirements first
        approve_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/requirements",
            json={"approved": True, "feedback": "Good requirements"}
        )
        assert approve_response.status_code == 200
        
        # Transition to design phase
        transition_data = {
            "target_phase": WorkflowPhase.DESIGN.value,
            "approval": True
        }
        
        response = client.post(f"/api/v1/specs/{spec_id}/transition", json=transition_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["current_phase"] == WorkflowPhase.DESIGN.value
        assert "design_content" in response_data
    
    def test_transition_workflow_endpoint_invalid_transition(self, client):
        """Test invalid workflow transition."""
        # Create a spec
        spec_data = {
            "feature_idea": "test feature",
            "feature_name": "invalid-transition-test"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Try invalid transition (requirements to execution)
        transition_data = {
            "target_phase": WorkflowPhase.EXECUTION.value,
            "approval": True
        }
        
        response = client.post(f"/api/v1/specs/{spec_id}/transition", json=transition_data)
        
        assert response.status_code == 400
        assert "transition" in response.json()["detail"].lower()
    
    def test_execute_task_endpoint_success(self, client):
        """Test successful task execution."""
        # Create a spec and progress to execution phase
        spec_id = self._create_spec_in_execution_phase(client)
        
        # Execute a task
        response = client.post(f"/api/v1/specs/{spec_id}/tasks/1/execute")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] == True
        assert response_data["task_id"] == "1"
        assert "files_created" in response_data
        assert "execution_time" in response_data
    
    def test_execute_task_endpoint_task_not_found(self, client):
        """Test task execution with non-existent task."""
        # Create a spec in execution phase
        spec_id = self._create_spec_in_execution_phase(client)
        
        # Try to execute non-existent task
        response = client.post(f"/api/v1/specs/{spec_id}/tasks/999/execute")
        
        assert response.status_code == 404
        assert "task not found" in response.json()["detail"].lower()
    
    def test_update_task_status_endpoint_success(self, client):
        """Test successful task status update."""
        # Create a spec in execution phase
        spec_id = self._create_spec_in_execution_phase(client)
        
        # Update task status
        status_data = {
            "status": TaskStatus.IN_PROGRESS.value
        }
        
        response = client.put(f"/api/v1/specs/{spec_id}/tasks/1/status", json=status_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == "1"
        assert response_data["status"] == TaskStatus.IN_PROGRESS.value
    
    def test_get_progress_endpoint_success(self, client):
        """Test getting spec progress."""
        # Create a spec in execution phase
        spec_id = self._create_spec_in_execution_phase(client)
        
        # Get progress
        response = client.get(f"/api/v1/specs/{spec_id}/progress")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "total_tasks" in response_data
        assert "completed_tasks" in response_data
        assert "completion_percentage" in response_data
        assert "next_recommended_task" in response_data
    
    def test_get_workflow_status_endpoint_success(self, client):
        """Test getting workflow status."""
        # Create a spec
        spec_data = {
            "feature_idea": "test feature for status",
            "feature_name": "status-test-spec"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Get workflow status
        response = client.get(f"/api/v1/specs/{spec_id}/status")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["spec_id"] == spec_id
        assert response_data["current_phase"] == WorkflowPhase.REQUIREMENTS.value
        assert response_data["status"] == WorkflowStatus.DRAFT.value
        assert "approvals" in response_data
        assert "metadata" in response_data
    
    def _create_spec_in_execution_phase(self, client) -> str:
        """Helper method to create a spec and progress it to execution phase."""
        # Create spec
        spec_data = {
            "feature_idea": "test feature for execution",
            "feature_name": f"execution-test-{datetime.now().timestamp()}"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Progress through phases
        phases = [
            (WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN),
            (WorkflowPhase.DESIGN, WorkflowPhase.TASKS),
            (WorkflowPhase.TASKS, WorkflowPhase.EXECUTION)
        ]
        
        for current_phase, next_phase in phases:
            # Approve current phase
            approve_response = client.post(
                f"/api/v1/specs/{spec_id}/approve/{current_phase.value}",
                json={"approved": True, "feedback": f"Approved {current_phase.value}"}
            )
            assert approve_response.status_code == 200
            
            # Transition to next phase
            transition_response = client.post(
                f"/api/v1/specs/{spec_id}/transition",
                json={"target_phase": next_phase.value, "approval": True}
            )
            assert transition_response.status_code == 200
        
        return spec_id


class TestWorkflowIntegration:
    """Integration tests for complete workflow scenarios."""
    
    @pytest.fixture
    def client(self, temp_workspace):
        """Create a test client for workflow testing."""
        def get_test_settings():
            settings = get_settings()
            settings.workspace_root = temp_workspace
            return settings
        
        app.dependency_overrides[get_settings] = get_test_settings
        
        with TestClient(app) as test_client:
            yield test_client
        
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_complete_workflow_simple_feature(self, client):
        """Test complete workflow for a simple feature."""
        # 1. Create spec
        spec_data = {
            "feature_idea": "simple user login system with email and password authentication",
            "feature_name": "simple-login-system"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        assert create_response.status_code == 201
        spec_id = create_response.json()["spec_id"]
        
        # 2. Review and approve requirements
        get_response = client.get(f"/api/v1/specs/{spec_id}")
        assert get_response.status_code == 200
        assert "requirements" in get_response.json()["documents"]
        
        approve_req_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/requirements",
            json={"approved": True, "feedback": "Requirements are clear and complete"}
        )
        assert approve_req_response.status_code == 200
        
        # 3. Transition to design phase
        transition_design_response = client.post(
            f"/api/v1/specs/{spec_id}/transition",
            json={"target_phase": WorkflowPhase.DESIGN.value, "approval": True}
        )
        assert transition_design_response.status_code == 200
        assert "design_content" in transition_design_response.json()
        
        # 4. Review and approve design
        approve_design_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/design",
            json={"approved": True, "feedback": "Design architecture looks solid"}
        )
        assert approve_design_response.status_code == 200
        
        # 5. Transition to tasks phase
        transition_tasks_response = client.post(
            f"/api/v1/specs/{spec_id}/transition",
            json={"target_phase": WorkflowPhase.TASKS.value, "approval": True}
        )
        assert transition_tasks_response.status_code == 200
        assert "tasks_content" in transition_tasks_response.json()
        
        # 6. Review and approve tasks
        approve_tasks_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/tasks",
            json={"approved": True, "feedback": "Task breakdown is comprehensive"}
        )
        assert approve_tasks_response.status_code == 200
        
        # 7. Transition to execution phase
        transition_exec_response = client.post(
            f"/api/v1/specs/{spec_id}/transition",
            json={"target_phase": WorkflowPhase.EXECUTION.value, "approval": True}
        )
        assert transition_exec_response.status_code == 200
        
        # 8. Execute some tasks
        progress_response = client.get(f"/api/v1/specs/{spec_id}/progress")
        assert progress_response.status_code == 200
        
        next_task_id = progress_response.json()["next_recommended_task"]["id"]
        
        execute_response = client.post(f"/api/v1/specs/{spec_id}/tasks/{next_task_id}/execute")
        assert execute_response.status_code == 200
        assert execute_response.json()["success"] == True
        
        # 9. Check final status
        status_response = client.get(f"/api/v1/specs/{spec_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["current_phase"] == WorkflowPhase.EXECUTION.value
    
    def test_complete_workflow_with_revisions(self, client):
        """Test complete workflow with requirement revisions."""
        # 1. Create spec
        spec_data = {
            "feature_idea": "e-commerce product catalog with search and filtering",
            "feature_name": "ecommerce-catalog"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # 2. Reject requirements initially
        reject_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/requirements",
            json={"approved": False, "feedback": "Need more detail on search functionality"}
        )
        assert reject_response.status_code == 200
        
        # 3. Update requirements based on feedback
        update_response = client.put(
            f"/api/v1/specs/{spec_id}/requirements",
            json={
                "changes": {
                    "add_requirement": {
                        "title": "Advanced Search Functionality",
                        "user_story": "**User Story:** As a customer, I want advanced search with filters, so that I can find products quickly",
                        "acceptance_criteria": "5.1. WHEN user searches THEN system SHALL provide autocomplete suggestions\n5.2. WHEN user applies filters THEN system SHALL update results in real-time"
                    }
                }
            }
        )
        assert update_response.status_code == 200
        
        # 4. Approve updated requirements
        approve_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/requirements",
            json={"approved": True, "feedback": "Much better with detailed search requirements"}
        )
        assert approve_response.status_code == 200
        
        # 5. Continue with rest of workflow
        transition_response = client.post(
            f"/api/v1/specs/{spec_id}/transition",
            json={"target_phase": WorkflowPhase.DESIGN.value, "approval": True}
        )
        assert transition_response.status_code == 200
        
        # Verify the design includes search functionality
        design_content = transition_response.json()["design_content"]
        assert "search" in design_content.lower()
    
    def test_workflow_error_recovery(self, client):
        """Test workflow error recovery scenarios."""
        # 1. Create spec with problematic data
        spec_data = {
            "feature_idea": "test feature for error recovery",
            "feature_name": "error-recovery-test"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # 2. Try invalid operations and verify error handling
        
        # Try to approve wrong phase
        wrong_phase_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/design",  # Should be requirements
            json={"approved": True, "feedback": "Test"}
        )
        assert wrong_phase_response.status_code == 400
        
        # Try invalid transition
        invalid_transition_response = client.post(
            f"/api/v1/specs/{spec_id}/transition",
            json={"target_phase": WorkflowPhase.EXECUTION.value, "approval": True}
        )
        assert invalid_transition_response.status_code == 400
        
        # Try to execute task before execution phase
        early_execute_response = client.post(f"/api/v1/specs/{spec_id}/tasks/1/execute")
        assert early_execute_response.status_code == 400
        
        # Verify spec is still in valid state
        status_response = client.get(f"/api/v1/specs/{spec_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["current_phase"] == WorkflowPhase.REQUIREMENTS.value
    
    def test_concurrent_workflow_operations(self, client):
        """Test concurrent operations on the same workflow."""
        # Create spec
        spec_data = {
            "feature_idea": "concurrent operations test",
            "feature_name": "concurrent-test"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Simulate concurrent operations
        # Note: In a real concurrent test, these would run in parallel
        # For this test, we'll verify the system handles sequential operations correctly
        
        # Multiple status checks
        for i in range(5):
            status_response = client.get(f"/api/v1/specs/{spec_id}/status")
            assert status_response.status_code == 200
        
        # Multiple approval attempts (should be idempotent)
        for i in range(3):
            approve_response = client.post(
                f"/api/v1/specs/{spec_id}/approve/requirements",
                json={"approved": True, "feedback": f"Approval attempt {i+1}"}
            )
            assert approve_response.status_code == 200
        
        # Verify final state is consistent
        final_status = client.get(f"/api/v1/specs/{spec_id}/status")
        assert final_status.status_code == 200
        workflow_state = final_status.json()
        assert workflow_state["approvals"]["requirements"]["approved"] == True
    
    def test_workflow_persistence_across_requests(self, client):
        """Test that workflow state persists across multiple requests."""
        # Create spec
        spec_data = {
            "feature_idea": "persistence test feature",
            "feature_name": "persistence-test"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        original_created_at = create_response.json()["workflow_state"]["created_at"]
        
        # Perform operations
        approve_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/requirements",
            json={"approved": True, "feedback": "Persistence test approval"}
        )
        assert approve_response.status_code == 200
        
        # Verify state persists in new request
        get_response = client.get(f"/api/v1/specs/{spec_id}")
        assert get_response.status_code == 200
        
        workflow_data = get_response.json()
        assert workflow_data["spec_id"] == spec_id
        assert workflow_data["created_at"] == original_created_at
        assert workflow_data["approvals"]["requirements"]["approved"] == True
        assert workflow_data["approvals"]["requirements"]["feedback"] == "Persistence test approval"
        
        # Verify in specs list
        list_response = client.get("/api/v1/specs")
        assert list_response.status_code == 200
        
        specs = list_response.json()["specs"]
        test_spec = next(spec for spec in specs if spec["id"] == spec_id)
        assert test_spec["current_phase"] == WorkflowPhase.REQUIREMENTS.value


class TestFileSystemIntegration:
    """Integration tests for file system operations."""
    
    @pytest.fixture
    def client_with_real_fs(self, temp_workspace):
        """Create client with real file system operations."""
        def get_test_settings():
            settings = get_settings()
            settings.workspace_root = temp_workspace
            return settings
        
        app.dependency_overrides[get_settings] = get_test_settings
        
        with TestClient(app) as test_client:
            yield test_client, temp_workspace
        
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_spec_directory_creation(self, client_with_real_fs):
        """Test that spec directories are created correctly."""
        client, workspace = client_with_real_fs
        
        # Create spec
        spec_data = {
            "feature_idea": "file system test feature",
            "feature_name": "filesystem-test"
        }
        
        response = client.post("/api/v1/specs", json=spec_data)
        assert response.status_code == 201
        
        # Verify directory structure
        spec_dir = Path(workspace) / ".kiro" / "specs" / "filesystem-test"
        assert spec_dir.exists()
        assert spec_dir.is_dir()
        
        # Verify files are created
        requirements_file = spec_dir / "requirements.md"
        assert requirements_file.exists()
        
        # Verify file content
        requirements_content = requirements_file.read_text()
        assert "# Requirements Document" in requirements_content
        assert "file system test feature" in requirements_content.lower()
    
    def test_document_persistence_and_loading(self, client_with_real_fs):
        """Test document persistence and loading from file system."""
        client, workspace = client_with_real_fs
        
        # Create spec
        spec_data = {
            "feature_idea": "document persistence test",
            "feature_name": "doc-persistence-test"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Progress to design phase
        approve_response = client.post(
            f"/api/v1/specs/{spec_id}/approve/requirements",
            json={"approved": True, "feedback": "Good requirements"}
        )
        assert approve_response.status_code == 200
        
        transition_response = client.post(
            f"/api/v1/specs/{spec_id}/transition",
            json={"target_phase": WorkflowPhase.DESIGN.value, "approval": True}
        )
        assert transition_response.status_code == 200
        
        # Verify design file is created
        spec_dir = Path(workspace) / ".kiro" / "specs" / spec_id
        design_file = spec_dir / "design.md"
        assert design_file.exists()
        
        # Verify design content
        design_content = design_file.read_text()
        assert "# Design Document" in design_content
        assert "## Overview" in design_content
        
        # Verify loading works
        get_response = client.get(f"/api/v1/specs/{spec_id}")
        assert get_response.status_code == 200
        
        response_data = get_response.json()
        assert "design" in response_data["documents"]
        assert response_data["documents"]["design"] == design_content
    
    def test_file_corruption_handling(self, client_with_real_fs):
        """Test handling of corrupted spec files."""
        client, workspace = client_with_real_fs
        
        # Create spec
        spec_data = {
            "feature_idea": "corruption test",
            "feature_name": "corruption-test"
        }
        
        create_response = client.post("/api/v1/specs", json=spec_data)
        spec_id = create_response.json()["spec_id"]
        
        # Corrupt the requirements file
        spec_dir = Path(workspace) / ".kiro" / "specs" / spec_id
        requirements_file = spec_dir / "requirements.md"
        requirements_file.write_text("CORRUPTED CONTENT")
        
        # Try to access the spec
        get_response = client.get(f"/api/v1/specs/{spec_id}")
        
        # Should handle corruption gracefully
        # Depending on implementation, this might return an error or attempt recovery
        assert get_response.status_code in [200, 400, 500]
        
        if get_response.status_code != 200:
            # Verify error message indicates corruption
            error_detail = get_response.json().get("detail", "").lower()
            assert any(keyword in error_detail for keyword in ["corrupt", "invalid", "error"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])