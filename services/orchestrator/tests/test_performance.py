"""
Performance and stress tests for spec-driven workflow system.

This module provides comprehensive performance testing for large spec handling,
memory usage, concurrent workflow execution, and system scalability.

Requirements addressed:
- System performance and scalability validation
- Large spec handling and memory usage testing
- Concurrent workflow execution stress testing
- Response time and resource usage benchmarking
"""

import pytest
import tempfile
import shutil
import time
import psutil
import threading
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple
from unittest.mock import Mock, patch
from dataclasses import dataclass

from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator
from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.generators import RequirementsGenerator, DesignGenerator, TasksGenerator
from eco_api.specs.task_execution_engine import TaskExecutionEngine
from eco_api.specs.models import WorkflowPhase, WorkflowStatus, TaskStatus


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    peak_memory_mb: float
    operations_per_second: float = 0.0
    success_rate: float = 100.0
    error_count: int = 0


class PerformanceMonitor:
    """Utility class for monitoring performance metrics."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.peak_memory = 0
        self.process = psutil.Process()
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
    
    def update_peak_memory(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        execution_time = end_time - self.start_time if self.start_time else 0
        memory_usage = end_memory - self.start_memory if self.start_memory else 0
        
        return PerformanceMetrics(
            execution_time=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_percent,
            peak_memory_mb=self.peak_memory
        )


class TestPerformanceLargeSpecs:
    """Performance tests for large specification handling."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for performance testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor."""
        return PerformanceMonitor()
    
    def generate_large_feature_idea(self, complexity_level: int) -> str:
        """Generate feature ideas of varying complexity."""
        base_modules = [
            "user management with authentication, authorization, and profile management",
            "product catalog with search, filtering, and recommendation engine",
            "shopping cart with session management, pricing calculations, and discount handling",
            "payment processing with multiple gateways, fraud detection, and transaction logging",
            "order management with workflow automation, status tracking, and fulfillment",
            "inventory management with stock tracking, reorder points, and supplier integration",
            "customer service with ticketing system, knowledge base, and chat support",
            "analytics dashboard with real-time metrics, reporting, and data visualization",
            "notification system with email, SMS, push notifications, and preference management",
            "content management with versioning, workflow approval, and media handling",
            "integration platform with API management, webhook handling, and data synchronization",
            "security framework with audit logging, compliance monitoring, and threat detection",
            "mobile applications with offline support, synchronization, and push notifications",
            "admin panel with user management, system configuration, and monitoring tools",
            "reporting engine with custom reports, scheduled delivery, and data export"
        ]
        
        selected_modules = base_modules[:min(complexity_level, len(base_modules))]
        
        return f"""
        Enterprise-grade platform with {complexity_level} integrated modules including:
        {chr(10).join(f'- {module}' for module in selected_modules)}
        
        The system requires:
        - Microservices architecture with service mesh
        - Event-driven communication with message queues
        - Distributed caching and session management
        - Multi-tenant architecture with data isolation
        - Horizontal scaling and load balancing
        - Comprehensive monitoring and observability
        - CI/CD pipeline with automated testing
        - Security compliance (SOC2, GDPR, HIPAA)
        - Performance optimization and caching strategies
        - Disaster recovery and backup systems
        """
    
    def test_large_spec_creation_performance(self, temp_workspace, performance_monitor):
        """Test performance of creating large, complex specifications."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        # Test different complexity levels
        complexity_levels = [5, 10, 15]
        results = {}
        
        for complexity in complexity_levels:
            feature_idea = self.generate_large_feature_idea(complexity)
            
            performance_monitor.start_monitoring()
            
            # Create spec
            workflow_state, create_result = orchestrator.create_spec_workflow(
                feature_idea, f"large-spec-{complexity}"
            )
            
            performance_monitor.update_peak_memory()
            metrics = performance_monitor.get_metrics()
            
            # Verify success
            assert create_result.success
            assert workflow_state is not None
            
            # Store results
            results[complexity] = metrics
            
            # Verify content quality scales with complexity
            spec_dir = Path(temp_workspace) / ".kiro" / "specs" / workflow_state.spec_id
            requirements_content = (spec_dir / "requirements.md").read_text()
            
            # More complex specs should generate more content
            assert len(requirements_content) > complexity * 200  # Rough scaling expectation
            
            # Performance assertions
            assert metrics.execution_time < 60  # Should complete within 60 seconds
            assert metrics.memory_usage_mb < 500  # Should not use excessive memory
        
        # Verify performance scales reasonably
        assert results[15].execution_time < results[5].execution_time * 5  # Not more than 5x slower
        
        print(f"Performance Results:")
        for complexity, metrics in results.items():
            print(f"  Complexity {complexity}: {metrics.execution_time:.2f}s, {metrics.memory_usage_mb:.1f}MB")
    
    def test_large_spec_workflow_progression_performance(self, temp_workspace, performance_monitor):
        """Test performance of progressing large specs through all phases."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        # Create a large, complex spec
        feature_idea = self.generate_large_feature_idea(12)
        
        performance_monitor.start_monitoring()
        
        # Phase 1: Create spec
        workflow_state, create_result = orchestrator.create_spec_workflow(
            feature_idea, "large-workflow-test"
        )
        
        assert create_result.success
        spec_id = workflow_state.spec_id
        
        phase_metrics = {}
        
        # Phase 2: Requirements to Design
        phase_start = time.time()
        
        approve_req_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Comprehensive requirements"
        )
        
        design_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=True
        )
        
        performance_monitor.update_peak_memory()
        phase_metrics['design_transition'] = time.time() - phase_start
        
        # Phase 3: Design to Tasks
        phase_start = time.time()
        
        approve_design_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True, "Solid architecture"
        )
        
        tasks_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.TASKS, approval=True
        )
        
        performance_monitor.update_peak_memory()
        phase_metrics['tasks_transition'] = time.time() - phase_start
        
        # Phase 4: Tasks to Execution
        phase_start = time.time()
        
        approve_tasks_result, _ = orchestrator.approve_phase(
            spec_id, WorkflowPhase.TASKS, True, "Detailed task breakdown"
        )
        
        execution_state, _ = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.EXECUTION, approval=True
        )
        
        performance_monitor.update_peak_memory()
        phase_metrics['execution_transition'] = time.time() - phase_start
        
        final_metrics = performance_monitor.get_metrics()
        
        # Performance assertions
        assert final_metrics.execution_time < 180  # Complete workflow within 3 minutes
        assert final_metrics.peak_memory_mb < 1000  # Peak memory under 1GB
        
        # Individual phase performance
        assert phase_metrics['design_transition'] < 60  # Design generation under 1 minute
        assert phase_metrics['tasks_transition'] < 90   # Task generation under 1.5 minutes
        assert phase_metrics['execution_transition'] < 10  # Execution transition under 10 seconds
        
        # Verify content quality
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / spec_id
        
        design_content = (spec_dir / "design.md").read_text()
        tasks_content = (spec_dir / "tasks.md").read_text()
        
        assert len(design_content) > 5000  # Substantial design document
        assert len(tasks_content) > 3000   # Detailed task breakdown
        
        # Count generated tasks
        task_count = len([line for line in tasks_content.split('\n') 
                         if line.strip().startswith('- [ ]')])
        assert task_count >= 20  # Complex spec should have many tasks
        
        print(f"Workflow Performance:")
        print(f"  Total time: {final_metrics.execution_time:.2f}s")
        print(f"  Peak memory: {final_metrics.peak_memory_mb:.1f}MB")
        print(f"  Design transition: {phase_metrics['design_transition']:.2f}s")
        print(f"  Tasks transition: {phase_metrics['tasks_transition']:.2f}s")
        print(f"  Generated tasks: {task_count}")
    
    def test_memory_usage_with_multiple_large_specs(self, temp_workspace, performance_monitor):
        """Test memory usage when handling multiple large specifications."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        performance_monitor.start_monitoring()
        
        # Create multiple large specs
        spec_count = 10
        created_specs = []
        
        for i in range(spec_count):
            feature_idea = self.generate_large_feature_idea(8)  # Medium complexity
            
            workflow_state, create_result = orchestrator.create_spec_workflow(
                feature_idea, f"multi-spec-{i+1}"
            )
            
            assert create_result.success
            created_specs.append(workflow_state.spec_id)
            
            performance_monitor.update_peak_memory()
            
            # Progress some specs to different phases
            if i % 3 == 0:  # Every 3rd spec to design
                approve_result, _ = orchestrator.approve_phase(
                    workflow_state.spec_id, WorkflowPhase.REQUIREMENTS, True, f"Approved {i}"
                )
                
                design_state, _ = orchestrator.transition_workflow(
                    workflow_state.spec_id, WorkflowPhase.DESIGN, approval=True
                )
                
                performance_monitor.update_peak_memory()
        
        final_metrics = performance_monitor.get_metrics()
        
        # Memory usage should scale reasonably
        memory_per_spec = final_metrics.peak_memory_mb / spec_count
        assert memory_per_spec < 100  # Less than 100MB per spec on average
        
        # Total memory should be reasonable
        assert final_metrics.peak_memory_mb < 1500  # Under 1.5GB total
        
        # Verify all specs are accessible
        workflow_list = orchestrator.list_workflows()
        assert len(workflow_list) == spec_count
        
        # Test random access performance
        access_times = []
        for spec_id in created_specs[:5]:  # Test first 5 specs
            start_time = time.time()
            
            retrieved_state = orchestrator.get_workflow_state(spec_id)
            assert retrieved_state is not None
            
            access_time = time.time() - start_time
            access_times.append(access_time)
        
        avg_access_time = sum(access_times) / len(access_times)
        assert avg_access_time < 0.1  # Average access under 100ms
        
        print(f"Multi-Spec Memory Usage:")
        print(f"  Total specs: {spec_count}")
        print(f"  Peak memory: {final_metrics.peak_memory_mb:.1f}MB")
        print(f"  Memory per spec: {memory_per_spec:.1f}MB")
        print(f"  Average access time: {avg_access_time*1000:.1f}ms")


class TestConcurrentWorkflowExecution:
    """Stress tests for concurrent workflow execution."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_concurrent_spec_creation(self, temp_workspace):
        """Test concurrent specification creation."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        def create_spec_worker(worker_id: int) -> Tuple[bool, float, str]:
            """Worker function for concurrent spec creation."""
            start_time = time.time()
            
            try:
                feature_idea = f"concurrent test feature {worker_id} with authentication and data management"
                
                workflow_state, create_result = orchestrator.create_spec_workflow(
                    feature_idea, f"concurrent-spec-{worker_id}"
                )
                
                execution_time = time.time() - start_time
                return create_result.success, execution_time, workflow_state.spec_id if create_result.success else ""
                
            except Exception as e:
                execution_time = time.time() - start_time
                return False, execution_time, str(e)
        
        # Run concurrent spec creation
        num_workers = 20
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(create_spec_worker, i) for i in range(num_workers)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_results = [r for r in results if r[0]]
        failed_results = [r for r in results if not r[0]]
        
        success_rate = len(successful_results) / len(results) * 100
        avg_execution_time = sum(r[1] for r in successful_results) / len(successful_results) if successful_results else 0
        
        # Performance assertions
        assert success_rate >= 90  # At least 90% success rate
        assert avg_execution_time < 30  # Average under 30 seconds
        
        # Verify file system integrity
        specs_dir = Path(temp_workspace) / ".kiro" / "specs"
        created_dirs = list(specs_dir.iterdir()) if specs_dir.exists() else []
        
        # Should have created directories for successful specs
        assert len(created_dirs) >= len(successful_results) * 0.9  # Allow for some cleanup issues
        
        print(f"Concurrent Creation Results:")
        print(f"  Workers: {num_workers}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average time: {avg_execution_time:.2f}s")
        print(f"  Failed: {len(failed_results)}")
    
    def test_concurrent_workflow_operations(self, temp_workspace):
        """Test concurrent operations on different workflows."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        # Pre-create specs for testing
        spec_ids = []
        for i in range(10):
            workflow_state, create_result = orchestrator.create_spec_workflow(
                f"test feature {i}", f"test-spec-{i}"
            )
            assert create_result.success
            spec_ids.append(workflow_state.spec_id)
        
        def workflow_operation_worker(spec_id: str, operation_type: str) -> Tuple[bool, float]:
            """Worker function for concurrent workflow operations."""
            start_time = time.time()
            
            try:
                if operation_type == "approve":
                    result, validation = orchestrator.approve_phase(
                        spec_id, WorkflowPhase.REQUIREMENTS, True, f"Approved by worker"
                    )
                    success = validation.is_valid
                    
                elif operation_type == "transition":
                    result, validation = orchestrator.transition_workflow(
                        spec_id, WorkflowPhase.DESIGN, approval=True
                    )
                    success = validation.is_valid
                    
                elif operation_type == "status":
                    state = orchestrator.get_workflow_state(spec_id)
                    success = state is not None
                    
                elif operation_type == "validate":
                    validation = orchestrator.validate_workflow(spec_id)
                    success = True  # Validation itself should always work
                    
                else:
                    success = False
                
                execution_time = time.time() - start_time
                return success, execution_time
                
            except Exception as e:
                execution_time = time.time() - start_time
                return False, execution_time
        
        # Create mixed concurrent operations
        operations = []
        for i, spec_id in enumerate(spec_ids):
            operations.extend([
                (spec_id, "status"),
                (spec_id, "validate"),
                (spec_id, "approve"),
            ])
        
        # Add some transition operations (these will fail for some specs but that's expected)
        for spec_id in spec_ids[:5]:
            operations.append((spec_id, "transition"))
        
        # Execute concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(workflow_operation_worker, spec_id, op_type) 
                      for spec_id, op_type in operations]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_results = [r for r in results if r[0]]
        success_rate = len(successful_results) / len(results) * 100
        avg_execution_time = sum(r[1] for r in successful_results) / len(successful_results) if successful_results else 0
        
        # Performance assertions
        assert success_rate >= 70  # At least 70% success rate (some operations expected to fail)
        assert avg_execution_time < 5   # Average under 5 seconds
        
        # Verify workflow states are consistent
        for spec_id in spec_ids:
            state = orchestrator.get_workflow_state(spec_id)
            assert state is not None
            assert state.spec_id == spec_id
        
        print(f"Concurrent Operations Results:")
        print(f"  Total operations: {len(operations)}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average time: {avg_execution_time:.3f}s")
    
    def test_concurrent_task_execution_simulation(self, temp_workspace):
        """Test concurrent task execution simulation."""
        # Create orchestrator and task engine
        orchestrator = WorkflowOrchestrator(temp_workspace)
        task_engine = TaskExecutionEngine(temp_workspace)
        
        # Create and progress a spec to execution phase
        workflow_state, create_result = orchestrator.create_spec_workflow(
            "concurrent task execution test feature", "concurrent-task-test"
        )
        assert create_result.success
        spec_id = workflow_state.spec_id
        
        # Progress through phases quickly
        orchestrator.approve_phase(spec_id, WorkflowPhase.REQUIREMENTS, True, "Approved")
        orchestrator.transition_workflow(spec_id, WorkflowPhase.DESIGN, approval=True)
        orchestrator.approve_phase(spec_id, WorkflowPhase.DESIGN, True, "Approved")
        orchestrator.transition_workflow(spec_id, WorkflowPhase.TASKS, approval=True)
        orchestrator.approve_phase(spec_id, WorkflowPhase.TASKS, True, "Approved")
        orchestrator.transition_workflow(spec_id, WorkflowPhase.EXECUTION, approval=True)
        
        def task_operation_worker(operation_type: str, task_id: str = None) -> Tuple[bool, float]:
            """Worker function for concurrent task operations."""
            start_time = time.time()
            
            try:
                if operation_type == "progress":
                    progress, result = task_engine.calculate_progress(spec_id)
                    success = result.is_valid
                    
                elif operation_type == "context":
                    context, result = task_engine.load_execution_context(spec_id)
                    success = result.is_valid
                    
                elif operation_type == "next_task":
                    next_task, result = task_engine.get_next_task(spec_id)
                    success = result.is_valid
                    
                elif operation_type == "status_update" and task_id:
                    result = task_engine.update_task_status(spec_id, task_id, TaskStatus.IN_PROGRESS)
                    success = result.is_valid
                    
                elif operation_type == "execute" and task_id:
                    # Mock execution for performance testing
                    with patch.object(task_engine, '_execute_task_implementation') as mock_exec:
                        from eco_api.specs.task_execution_engine import TaskResult
                        mock_exec.return_value = TaskResult(
                            task_id=task_id, success=True, message="Mock execution"
                        )
                        result = task_engine.execute_task(spec_id, task_id)
                        success = result.success
                else:
                    success = False
                
                execution_time = time.time() - start_time
                return success, execution_time
                
            except Exception as e:
                execution_time = time.time() - start_time
                return False, execution_time
        
        # Create concurrent task operations
        operations = []
        
        # Add read operations (these should always work)
        for _ in range(20):
            operations.extend([
                ("progress", None),
                ("context", None),
                ("next_task", None),
            ])
        
        # Add some write operations
        for i in range(5):
            operations.extend([
                ("status_update", "1"),
                ("status_update", "2"),
            ])
        
        # Execute concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(task_operation_worker, op_type, task_id) 
                      for op_type, task_id in operations]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_results = [r for r in results if r[0]]
        success_rate = len(successful_results) / len(results) * 100
        avg_execution_time = sum(r[1] for r in successful_results) / len(successful_results) if successful_results else 0
        
        # Performance assertions
        assert success_rate >= 85  # At least 85% success rate
        assert avg_execution_time < 2   # Average under 2 seconds
        
        print(f"Concurrent Task Operations Results:")
        print(f"  Total operations: {len(operations)}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average time: {avg_execution_time:.3f}s")


class TestResponseTimeAndResourceUsage:
    """Benchmark tests for response times and resource usage."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_api_response_time_benchmarks(self, temp_workspace):
        """Benchmark API response times for various operations."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        # Create test specs for benchmarking
        test_specs = []
        for i in range(5):
            workflow_state, create_result = orchestrator.create_spec_workflow(
                f"benchmark test feature {i}", f"benchmark-spec-{i}"
            )
            assert create_result.success
            test_specs.append(workflow_state.spec_id)
        
        benchmark_results = {}
        
        # Benchmark spec creation
        creation_times = []
        for i in range(10):
            start_time = time.time()
            
            workflow_state, create_result = orchestrator.create_spec_workflow(
                f"benchmark creation test {i}", f"creation-benchmark-{i}"
            )
            
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            
            assert create_result.success
        
        benchmark_results['spec_creation'] = {
            'avg_time': sum(creation_times) / len(creation_times),
            'max_time': max(creation_times),
            'min_time': min(creation_times)
        }
        
        # Benchmark spec retrieval
        retrieval_times = []
        for _ in range(50):  # More iterations for read operations
            spec_id = test_specs[_ % len(test_specs)]
            
            start_time = time.time()
            state = orchestrator.get_workflow_state(spec_id)
            retrieval_time = time.time() - start_time
            
            retrieval_times.append(retrieval_time)
            assert state is not None
        
        benchmark_results['spec_retrieval'] = {
            'avg_time': sum(retrieval_times) / len(retrieval_times),
            'max_time': max(retrieval_times),
            'min_time': min(retrieval_times)
        }
        
        # Benchmark workflow transitions
        transition_times = []
        for spec_id in test_specs:
            # Approve requirements
            start_time = time.time()
            
            approve_result, _ = orchestrator.approve_phase(
                spec_id, WorkflowPhase.REQUIREMENTS, True, "Benchmark approval"
            )
            
            # Transition to design
            design_state, _ = orchestrator.transition_workflow(
                spec_id, WorkflowPhase.DESIGN, approval=True
            )
            
            transition_time = time.time() - start_time
            transition_times.append(transition_time)
        
        benchmark_results['workflow_transition'] = {
            'avg_time': sum(transition_times) / len(transition_times),
            'max_time': max(transition_times),
            'min_time': min(transition_times)
        }
        
        # Benchmark spec listing
        listing_times = []
        for _ in range(20):
            start_time = time.time()
            
            workflow_list = orchestrator.list_workflows()
            
            listing_time = time.time() - start_time
            listing_times.append(listing_time)
            
            assert len(workflow_list) >= len(test_specs)
        
        benchmark_results['spec_listing'] = {
            'avg_time': sum(listing_times) / len(listing_times),
            'max_time': max(listing_times),
            'min_time': min(listing_times)
        }
        
        # Performance assertions
        assert benchmark_results['spec_creation']['avg_time'] < 15  # Average creation under 15s
        assert benchmark_results['spec_retrieval']['avg_time'] < 0.1  # Average retrieval under 100ms
        assert benchmark_results['workflow_transition']['avg_time'] < 30  # Average transition under 30s
        assert benchmark_results['spec_listing']['avg_time'] < 0.5  # Average listing under 500ms
        
        # Print benchmark results
        print("\nAPI Response Time Benchmarks:")
        for operation, metrics in benchmark_results.items():
            print(f"  {operation}:")
            print(f"    Average: {metrics['avg_time']*1000:.1f}ms")
            print(f"    Min: {metrics['min_time']*1000:.1f}ms")
            print(f"    Max: {metrics['max_time']*1000:.1f}ms")
    
    def test_memory_usage_patterns(self, temp_workspace):
        """Test memory usage patterns under various loads."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        process = psutil.Process()
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        memory_measurements = []
        
        # Test memory usage during spec creation
        for i in range(20):
            workflow_state, create_result = orchestrator.create_spec_workflow(
                f"memory test feature {i} with comprehensive requirements", 
                f"memory-test-{i}"
            )
            assert create_result.success
            
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory - baseline_memory)
        
        # Test memory usage during workflow progression
        for i in range(0, 10, 2):  # Progress every other spec
            spec_id = f"memory-test-{i}"
            
            orchestrator.approve_phase(spec_id, WorkflowPhase.REQUIREMENTS, True, "Approved")
            orchestrator.transition_workflow(spec_id, WorkflowPhase.DESIGN, approval=True)
            
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory - baseline_memory)
        
        # Analyze memory usage
        max_memory_usage = max(memory_measurements)
        avg_memory_usage = sum(memory_measurements) / len(memory_measurements)
        
        # Memory usage assertions
        assert max_memory_usage < 1000  # Peak memory under 1GB
        assert avg_memory_usage < 500   # Average memory under 500MB
        
        # Test memory cleanup
        # Force garbage collection and measure
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_after_gc = final_memory - baseline_memory
        
        # Memory should not grow excessively
        assert memory_after_gc < max_memory_usage * 1.2  # Allow 20% overhead
        
        print(f"\nMemory Usage Patterns:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Peak usage: {max_memory_usage:.1f}MB")
        print(f"  Average usage: {avg_memory_usage:.1f}MB")
        print(f"  After GC: {memory_after_gc:.1f}MB")
    
    def test_file_system_performance(self, temp_workspace):
        """Test file system operation performance."""
        file_manager = FileSystemManager(temp_workspace)
        
        # Test directory creation performance
        creation_times = []
        for i in range(100):
            start_time = time.time()
            
            spec_id, result = file_manager.create_spec_directory(f"fs-perf-test-{i}")
            
            creation_time = time.time() - start_time
            creation_times.append(creation_time)
            
            assert result.success
        
        # Test file write performance
        write_times = []
        test_content = "# Test Document\n\n" + "Test content line.\n" * 1000  # ~17KB content
        
        for i in range(50):
            spec_id = f"fs-perf-test-{i}"
            
            start_time = time.time()
            
            from eco_api.specs.models import SpecDocument, DocumentType, DocumentMetadata
            from datetime import datetime
            
            doc = SpecDocument(
                type=DocumentType.REQUIREMENTS,
                content=test_content,
                metadata=DocumentMetadata(
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    version="1.0.0",
                    checksum="test_checksum"
                )
            )
            
            result = file_manager.save_document(spec_id, doc)
            
            write_time = time.time() - start_time
            write_times.append(write_time)
            
            assert result.success
        
        # Test file read performance
        read_times = []
        for i in range(50):
            spec_id = f"fs-perf-test-{i}"
            
            start_time = time.time()
            
            doc, result = file_manager.load_document(spec_id, DocumentType.REQUIREMENTS)
            
            read_time = time.time() - start_time
            read_times.append(read_time)
            
            assert result.success
            assert len(doc.content) > 1000
        
        # Performance assertions
        avg_creation_time = sum(creation_times) / len(creation_times)
        avg_write_time = sum(write_times) / len(write_times)
        avg_read_time = sum(read_times) / len(read_times)
        
        assert avg_creation_time < 0.1  # Directory creation under 100ms
        assert avg_write_time < 0.1     # File write under 100ms
        assert avg_read_time < 0.05     # File read under 50ms
        
        print(f"\nFile System Performance:")
        print(f"  Directory creation: {avg_creation_time*1000:.1f}ms")
        print(f"  File write: {avg_write_time*1000:.1f}ms")
        print(f"  File read: {avg_read_time*1000:.1f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print output