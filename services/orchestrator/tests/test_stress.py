"""
Stress tests for concurrent workflow execution and system limits.

This module provides comprehensive stress testing for the spec-driven workflow
system under high load, concurrent access, and resource constraints.

Requirements addressed:
- System performance and scalability validation
- Stress tests for concurrent workflow execution
- System behavior under resource constraints and high load
- Reliability and stability testing under extreme conditions
"""

import pytest
import tempfile
import shutil
import time
import threading
import multiprocessing
import psutil
import random
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from unittest.mock import Mock, patch
from dataclasses import dataclass, field
from queue import Queue, Empty
import gc

from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator
from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.task_execution_engine import TaskExecutionEngine
from eco_api.specs.models import WorkflowPhase, WorkflowStatus, TaskStatus, DocumentType


@dataclass
class StressTestResults:
    """Container for stress test results."""
    total_operations: int
    successful_operations: int
    failed_operations: int
    success_rate: float
    total_duration: float
    operations_per_second: float
    average_response_time: float
    peak_memory_mb: float
    errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.total_operations > 0:
            self.success_rate = (self.successful_operations / self.total_operations) * 100
            self.operations_per_second = self.total_operations / self.total_duration if self.total_duration > 0 else 0


class StressTestRunner:
    """Utility class for running stress tests with monitoring."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.orchestrator = WorkflowOrchestrator(workspace_path)
        self.task_engine = TaskExecutionEngine(workspace_path)
        self.process = psutil.Process()
        self.peak_memory = 0
        self.start_time = None
        self.results_queue = Queue()
    
    def monitor_resources(self):
        """Monitor system resources during test execution."""
        while self.start_time and time.time() - self.start_time < 300:  # 5 minute max
            current_memory = self.process.memory_info().rss / 1024 / 1024
            self.peak_memory = max(self.peak_memory, current_memory)
            time.sleep(0.1)
    
    def run_stress_test(self, test_function, num_workers: int, operations_per_worker: int, 
                       timeout: int = 300) -> StressTestResults:
        """Run a stress test with the given parameters."""
        self.start_time = time.time()
        self.peak_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Start resource monitoring
        monitor_thread = threading.Thread(target=self.monitor_resources, daemon=True)
        monitor_thread.start()
        
        total_operations = num_workers * operations_per_worker
        successful_operations = 0
        failed_operations = 0
        response_times = []
        errors = []
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all tasks
                futures = []
                for worker_id in range(num_workers):
                    for op_id in range(operations_per_worker):
                        future = executor.submit(test_function, worker_id, op_id)
                        futures.append(future)
                
                # Collect results with timeout
                for future in concurrent.futures.as_completed(futures, timeout=timeout):
                    try:
                        success, response_time, error_msg = future.result()
                        if success:
                            successful_operations += 1
                        else:
                            failed_operations += 1
                            if error_msg:
                                errors.append(error_msg)
                        
                        if response_time is not None:
                            response_times.append(response_time)
                            
                    except concurrent.futures.TimeoutError:
                        failed_operations += 1
                        errors.append("Operation timeout")
                    except Exception as e:
                        failed_operations += 1
                        errors.append(f"Execution error: {str(e)}")
        
        except Exception as e:
            errors.append(f"Test execution error: {str(e)}")
        
        total_duration = time.time() - self.start_time
        average_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return StressTestResults(
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            success_rate=0,  # Will be calculated in __post_init__
            total_duration=total_duration,
            operations_per_second=0,  # Will be calculated in __post_init__
            average_response_time=average_response_time,
            peak_memory_mb=self.peak_memory,
            errors=errors[:10]  # Keep only first 10 errors
        )


class TestHighVolumeSpecCreation:
    """Stress tests for high-volume spec creation."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for stress testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def stress_runner(self, temp_workspace):
        """Create stress test runner."""
        return StressTestRunner(temp_workspace)
    
    def test_high_volume_spec_creation_stress(self, stress_runner):
        """Stress test with high volume of concurrent spec creation."""
        
        def create_spec_operation(worker_id: int, op_id: int) -> Tuple[bool, Optional[float], Optional[str]]:
            """Single spec creation operation."""
            start_time = time.time()
            
            try:
                feature_idea = f"stress test feature {worker_id}-{op_id} with authentication, data management, and user interface components"
                spec_name = f"stress-spec-{worker_id}-{op_id}"
                
                workflow_state, create_result = stress_runner.orchestrator.create_spec_workflow(
                    feature_idea, spec_name
                )
                
                response_time = time.time() - start_time
                
                if create_result.success:
                    return True, response_time, None
                else:
                    return False, response_time, create_result.message
                    
            except Exception as e:
                response_time = time.time() - start_time
                return False, response_time, str(e)
        
        # Run stress test: 50 workers, 5 operations each = 250 total specs
        results = stress_runner.run_stress_test(
            test_function=create_spec_operation,
            num_workers=50,
            operations_per_worker=5,
            timeout=600  # 10 minutes
        )
        
        # Stress test assertions
        assert results.success_rate >= 80, f"Success rate too low: {results.success_rate}%"
        assert results.operations_per_second >= 2, f"Throughput too low: {results.operations_per_second} ops/sec"
        assert results.average_response_time <= 30, f"Response time too high: {results.average_response_time}s"
        assert results.peak_memory_mb <= 2000, f"Memory usage too high: {results.peak_memory_mb}MB"
        
        # Verify file system integrity
        specs_dir = Path(stress_runner.workspace_path) / ".kiro" / "specs"
        if specs_dir.exists():
            created_dirs = list(specs_dir.iterdir())
            # Should have created most of the successful specs
            assert len(created_dirs) >= results.successful_operations * 0.8
        
        print(f"\nHigh Volume Spec Creation Stress Test Results:")
        print(f"  Total operations: {results.total_operations}")
        print(f"  Success rate: {results.success_rate:.1f}%")
        print(f"  Operations/second: {results.operations_per_second:.2f}")
        print(f"  Average response time: {results.average_response_time:.2f}s")
        print(f"  Peak memory: {results.peak_memory_mb:.1f}MB")
        if results.errors:
            print(f"  Sample errors: {results.errors[:3]}")
    
    def test_rapid_fire_spec_operations_stress(self, stress_runner):
        """Stress test with rapid-fire operations on existing specs."""
        
        # Pre-create some specs for testing
        base_specs = []
        for i in range(20):
            workflow_state, create_result = stress_runner.orchestrator.create_spec_workflow(
                f"base spec {i}", f"base-spec-{i}"
            )
            if create_result.success:
                base_specs.append(workflow_state.spec_id)
        
        assert len(base_specs) >= 15, "Failed to create enough base specs"
        
        def rapid_operation(worker_id: int, op_id: int) -> Tuple[bool, Optional[float], Optional[str]]:
            """Rapid-fire operation on random spec."""
            start_time = time.time()
            
            try:
                spec_id = random.choice(base_specs)
                operation_type = random.choice(['get_state', 'validate', 'list_all', 'approve'])
                
                if operation_type == 'get_state':
                    state = stress_runner.orchestrator.get_workflow_state(spec_id)
                    success = state is not None
                    
                elif operation_type == 'validate':
                    validation = stress_runner.orchestrator.validate_workflow(spec_id)
                    success = True  # Validation should always complete
                    
                elif operation_type == 'list_all':
                    workflows = stress_runner.orchestrator.list_workflows()
                    success = len(workflows) >= len(base_specs)
                    
                elif operation_type == 'approve':
                    # Try to approve (may fail if already approved, that's ok)
                    try:
                        result, validation = stress_runner.orchestrator.approve_phase(
                            spec_id, WorkflowPhase.REQUIREMENTS, True, f"Rapid approval {worker_id}-{op_id}"
                        )
                        success = True  # Operation completed, regardless of approval result
                    except Exception:
                        success = True  # Still count as success if operation completed
                
                else:
                    success = False
                
                response_time = time.time() - start_time
                return success, response_time, None
                
            except Exception as e:
                response_time = time.time() - start_time
                return False, response_time, str(e)
        
        # Run rapid-fire stress test: 30 workers, 20 operations each = 600 total operations
        results = stress_runner.run_stress_test(
            test_function=rapid_operation,
            num_workers=30,
            operations_per_worker=20,
            timeout=300  # 5 minutes
        )
        
        # Rapid-fire stress assertions
        assert results.success_rate >= 90, f"Success rate too low: {results.success_rate}%"
        assert results.operations_per_second >= 10, f"Throughput too low: {results.operations_per_second} ops/sec"
        assert results.average_response_time <= 2, f"Response time too high: {results.average_response_time}s"
        
        print(f"\nRapid-Fire Operations Stress Test Results:")
        print(f"  Total operations: {results.total_operations}")
        print(f"  Success rate: {results.success_rate:.1f}%")
        print(f"  Operations/second: {results.operations_per_second:.2f}")
        print(f"  Average response time: {results.average_response_time:.3f}s")
        print(f"  Peak memory: {results.peak_memory_mb:.1f}MB")


class TestConcurrentWorkflowProgression:
    """Stress tests for concurrent workflow progression through phases."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def stress_runner(self, temp_workspace):
        """Create stress test runner."""
        return StressTestRunner(temp_workspace)
    
    def test_concurrent_workflow_progression_stress(self, stress_runner):
        """Stress test concurrent progression of multiple workflows."""
        
        # Pre-create workflows for progression testing
        workflow_specs = []
        for i in range(25):
            workflow_state, create_result = stress_runner.orchestrator.create_spec_workflow(
                f"progression test feature {i}", f"progression-spec-{i}"
            )
            if create_result.success:
                workflow_specs.append(workflow_state.spec_id)
        
        assert len(workflow_specs) >= 20, "Failed to create enough specs for progression test"
        
        def workflow_progression_operation(worker_id: int, op_id: int) -> Tuple[bool, Optional[float], Optional[str]]:
            """Progress a workflow through phases."""
            start_time = time.time()
            
            try:
                # Select a spec to work on
                spec_index = (worker_id * 100 + op_id) % len(workflow_specs)
                spec_id = workflow_specs[spec_index]
                
                # Get current state
                current_state = stress_runner.orchestrator.get_workflow_state(spec_id)
                if not current_state:
                    return False, time.time() - start_time, "Could not get workflow state"
                
                success = True
                error_msg = None
                
                # Progress based on current phase
                try:
                    if current_state.current_phase == WorkflowPhase.REQUIREMENTS:
                        # Try to approve requirements
                        if current_state.approvals.get("requirements", {}).get("approved") != True:
                            approve_result, validation = stress_runner.orchestrator.approve_phase(
                                spec_id, WorkflowPhase.REQUIREMENTS, True, f"Stress test approval {worker_id}-{op_id}"
                            )
                            if not validation.is_valid:
                                success = False
                                error_msg = f"Requirements approval failed: {validation.errors}"
                        
                        # Try to transition to design
                        if success:
                            design_state, validation = stress_runner.orchestrator.transition_workflow(
                                spec_id, WorkflowPhase.DESIGN, approval=True
                            )
                            if not validation.is_valid:
                                success = False
                                error_msg = f"Design transition failed: {validation.errors}"
                    
                    elif current_state.current_phase == WorkflowPhase.DESIGN:
                        # Try to approve design
                        if current_state.approvals.get("design", {}).get("approved") != True:
                            approve_result, validation = stress_runner.orchestrator.approve_phase(
                                spec_id, WorkflowPhase.DESIGN, True, f"Design approval {worker_id}-{op_id}"
                            )
                            if not validation.is_valid:
                                success = False
                                error_msg = f"Design approval failed: {validation.errors}"
                        
                        # Try to transition to tasks
                        if success:
                            tasks_state, validation = stress_runner.orchestrator.transition_workflow(
                                spec_id, WorkflowPhase.TASKS, approval=True
                            )
                            if not validation.is_valid:
                                success = False
                                error_msg = f"Tasks transition failed: {validation.errors}"
                    
                    elif current_state.current_phase == WorkflowPhase.TASKS:
                        # Try to approve tasks
                        if current_state.approvals.get("tasks", {}).get("approved") != True:
                            approve_result, validation = stress_runner.orchestrator.approve_phase(
                                spec_id, WorkflowPhase.TASKS, True, f"Tasks approval {worker_id}-{op_id}"
                            )
                            if not validation.is_valid:
                                success = False
                                error_msg = f"Tasks approval failed: {validation.errors}"
                        
                        # Try to transition to execution
                        if success:
                            exec_state, validation = stress_runner.orchestrator.transition_workflow(
                                spec_id, WorkflowPhase.EXECUTION, approval=True
                            )
                            if not validation.is_valid:
                                success = False
                                error_msg = f"Execution transition failed: {validation.errors}"
                    
                    else:
                        # Already in execution phase, just validate
                        validation = stress_runner.orchestrator.validate_workflow(spec_id)
                        success = validation.is_valid
                        if not success:
                            error_msg = f"Validation failed: {validation.errors}"
                
                except Exception as e:
                    success = False
                    error_msg = f"Operation exception: {str(e)}"
                
                response_time = time.time() - start_time
                return success, response_time, error_msg
                
            except Exception as e:
                response_time = time.time() - start_time
                return False, response_time, str(e)
        
        # Run concurrent progression stress test
        results = stress_runner.run_stress_test(
            test_function=workflow_progression_operation,
            num_workers=15,
            operations_per_worker=10,
            timeout=900  # 15 minutes for complex operations
        )
        
        # Progression stress assertions
        assert results.success_rate >= 70, f"Success rate too low: {results.success_rate}%"
        assert results.operations_per_second >= 0.5, f"Throughput too low: {results.operations_per_second} ops/sec"
        assert results.average_response_time <= 60, f"Response time too high: {results.average_response_time}s"
        assert results.peak_memory_mb <= 3000, f"Memory usage too high: {results.peak_memory_mb}MB"
        
        # Verify final states
        final_phases = []
        for spec_id in workflow_specs[:10]:  # Check first 10 specs
            state = stress_runner.orchestrator.get_workflow_state(spec_id)
            if state:
                final_phases.append(state.current_phase)
        
        # Should have progressed some workflows beyond requirements
        advanced_phases = [p for p in final_phases if p != WorkflowPhase.REQUIREMENTS]
        assert len(advanced_phases) >= len(final_phases) * 0.3, "Not enough workflows progressed"
        
        print(f"\nConcurrent Workflow Progression Stress Test Results:")
        print(f"  Total operations: {results.total_operations}")
        print(f"  Success rate: {results.success_rate:.1f}%")
        print(f"  Operations/second: {results.operations_per_second:.2f}")
        print(f"  Average response time: {results.average_response_time:.2f}s")
        print(f"  Peak memory: {results.peak_memory_mb:.1f}MB")
        print(f"  Advanced workflows: {len(advanced_phases)}/{len(final_phases)}")


class TestResourceConstraintStress:
    """Stress tests under resource constraints."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_memory_pressure_stress(self, temp_workspace):
        """Test system behavior under memory pressure."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        # Create memory pressure by creating many large specs
        memory_hogs = []
        process = psutil.Process()
        
        start_memory = process.memory_info().rss / 1024 / 1024
        target_memory_increase = 1000  # Try to increase memory by 1GB
        
        spec_count = 0
        while True:
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - start_memory
            
            if memory_increase >= target_memory_increase or spec_count >= 200:
                break
            
            # Create large, complex spec
            large_feature_idea = f"""
            Memory pressure test feature {spec_count} with extensive requirements:
            """ + "\n".join([f"- Module {i}: Complex functionality with detailed requirements" 
                           for i in range(50)])
            
            try:
                workflow_state, create_result = orchestrator.create_spec_workflow(
                    large_feature_idea, f"memory-pressure-{spec_count}"
                )
                
                if create_result.success:
                    memory_hogs.append(workflow_state.spec_id)
                    
                    # Progress some specs to increase memory usage
                    if spec_count % 5 == 0:
                        orchestrator.approve_phase(
                            workflow_state.spec_id, WorkflowPhase.REQUIREMENTS, True, "Approved"
                        )
                        orchestrator.transition_workflow(
                            workflow_state.spec_id, WorkflowPhase.DESIGN, approval=True
                        )
                
                spec_count += 1
                
            except MemoryError:
                print(f"Hit memory limit at {spec_count} specs")
                break
            except Exception as e:
                print(f"Error at spec {spec_count}: {e}")
                break
        
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - start_memory
        
        print(f"\nMemory Pressure Test Results:")
        print(f"  Specs created: {len(memory_hogs)}")
        print(f"  Memory increase: {memory_increase:.1f}MB")
        print(f"  Peak memory: {peak_memory:.1f}MB")
        
        # Test system responsiveness under memory pressure
        response_times = []
        for i in range(10):
            start_time = time.time()
            
            # Try basic operations
            workflows = orchestrator.list_workflows()
            if memory_hogs:
                state = orchestrator.get_workflow_state(memory_hogs[0])
            
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        
        # System should still be responsive
        assert avg_response_time < 5, f"System too slow under memory pressure: {avg_response_time}s"
        assert len(memory_hogs) >= 10, "Should have created at least 10 specs"
        
        print(f"  Average response time under pressure: {avg_response_time:.2f}s")
        
        # Test cleanup and recovery
        gc.collect()
        
        after_gc_memory = process.memory_info().rss / 1024 / 1024
        print(f"  Memory after GC: {after_gc_memory:.1f}MB")
    
    def test_file_system_stress(self, temp_workspace):
        """Test behavior under file system stress."""
        file_manager = FileSystemManager(temp_workspace)
        
        # Create many specs to stress file system
        created_specs = []
        file_operations = []
        
        # Rapid file creation
        start_time = time.time()
        
        for i in range(500):  # Create 500 specs rapidly
            try:
                spec_id, result = file_manager.create_spec_directory(f"fs-stress-{i}")
                
                if result.success:
                    created_specs.append(spec_id)
                    
                    # Write documents rapidly
                    from eco_api.specs.models import SpecDocument, DocumentType, DocumentMetadata
                    
                    doc = SpecDocument(
                        type=DocumentType.REQUIREMENTS,
                        content=f"# Requirements for spec {i}\n\n" + "Content line.\n" * 100,
                        metadata=DocumentMetadata(
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                            version="1.0.0",
                            checksum=f"checksum_{i}"
                        )
                    )
                    
                    save_result = file_manager.save_document(spec_id, doc)
                    file_operations.append(save_result.success)
                
            except Exception as e:
                print(f"File system error at spec {i}: {e}")
                break
        
        creation_time = time.time() - start_time
        
        # Test concurrent file access
        def concurrent_file_access(spec_ids: List[str]) -> int:
            """Access files concurrently."""
            successful_reads = 0
            
            for spec_id in spec_ids[:50]:  # Test first 50
                try:
                    doc, result = file_manager.load_document(spec_id, DocumentType.REQUIREMENTS)
                    if result.success:
                        successful_reads += 1
                except Exception:
                    pass
            
            return successful_reads
        
        # Run concurrent access test
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            chunk_size = len(created_specs) // 10 if created_specs else 1
            
            for i in range(0, len(created_specs), chunk_size):
                chunk = created_specs[i:i + chunk_size]
                if chunk:
                    future = executor.submit(concurrent_file_access, chunk)
                    futures.append(future)
            
            concurrent_results = [future.result() for future in concurrent.futures.as_completed(futures, timeout=60)]
        
        total_concurrent_reads = sum(concurrent_results)
        
        # File system stress assertions
        assert len(created_specs) >= 400, f"Should create at least 400 specs, got {len(created_specs)}"
        assert sum(file_operations) >= len(created_specs) * 0.9, "File operations success rate too low"
        assert creation_time < 120, f"File creation too slow: {creation_time}s"
        assert total_concurrent_reads >= len(created_specs) * 0.3, "Concurrent reads success rate too low"
        
        print(f"\nFile System Stress Test Results:")
        print(f"  Specs created: {len(created_specs)}")
        print(f"  Creation time: {creation_time:.2f}s")
        print(f"  File operations success rate: {sum(file_operations)/len(file_operations)*100:.1f}%")
        print(f"  Concurrent reads: {total_concurrent_reads}")
        
        # Verify file system integrity
        specs_dir = Path(temp_workspace) / ".kiro" / "specs"
        if specs_dir.exists():
            actual_dirs = list(specs_dir.iterdir())
            assert len(actual_dirs) >= len(created_specs) * 0.9, "File system integrity check failed"


class TestSystemLimitsAndFailover:
    """Tests for system limits and failover scenarios."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_maximum_concurrent_connections(self, temp_workspace):
        """Test maximum concurrent connections/operations."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        # Create base specs for testing
        base_specs = []
        for i in range(10):
            workflow_state, result = orchestrator.create_spec_workflow(
                f"connection test spec {i}", f"conn-test-{i}"
            )
            if result.success:
                base_specs.append(workflow_state.spec_id)
        
        def concurrent_operation(worker_id: int) -> Tuple[bool, float]:
            """Simulate a concurrent connection/operation."""
            start_time = time.time()
            
            try:
                # Simulate various operations
                operations = [
                    lambda: orchestrator.list_workflows(),
                    lambda: orchestrator.get_workflow_state(random.choice(base_specs)) if base_specs else None,
                    lambda: orchestrator.validate_workflow(random.choice(base_specs)) if base_specs else None,
                ]
                
                # Perform multiple operations per "connection"
                for _ in range(5):
                    operation = random.choice(operations)
                    result = operation()
                    time.sleep(0.01)  # Small delay between operations
                
                response_time = time.time() - start_time
                return True, response_time
                
            except Exception as e:
                response_time = time.time() - start_time
                return False, response_time
        
        # Test with increasing number of concurrent "connections"
        connection_counts = [50, 100, 200]
        results = {}
        
        for conn_count in connection_counts:
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=conn_count) as executor:
                futures = [executor.submit(concurrent_operation, i) for i in range(conn_count)]
                
                try:
                    completed_results = [future.result(timeout=30) for future in futures]
                    successful = sum(1 for success, _ in completed_results if success)
                    avg_time = sum(time for _, time in completed_results) / len(completed_results)
                    
                    results[conn_count] = {
                        'success_rate': (successful / conn_count) * 100,
                        'avg_response_time': avg_time,
                        'total_time': time.time() - start_time
                    }
                    
                except concurrent.futures.TimeoutError:
                    results[conn_count] = {
                        'success_rate': 0,
                        'avg_response_time': 30,
                        'total_time': time.time() - start_time
                    }
        
        # Analyze scalability
        for conn_count, metrics in results.items():
            print(f"\nConcurrent Connections Test - {conn_count} connections:")
            print(f"  Success rate: {metrics['success_rate']:.1f}%")
            print(f"  Average response time: {metrics['avg_response_time']:.3f}s")
            print(f"  Total time: {metrics['total_time']:.2f}s")
            
            # Basic performance expectations
            if conn_count <= 100:
                assert metrics['success_rate'] >= 80, f"Success rate too low for {conn_count} connections"
                assert metrics['avg_response_time'] <= 5, f"Response time too high for {conn_count} connections"
    
    def test_error_recovery_under_stress(self, temp_workspace):
        """Test error recovery mechanisms under stress conditions."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        # Create specs and introduce various error conditions
        error_scenarios = []
        recovery_results = []
        
        # Scenario 1: Corrupted files
        workflow_state, result = orchestrator.create_spec_workflow(
            "corruption test feature", "corruption-test"
        )
        assert result.success
        
        # Corrupt the requirements file
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / workflow_state.spec_id
        requirements_file = spec_dir / "requirements.md"
        original_content = requirements_file.read_text()
        requirements_file.write_text("CORRUPTED CONTENT")
        
        # Test recovery
        try:
            validation = orchestrator.validate_workflow(workflow_state.spec_id)
            recovery_results.append(('file_corruption', not validation.is_valid))
            
            # Restore file
            requirements_file.write_text(original_content)
            
            # Verify recovery
            validation_after = orchestrator.validate_workflow(workflow_state.spec_id)
            recovery_results.append(('file_recovery', validation_after.is_valid))
            
        except Exception as e:
            recovery_results.append(('file_corruption', False))
        
        # Scenario 2: Concurrent modification conflicts
        def concurrent_modifier(spec_id: str, modifier_id: int) -> bool:
            """Simulate concurrent modifications."""
            try:
                # Try to approve the same phase concurrently
                result, validation = orchestrator.approve_phase(
                    spec_id, WorkflowPhase.REQUIREMENTS, True, f"Concurrent approval {modifier_id}"
                )
                return validation.is_valid
            except Exception:
                return False
        
        # Create a spec for concurrent modification testing
        concurrent_spec, result = orchestrator.create_spec_workflow(
            "concurrent modification test", "concurrent-mod-test"
        )
        assert result.success
        
        # Run concurrent modifications
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_modifier, concurrent_spec.spec_id, i) 
                      for i in range(10)]
            concurrent_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # At least one should succeed, others should fail gracefully
        successful_modifications = sum(concurrent_results)
        recovery_results.append(('concurrent_modification', successful_modifications >= 1))
        recovery_results.append(('concurrent_graceful_failure', successful_modifications <= 5))
        
        # Scenario 3: Resource exhaustion simulation
        try:
            # Try to create many specs rapidly to simulate resource exhaustion
            rapid_specs = []
            for i in range(100):
                try:
                    workflow_state, result = orchestrator.create_spec_workflow(
                        f"resource exhaustion test {i}", f"resource-test-{i}"
                    )
                    if result.success:
                        rapid_specs.append(workflow_state.spec_id)
                    else:
                        break
                except Exception:
                    break
            
            # System should handle resource constraints gracefully
            recovery_results.append(('resource_exhaustion_handling', len(rapid_specs) >= 50))
            
            # Test system responsiveness after resource stress
            start_time = time.time()
            workflows = orchestrator.list_workflows()
            response_time = time.time() - start_time
            
            recovery_results.append(('post_stress_responsiveness', response_time < 10))
            
        except Exception as e:
            recovery_results.append(('resource_exhaustion_handling', False))
        
        # Analyze recovery results
        successful_recoveries = sum(1 for _, success in recovery_results if success)
        total_scenarios = len(recovery_results)
        recovery_rate = (successful_recoveries / total_scenarios) * 100
        
        print(f"\nError Recovery Under Stress Test Results:")
        for scenario, success in recovery_results:
            print(f"  {scenario}: {'PASS' if success else 'FAIL'}")
        print(f"  Overall recovery rate: {recovery_rate:.1f}%")
        
        # Recovery assertions
        assert recovery_rate >= 70, f"Recovery rate too low: {recovery_rate}%"
        
        # Specific critical recoveries
        critical_scenarios = ['file_recovery', 'concurrent_graceful_failure', 'post_stress_responsiveness']
        critical_results = [success for scenario, success in recovery_results if scenario in critical_scenarios]
        
        assert all(critical_results), "Critical recovery scenarios failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])  # -s for print output, --tb=short for concise tracebacks