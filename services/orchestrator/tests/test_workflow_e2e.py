"""
End-to-end workflow tests with file system operations.

This module provides comprehensive end-to-end testing for complete spec-driven
workflows with actual file system operations and persistence.

Requirements addressed:
- All requirements - integration validation
- End-to-end workflow tests with file system operations
- Complete workflow scenarios from creation to task execution
"""

import pytest
import tempfile
import shutil
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator
from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.generators import RequirementsGenerator, DesignGenerator, TasksGenerator
from eco_api.specs.task_execution_engine import TaskExecutionEngine
from eco_api.specs.research_service import ResearchService
from eco_api.specs.models import (
    WorkflowPhase, WorkflowStatus, TaskStatus, DocumentType,
    ValidationResult, ValidationError, ValidationWarning
)


class TestEndToEndWorkflows:
    """End-to-end tests for complete spec-driven workflows."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for E2E testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def workflow_orchestrator(self, temp_workspace):
        """Create a WorkflowOrchestrator with real dependencies."""
        return WorkflowOrchestrator(temp_workspace)
    
    @pytest.fixture
    def file_manager(self, temp_workspace):
        """Create a FileSystemManager for testing."""
        return FileSystemManager(temp_workspace)
    
    @pytest.fixture
    def task_engine(self, temp_workspace):
        """Create a TaskExecutionEngine for testing."""
        return TaskExecutionEngine(temp_workspace)
    
    def test_complete_simple_workflow_e2e(self, workflow_orchestrator, file_manager, task_engine, temp_workspace):
        """Test complete end-to-end workflow for a simple feature."""
        feature_idea = "user authentication system with email and password login"
        
        # Phase 1: Create spec and generate requirements
        workflow_state, create_result = workflow_orchestrator.create_spec_workflow(feature_idea)
        
        assert create_result.success
        assert workflow_state is not None
        spec_id = workflow_state.spec_id
        
        # Verify file system structure
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        assert spec_dir.exists()
        assert (spec_dir / "requirements.md").exists()
        assert (spec_dir / ".spec-metadata.json").exists()
        
        # Verify requirements content
        requirements_content = (spec_dir / "requirements.md").read_text()
        assert "# Requirements Document" in requirements_content
        assert "authentication" in requirements_content.lower()
        assert "**User Story:**" in requirements_content
        assert "WHEN" in requirements_content and "THEN" in requirements_content and "SHALL" in requirements_content
        
        # Phase 2: Approve requirements and transition to design
        approve_result, validation = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Requirements are clear and comprehensive"
        )
        
        assert validation.is_valid
        assert approve_result.approvals["requirements"].approved == True
        
        # Transition to design phase
        design_state, design_validation = workflow_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        assert design_validation.is_valid
        assert design_state.current_phase == WorkflowPhase.DESIGN
        
        # Verify design file was created
        assert (spec_dir / "design.md").exists()
        
        design_content = (spec_dir / "design.md").read_text()
        assert "# Design Document" in design_content
        assert "## Overview" in design_content
        assert "## Architecture" in design_content
        assert "## Components and Interfaces" in design_content
        assert "authentication" in design_content.lower()
        
        # Phase 3: Approve design and transition to tasks
        approve_design_result, design_approval_validation = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Architecture looks solid and scalable"
        )
        
        assert design_approval_validation.is_valid
        
        tasks_state, tasks_validation = workflow_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        assert tasks_validation.is_valid
        assert tasks_state.current_phase == WorkflowPhase.TASKS
        
        # Verify tasks file was created
        assert (spec_dir / "tasks.md").exists()
        
        tasks_content = (spec_dir / "tasks.md").read_text()
        assert "# Implementation Plan" in tasks_content
        assert "- [ ]" in tasks_content  # Checkbox format
        assert "_Requirements:" in tasks_content  # Requirement references
        
        # Phase 4: Approve tasks and transition to execution
        approve_tasks_result, tasks_approval_validation = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.TASKS, True, "Task breakdown is detailed and actionable"
        )
        
        assert tasks_approval_validation.is_valid
        
        execution_state, execution_validation = workflow_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.EXECUTION, approval=True
        )
        
        assert execution_validation.is_valid
        assert execution_state.current_phase == WorkflowPhase.EXECUTION
        
        # Phase 5: Execute tasks
        # Load execution context
        context, context_result = task_engine.load_execution_context(spec_id)
        assert context_result.is_valid
        assert context is not None
        
        # Get available tasks
        tasks = task_engine.parse_tasks_from_document(context.tasks_content)
        assert len(tasks) > 0
        
        # Execute first task
        first_task = next(task for task in tasks if task.level == 0)  # Main task
        execution_result = task_engine.execute_task(spec_id, first_task.id)
        
        assert execution_result.success
        assert execution_result.task_id == first_task.id
        assert len(execution_result.files_created) > 0 or len(execution_result.files_modified) > 0
        
        # Verify task status was updated in file
        updated_tasks_content = (spec_dir / "tasks.md").read_text()
        assert f"- [x] {first_task.id}." in updated_tasks_content or f"- [-] {first_task.id}." in updated_tasks_content
        
        # Check progress
        progress, progress_result = task_engine.calculate_progress(spec_id)
        assert progress_result.is_valid
        assert progress['total_tasks'] > 0
        assert progress['completed_tasks'] >= 1 or progress['in_progress_tasks'] >= 1
        
        # Verify final workflow state
        final_state = workflow_orchestrator.get_workflow_state(spec_id)
        assert final_state.current_phase == WorkflowPhase.EXECUTION
        assert final_state.status == WorkflowStatus.IN_PROGRESS
    
    def test_complex_workflow_with_revisions_e2e(self, workflow_orchestrator, file_manager, temp_workspace):
        """Test complex workflow with multiple revisions and updates."""
        feature_idea = "e-commerce platform with product catalog, shopping cart, payment processing, and order management"
        
        # Create initial spec
        workflow_state, create_result = workflow_orchestrator.create_spec_workflow(feature_idea)
        assert create_result.success
        spec_id = workflow_state.spec_id
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        
        # Initial requirements review - reject for more detail
        reject_result, reject_validation = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, False, 
            "Need more detail on payment processing security and order state management"
        )
        
        assert reject_validation.is_valid
        assert reject_result.approvals["requirements"].approved == False
        
        # Update requirements based on feedback
        requirements_changes = {
            "add_requirement": {
                "title": "Payment Security and Compliance",
                "user_story": "**User Story:** As a customer, I want secure payment processing, so that my financial data is protected",
                "acceptance_criteria": """6.1. WHEN processing payments THEN system SHALL use PCI DSS compliant methods
6.2. WHEN storing payment data THEN system SHALL encrypt sensitive information
6.3. IF payment fails THEN system SHALL handle errors gracefully without exposing sensitive data"""
            }
        }
        
        updated_req_state, req_update_validation = workflow_orchestrator.update_document(
            spec_id, DocumentType.REQUIREMENTS, requirements_changes
        )
        
        assert req_update_validation.is_valid
        
        # Verify updated requirements file
        updated_requirements = (spec_dir / "requirements.md").read_text()
        assert "Payment Security and Compliance" in updated_requirements
        assert "PCI DSS" in updated_requirements
        
        # Approve updated requirements
        approve_updated_result, approve_validation = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, 
            "Much better with detailed security requirements"
        )
        
        assert approve_validation.is_valid
        
        # Progress through design phase
        design_state, design_validation = workflow_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        assert design_validation.is_valid
        
        # Verify design includes security considerations
        design_content = (spec_dir / "design.md").read_text()
        assert "security" in design_content.lower()
        assert "payment" in design_content.lower()
        
        # Update design to add more architectural detail
        design_changes = {
            "update_section": {
                "section": "Architecture",
                "content": """### System Architecture

The e-commerce platform uses a microservices architecture with the following services:

1. **Product Catalog Service**: Manages product information and search
2. **Shopping Cart Service**: Handles cart operations and session management  
3. **Payment Service**: Processes payments with PCI DSS compliance
4. **Order Management Service**: Manages order lifecycle and state transitions
5. **User Service**: Handles authentication and user profiles

### Security Architecture

- All services communicate via encrypted channels (TLS 1.3)
- Payment service is isolated with additional security controls
- API Gateway handles authentication and rate limiting
- Audit logging for all financial transactions"""
            }
        }
        
        updated_design_state, design_update_validation = workflow_orchestrator.update_document(
            spec_id, DocumentType.DESIGN, design_changes
        )
        
        assert design_update_validation.is_valid
        
        # Verify updated design
        updated_design = (spec_dir / "design.md").read_text()
        assert "microservices architecture" in updated_design.lower()
        assert "Payment Service" in updated_design
        
        # Continue through workflow
        approve_design_result, _ = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Comprehensive architecture with good security design"
        )
        
        tasks_state, _ = workflow_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        # Verify tasks reflect the complexity
        tasks_content = (spec_dir / "tasks.md").read_text()
        assert "microservice" in tasks_content.lower() or "service" in tasks_content.lower()
        assert "payment" in tasks_content.lower()
        assert "security" in tasks_content.lower()
        
        # Count tasks to verify complexity
        task_lines = [line for line in tasks_content.split('\n') if line.strip().startswith('- [ ]')]
        assert len(task_lines) >= 10  # Complex feature should have many tasks
    
    def test_workflow_persistence_and_recovery_e2e(self, temp_workspace):
        """Test workflow persistence and recovery across orchestrator instances."""
        feature_idea = "project management tool with task tracking and team collaboration"
        
        # Create workflow with first orchestrator instance
        orchestrator1 = WorkflowOrchestrator(temp_workspace)
        workflow_state1, create_result = orchestrator1.create_spec_workflow(feature_idea)
        
        assert create_result.success
        spec_id = workflow_state1.spec_id
        
        # Progress through some phases
        approve_result, _ = orchestrator1.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Good requirements"
        )
        
        design_state, _ = orchestrator1.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        # Store some metadata for comparison
        original_created_at = workflow_state1.created_at
        original_version = workflow_state1.version
        
        # Create new orchestrator instance (simulates restart)
        orchestrator2 = WorkflowOrchestrator(temp_workspace)
        
        # Verify workflow can be recovered
        recovered_state = orchestrator2.get_workflow_state(spec_id)
        
        assert recovered_state is not None
        assert recovered_state.spec_id == spec_id
        assert recovered_state.current_phase == WorkflowPhase.DESIGN
        assert recovered_state.created_at == original_created_at
        
        # Verify we can continue the workflow
        approve_design_result, _ = orchestrator2.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Design looks good"
        )
        
        tasks_state, _ = orchestrator2.transition_workflow(
            spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        assert tasks_state.current_phase == WorkflowPhase.TASKS
        
        # Verify files are consistent
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        assert (spec_dir / "requirements.md").exists()
        assert (spec_dir / "design.md").exists()
        assert (spec_dir / "tasks.md").exists()
    
    def test_concurrent_workflow_operations_e2e(self, temp_workspace):
        """Test concurrent operations on multiple workflows."""
        # Create multiple workflows concurrently
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        feature_ideas = [
            "user authentication system",
            "data analytics dashboard", 
            "file upload service",
            "notification system",
            "search functionality"
        ]
        
        # Create all workflows
        workflows = []
        for i, idea in enumerate(feature_ideas):
            workflow_state, result = orchestrator.create_spec_workflow(
                idea, f"feature-{i+1}"
            )
            assert result.success
            workflows.append(workflow_state)
        
        # Verify all workflows exist
        workflow_list = orchestrator.list_workflows()
        assert len(workflow_list) == len(feature_ideas)
        
        # Progress each workflow to different phases
        for i, workflow in enumerate(workflows):
            spec_id = workflow.spec_id
            
            # Approve requirements
            approve_result, _ = orchestrator.approve_phase(
                spec_id, WorkflowPhase.REQUIREMENTS, True, f"Approved requirements for {spec_id}"
            )
            
            if i % 2 == 0:  # Progress even-numbered workflows further
                design_state, _ = orchestrator.transition_workflow(
                    spec_id, WorkflowPhase.DESIGN, approval=True
                )
                
                if i % 4 == 0:  # Progress every 4th workflow to tasks
                    approve_design_result, _ = orchestrator.approve_phase(
                        spec_id, WorkflowPhase.DESIGN, True, f"Approved design for {spec_id}"
                    )
                    
                    tasks_state, _ = orchestrator.transition_workflow(
                        spec_id, WorkflowPhase.TASKS, approval=True
                    )
        
        # Verify final states
        final_workflows = orchestrator.list_workflows()
        phases = [w.current_phase for w in final_workflows]
        
        # Should have workflows in different phases
        assert WorkflowPhase.REQUIREMENTS in phases
        assert WorkflowPhase.DESIGN in phases
        assert WorkflowPhase.TASKS in phases
        
        # Verify file system integrity
        specs_dir = Path(temp_workspace) / ".kiro" / "specs"
        created_dirs = list(specs_dir.iterdir())
        assert len(created_dirs) == len(feature_ideas)
        
        for spec_dir in created_dirs:
            assert (spec_dir / "requirements.md").exists()
            # Design and tasks files should exist for progressed workflows
    
    def test_error_recovery_and_validation_e2e(self, workflow_orchestrator, file_manager, temp_workspace):
        """Test error recovery and validation in end-to-end scenarios."""
        feature_idea = "error recovery test feature"
        
        # Create workflow
        workflow_state, create_result = workflow_orchestrator.create_spec_workflow(feature_idea)
        assert create_result.success
        spec_id = workflow_state.spec_id
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        
        # Test file corruption recovery
        requirements_file = spec_dir / "requirements.md"
        original_content = requirements_file.read_text()
        
        # Corrupt the file
        requirements_file.write_text("CORRUPTED CONTENT")
        
        # Try to validate - should detect corruption
        validation_result = workflow_orchestrator.validate_workflow(spec_id)
        assert not validation_result.is_valid
        assert any("corrupt" in error.message.lower() or "invalid" in error.message.lower() 
                  for error in validation_result.errors)
        
        # Restore file and verify recovery
        requirements_file.write_text(original_content)
        
        validation_result = workflow_orchestrator.validate_workflow(spec_id)
        assert validation_result.is_valid
        
        # Test invalid workflow transitions
        # Try to skip phases
        invalid_transition_state, invalid_validation = workflow_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.EXECUTION, approval=True
        )
        
        assert not invalid_validation.is_valid
        assert invalid_transition_state is None
        
        # Test invalid approvals
        invalid_approve_result, invalid_approve_validation = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Invalid approval"  # Should be requirements phase
        )
        
        assert not invalid_approve_validation.is_valid
        assert invalid_approve_result is None
        
        # Verify workflow is still in valid state
        current_state = workflow_orchestrator.get_workflow_state(spec_id)
        assert current_state.current_phase == WorkflowPhase.REQUIREMENTS
        assert current_state.status == WorkflowStatus.DRAFT
    
    def test_large_scale_workflow_performance_e2e(self, temp_workspace):
        """Test performance with large-scale workflows."""
        # Create a complex feature that should generate many requirements and tasks
        complex_feature_idea = """
        Enterprise resource planning system with comprehensive modules including:
        - Human resources management with employee records, payroll, benefits, performance tracking
        - Financial management with accounting, budgeting, reporting, tax compliance  
        - Supply chain management with procurement, inventory, vendor management
        - Customer relationship management with sales tracking, marketing automation
        - Project management with resource allocation, timeline tracking, collaboration tools
        - Business intelligence with data analytics, dashboards, predictive modeling
        - Document management with version control, workflow automation, compliance tracking
        - Integration capabilities with third-party systems, APIs, data synchronization
        - Security framework with role-based access, audit trails, data encryption
        - Mobile applications for field workers, managers, executives
        """
        
        import time
        start_time = time.time()
        
        orchestrator = WorkflowOrchestrator(temp_workspace)
        workflow_state, create_result = orchestrator.create_spec_workflow(
            complex_feature_idea, "enterprise-erp-system"
        )
        
        creation_time = time.time() - start_time
        
        assert create_result.success
        assert creation_time < 30  # Should complete within 30 seconds
        
        spec_id = workflow_state.spec_id
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        
        # Verify substantial content was generated
        requirements_content = (spec_dir / "requirements.md").read_text()
        assert len(requirements_content) > 3000  # Should be substantial
        
        # Count requirements
        requirement_count = len([line for line in requirements_content.split('\n') 
                               if line.strip().startswith('### Requirement')])
        assert requirement_count >= 5  # Complex system should have many requirements
        
        # Progress through design phase and measure performance
        start_time = time.time()
        
        approve_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Comprehensive requirements"
        )
        
        design_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        design_time = time.time() - start_time
        assert design_time < 45  # Design generation should complete within 45 seconds
        
        # Verify design content
        design_content = (spec_dir / "design.md").read_text()
        assert len(design_content) > 5000  # Should be comprehensive
        
        # Progress to tasks and measure
        start_time = time.time()
        
        approve_design_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Solid architecture"
        )
        
        tasks_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        tasks_time = time.time() - start_time
        assert tasks_time < 60  # Task generation should complete within 60 seconds
        
        # Verify task content
        tasks_content = (spec_dir / "tasks.md").read_text()
        assert len(tasks_content) > 4000  # Should be detailed
        
        # Count tasks
        task_count = len([line for line in tasks_content.split('\n') 
                         if line.strip().startswith('- [ ]')])
        assert task_count >= 15  # Complex system should have many tasks
    
    def test_workflow_metadata_and_versioning_e2e(self, workflow_orchestrator, temp_workspace):
        """Test workflow metadata tracking and versioning."""
        feature_idea = "versioning test feature"
        
        # Create workflow
        workflow_state, create_result = workflow_orchestrator.create_spec_workflow(feature_idea)
        assert create_result.success
        spec_id = workflow_state.spec_id
        
        # Check initial metadata
        initial_created_at = workflow_state.created_at
        initial_updated_at = workflow_state.updated_at
        initial_version = workflow_state.version
        
        assert initial_created_at is not None
        assert initial_updated_at is not None
        assert initial_version == "1.0.0"
        
        # Make changes and verify metadata updates
        import time
        time.sleep(0.1)  # Ensure timestamp difference
        
        approve_result, _ = workflow_orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Approved"
        )
        
        updated_state = workflow_orchestrator.get_workflow_state(spec_id)
        assert updated_state.updated_at > initial_updated_at
        assert updated_state.created_at == initial_created_at  # Should not change
        
        # Verify metadata persistence
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        metadata_file = spec_dir / ".spec-metadata.json"
        assert metadata_file.exists()
        
        metadata = json.loads(metadata_file.read_text())
        assert metadata["id"] == spec_id
        assert metadata["version"] == "1.0.0"
        assert "created_at" in metadata
        assert "updated_at" in metadata
        
        # Test version tracking through phases
        design_state, _ = workflow_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        # Verify version increments or metadata updates
        final_state = workflow_orchestrator.get_workflow_state(spec_id)
        assert final_state.updated_at > updated_state.updated_at


class TestWorkflowIntegrationScenarios:
    """Integration scenarios testing specific workflow combinations."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_multi_user_workflow_simulation(self, temp_workspace):
        """Simulate multi-user workflow interactions."""
        # This test simulates multiple users working on the same spec
        # by using different orchestrator instances
        
        feature_idea = "collaborative document editor with real-time sync"
        
        # User 1 creates the spec
        user1_orchestrator = WorkflowOrchestrator(temp_workspace)
        workflow_state, create_result = user1_orchestrator.create_spec_workflow(feature_idea)
        assert create_result.success
        spec_id = workflow_state.spec_id
        
        # User 1 reviews and rejects requirements
        reject_result, _ = user1_orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, False, 
            "Need more detail on conflict resolution"
        )
        
        # User 2 (different orchestrator instance) updates requirements
        user2_orchestrator = WorkflowOrchestrator(temp_workspace)
        
        requirements_changes = {
            "add_requirement": {
                "title": "Conflict Resolution",
                "user_story": "**User Story:** As a user, I want automatic conflict resolution, so that collaborative editing is seamless",
                "acceptance_criteria": "5.1. WHEN conflicts occur THEN system SHALL use operational transforms\n5.2. WHEN merging changes THEN system SHALL preserve user intent"
            }
        }
        
        updated_state, _ = user2_orchestrator.update_document(
            spec_id, DocumentType.REQUIREMENTS, requirements_changes
        )
        
        # User 1 approves updated requirements
        approve_result, _ = user1_orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, 
            "Much better with conflict resolution details"
        )
        
        # User 2 progresses to design
        design_state, _ = user2_orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        # Verify both users see consistent state
        user1_state = user1_orchestrator.get_workflow_state(spec_id)
        user2_state = user2_orchestrator.get_workflow_state(spec_id)
        
        assert user1_state.current_phase == user2_state.current_phase == WorkflowPhase.DESIGN
        assert user1_state.approvals["requirements"].approved == True
        assert user2_state.approvals["requirements"].approved == True
    
    def test_workflow_branching_and_merging_simulation(self, temp_workspace):
        """Simulate workflow branching scenarios."""
        # This test simulates creating alternative approaches within a workflow
        
        feature_idea = "payment processing system with multiple gateway support"
        
        orchestrator = WorkflowOrchestrator(temp_workspace)
        workflow_state, create_result = orchestrator.create_spec_workflow(feature_idea)
        assert create_result.success
        spec_id = workflow_state.spec_id
        
        # Progress to design phase
        approve_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Good requirements"
        )
        
        design_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        # Create "branch" by updating design with alternative approach
        original_design_content = (Path(temp_workspace) / ".kiro" / "specs" / spec_id / "design.md").read_text()
        
        # Update with alternative architecture
        alternative_changes = {
            "update_section": {
                "section": "Architecture",
                "content": """### Alternative Architecture: Event-Driven Approach

Instead of direct API calls to payment gateways, use an event-driven architecture:

1. **Payment Event Bus**: Central event processing for all payment operations
2. **Gateway Adapters**: Individual adapters for each payment provider
3. **Event Store**: Persistent storage for payment events and state
4. **Saga Orchestrator**: Manages complex payment workflows across services

This approach provides better resilience and easier testing."""
            }
        }
        
        updated_design_state, _ = orchestrator.update_document(
            spec_id, DocumentType.DESIGN, alternative_changes
        )
        
        # Verify alternative approach is reflected
        updated_design_content = (Path(temp_workspace) / ".kiro" / "specs" / spec_id / "design.md").read_text()
        assert "Event-Driven Approach" in updated_design_content
        assert "Payment Event Bus" in updated_design_content
        
        # Progress with alternative design
        approve_design_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Event-driven approach is more robust"
        )
        
        tasks_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        # Verify tasks reflect the alternative architecture
        tasks_content = (Path(temp_workspace) / ".kiro" / "specs" / spec_id / "tasks.md").read_text()
        assert "event" in tasks_content.lower()
        assert "saga" in tasks_content.lower() or "orchestrator" in tasks_content.lower()
    
    def test_workflow_rollback_and_recovery(self, temp_workspace):
        """Test workflow rollback and recovery scenarios."""
        feature_idea = "rollback test feature with complex requirements"
        
        orchestrator = WorkflowOrchestrator(temp_workspace)
        workflow_state, create_result = orchestrator.create_spec_workflow(feature_idea)
        assert create_result.success
        spec_id = workflow_state.spec_id
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        
        # Progress through multiple phases
        approve_req_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Initial approval"
        )
        
        design_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        approve_design_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Design approved"
        )
        
        tasks_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        # Simulate need to rollback to requirements due to major changes
        # In a real system, this might be a formal rollback operation
        # For this test, we'll simulate by transitioning back and updating
        
        # Go back to requirements phase (simulate rollback)
        rollback_state, rollback_validation = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.REQUIREMENTS
        )
        
        # Update requirements with major changes
        major_changes = {
            "add_requirement": {
                "title": "Major New Requirement",
                "user_story": "**User Story:** As a stakeholder, I want completely different functionality, so that business needs are met",
                "acceptance_criteria": "7.1. WHEN requirements change THEN system SHALL adapt architecture accordingly"
            }
        }
        
        updated_req_state, _ = orchestrator.update_document(
            spec_id, DocumentType.REQUIREMENTS, major_changes
        )
        
        # Re-approve and progress again
        re_approve_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Updated requirements approved"
        )
        
        new_design_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        # Verify new design reflects updated requirements
        new_design_content = (spec_dir / "design.md").read_text()
        assert "Major New Requirement" in new_design_content or "different functionality" in new_design_content.lower()
        
        # Verify workflow state is consistent
        final_state = orchestrator.get_workflow_state(spec_id)
        assert final_state.current_phase == WorkflowPhase.DESIGN
        assert final_state.approvals["requirements"].approved == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])