"""
Benchmark tests for response times and resource usage.

This module provides comprehensive benchmarking for the spec-driven workflow
system to establish performance baselines and identify optimization opportunities.

Requirements addressed:
- Response time and resource usage benchmarking
- Performance baseline establishment
- System optimization guidance
- Scalability measurement and analysis
"""

import pytest
import tempfile
import shutil
import time
import psutil
import statistics
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from unittest.mock import Mock, patch

from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator
from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.task_execution_engine import TaskExecutionEngine
from eco_api.specs.generators import RequirementsGenerator, DesignGenerator, TasksGenerator
from eco_api.specs.models import WorkflowPhase, WorkflowStatus, TaskStatus, DocumentType


@dataclass
class BenchmarkResult:
    """Container for benchmark measurement results."""
    operation_name: str
    sample_size: int
    mean_time: float
    median_time: float
    min_time: float
    max_time: float
    std_deviation: float
    percentile_95: float
    percentile_99: float
    operations_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class BenchmarkRunner:
    """Utility class for running performance benchmarks."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.orchestrator = WorkflowOrchestrator(workspace_path)
        self.task_engine = TaskExecutionEngine(workspace_path)
        self.file_manager = FileSystemManager(workspace_path)
        self.process = psutil.Process()
    
    def run_benchmark(self, operation_func, operation_name: str, 
                     iterations: int = 100, warmup_iterations: int = 10) -> BenchmarkResult:
        """Run a benchmark for the given operation."""
        # Warmup runs
        for _ in range(warmup_iterations):
            try:
                operation_func()
            except Exception:
                pass  # Ignore warmup errors
        
        # Actual benchmark runs
        execution_times = []
        memory_measurements = []
        cpu_measurements = []
        
        for i in range(iterations):
            # Measure memory before operation
            memory_before = self.process.memory_info().rss / 1024 / 1024
            
            # Measure execution time
            start_time = time.perf_counter()
            
            try:
                operation_func()
                success = True
            except Exception as e:
                success = False
                print(f"Benchmark iteration {i} failed: {e}")
            
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            if success:
                execution_times.append(execution_time)
                
                # Measure memory after operation
                memory_after = self.process.memory_info().rss / 1024 / 1024
                memory_measurements.append(memory_after)
                
                # Measure CPU usage
                cpu_percent = self.process.cpu_percent()
                cpu_measurements.append(cpu_percent)
        
        # Calculate statistics
        if execution_times:
            mean_time = statistics.mean(execution_times)
            median_time = statistics.median(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            std_deviation = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
            
            # Calculate percentiles
            sorted_times = sorted(execution_times)
            percentile_95 = sorted_times[int(0.95 * len(sorted_times))]
            percentile_99 = sorted_times[int(0.99 * len(sorted_times))]
            
            operations_per_second = 1.0 / mean_time if mean_time > 0 else 0
            
            avg_memory = statistics.mean(memory_measurements) if memory_measurements else 0
            avg_cpu = statistics.mean(cpu_measurements) if cpu_measurements else 0
            
            return BenchmarkResult(
                operation_name=operation_name,
                sample_size=len(execution_times),
                mean_time=mean_time,
                median_time=median_time,
                min_time=min_time,
                max_time=max_time,
                std_deviation=std_deviation,
                percentile_95=percentile_95,
                percentile_99=percentile_99,
                operations_per_second=operations_per_second,
                memory_usage_mb=avg_memory,
                cpu_usage_percent=avg_cpu
            )
        else:
            # All iterations failed
            return BenchmarkResult(
                operation_name=operation_name,
                sample_size=0,
                mean_time=0,
                median_time=0,
                min_time=0,
                max_time=0,
                std_deviation=0,
                percentile_95=0,
                percentile_99=0,
                operations_per_second=0,
                memory_usage_mb=0,
                cpu_usage_percent=0
            )

class TestWorkflowOperationBenchmarks:
    """Benchmark tests for core workflow operations."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for benchmarking."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def benchmark_runner(self, temp_workspace):
        """Create benchmark runner."""
        return BenchmarkRunner(temp_workspace)
    
    @pytest.fixture
    def sample_specs(self, benchmark_runner):
        """Create sample specs for benchmarking."""
        specs = []
        for i in range(10):
            workflow_state, result = benchmark_runner.orchestrator.create_spec_workflow(
                f"benchmark test feature {i}", f"benchmark-spec-{i}"
            )
            if result.success:
                specs.append(workflow_state.spec_id)
        return specs
    
    def test_spec_creation_benchmark(self, benchmark_runner):
        """Benchmark spec creation performance."""
        
        creation_counter = 0
        
        def create_spec_operation():
            nonlocal creation_counter
            feature_idea = f"benchmark creation test feature {creation_counter} with authentication and data management"
            spec_name = f"creation-benchmark-{creation_counter}"
            creation_counter += 1
            
            workflow_state, result = benchmark_runner.orchestrator.create_spec_workflow(
                feature_idea, spec_name
            )
            
            if not result.success:
                raise Exception(f"Spec creation failed: {result.message}")
            
            return workflow_state
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=create_spec_operation,
            operation_name="spec_creation",
            iterations=50,
            warmup_iterations=5
        )
        
        # Performance assertions
        assert result.sample_size >= 45, f"Too many failed iterations: {result.sample_size}/50"
        assert result.mean_time <= 20, f"Mean creation time too high: {result.mean_time:.2f}s"
        assert result.percentile_95 <= 30, f"95th percentile too high: {result.percentile_95:.2f}s"
        assert result.operations_per_second >= 0.05, f"Throughput too low: {result.operations_per_second:.3f} ops/sec"
        
        print(f"\nSpec Creation Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time:.3f}s")
        print(f"  Median time: {result.median_time:.3f}s")
        print(f"  95th percentile: {result.percentile_95:.3f}s")
        print(f"  Operations/sec: {result.operations_per_second:.3f}")
        print(f"  Memory usage: {result.memory_usage_mb:.1f}MB")
    
    def test_spec_retrieval_benchmark(self, benchmark_runner, sample_specs):
        """Benchmark spec retrieval performance."""
        
        retrieval_counter = 0
        
        def retrieve_spec_operation():
            nonlocal retrieval_counter
            spec_id = sample_specs[retrieval_counter % len(sample_specs)]
            retrieval_counter += 1
            
            state = benchmark_runner.orchestrator.get_workflow_state(spec_id)
            
            if state is None:
                raise Exception(f"Failed to retrieve spec: {spec_id}")
            
            return state
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=retrieve_spec_operation,
            operation_name="spec_retrieval",
            iterations=200,
            warmup_iterations=20
        )
        
        # Performance assertions
        assert result.sample_size >= 190, f"Too many failed iterations: {result.sample_size}/200"
        assert result.mean_time <= 0.1, f"Mean retrieval time too high: {result.mean_time:.4f}s"
        assert result.percentile_95 <= 0.2, f"95th percentile too high: {result.percentile_95:.4f}s"
        assert result.operations_per_second >= 10, f"Throughput too low: {result.operations_per_second:.1f} ops/sec"
        
        print(f"\nSpec Retrieval Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  Median time: {result.median_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")
    
    def test_workflow_transition_benchmark(self, benchmark_runner):
        """Benchmark workflow transition performance."""
        
        # Pre-create specs for transition testing
        transition_specs = []
        for i in range(20):
            workflow_state, result = benchmark_runner.orchestrator.create_spec_workflow(
                f"transition benchmark feature {i}", f"transition-benchmark-{i}"
            )
            if result.success:
                transition_specs.append(workflow_state.spec_id)
        
        transition_counter = 0
        
        def transition_operation():
            nonlocal transition_counter
            spec_id = transition_specs[transition_counter % len(transition_specs)]
            transition_counter += 1
            
            # Get current state
            current_state = benchmark_runner.orchestrator.get_workflow_state(spec_id)
            if not current_state:
                raise Exception(f"Could not get workflow state for {spec_id}")
            
            # Perform transition based on current phase
            if current_state.current_phase == WorkflowPhase.REQUIREMENTS:
                # Approve and transition to design
                approve_result, validation = benchmark_runner.orchestrator.approve_phase(
                    spec_id, WorkflowPhase.REQUIREMENTS, True, f"Benchmark approval {transition_counter}"
                )
                
                if not validation.is_valid:
                    raise Exception(f"Requirements approval failed: {validation.errors}")
                
                design_state, validation = benchmark_runner.orchestrator.transition_workflow(
                    spec_id, WorkflowPhase.DESIGN, approval=True
                )
                
                if not validation.is_valid:
                    raise Exception(f"Design transition failed: {validation.errors}")
                
                return design_state
            
            else:
                # Just validate for other phases
                validation = benchmark_runner.orchestrator.validate_workflow(spec_id)
                if not validation.is_valid:
                    raise Exception(f"Validation failed: {validation.errors}")
                return current_state
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=transition_operation,
            operation_name="workflow_transition",
            iterations=30,
            warmup_iterations=3
        )
        
        # Performance assertions
        assert result.sample_size >= 25, f"Too many failed iterations: {result.sample_size}/30"
        assert result.mean_time <= 45, f"Mean transition time too high: {result.mean_time:.2f}s"
        assert result.percentile_95 <= 60, f"95th percentile too high: {result.percentile_95:.2f}s"
        
        print(f"\nWorkflow Transition Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time:.2f}s")
        print(f"  Median time: {result.median_time:.2f}s")
        print(f"  95th percentile: {result.percentile_95:.2f}s")
        print(f"  Operations/sec: {result.operations_per_second:.3f}")
    
    def test_spec_listing_benchmark(self, benchmark_runner, sample_specs):
        """Benchmark spec listing performance."""
        
        def list_specs_operation():
            workflows = benchmark_runner.orchestrator.list_workflows()
            
            if len(workflows) < len(sample_specs):
                raise Exception(f"Expected at least {len(sample_specs)} workflows, got {len(workflows)}")
            
            return workflows
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=list_specs_operation,
            operation_name="spec_listing",
            iterations=100,
            warmup_iterations=10
        )
        
        # Performance assertions
        assert result.sample_size >= 95, f"Too many failed iterations: {result.sample_size}/100"
        assert result.mean_time <= 0.5, f"Mean listing time too high: {result.mean_time:.3f}s"
        assert result.percentile_95 <= 1.0, f"95th percentile too high: {result.percentile_95:.3f}s"
        assert result.operations_per_second >= 2, f"Throughput too low: {result.operations_per_second:.1f} ops/sec"
        
        print(f"\nSpec Listing Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  Median time: {result.median_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")


class TestFileSystemBenchmarks:
    """Benchmark tests for file system operations."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def benchmark_runner(self, temp_workspace):
        """Create benchmark runner."""
        return BenchmarkRunner(temp_workspace)
    
    def test_file_creation_benchmark(self, benchmark_runner):
        """Benchmark file creation performance."""
        
        creation_counter = 0
        
        def create_file_operation():
            nonlocal creation_counter
            spec_id, result = benchmark_runner.file_manager.create_spec_directory(
                f"file-benchmark-{creation_counter}"
            )
            creation_counter += 1
            
            if not result.success:
                raise Exception(f"Directory creation failed: {result.message}")
            
            return spec_id
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=create_file_operation,
            operation_name="file_creation",
            iterations=200,
            warmup_iterations=20
        )
        
        # Performance assertions
        assert result.sample_size >= 190, f"Too many failed iterations: {result.sample_size}/200"
        assert result.mean_time <= 0.1, f"Mean creation time too high: {result.mean_time:.4f}s"
        assert result.percentile_95 <= 0.2, f"95th percentile too high: {result.percentile_95:.4f}s"
        
        print(f"\nFile Creation Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")
    
    def test_document_write_benchmark(self, benchmark_runner):
        """Benchmark document write performance."""
        
        # Pre-create directories
        spec_dirs = []
        for i in range(50):
            spec_id, result = benchmark_runner.file_manager.create_spec_directory(f"write-benchmark-{i}")
            if result.success:
                spec_dirs.append(spec_id)
        
        write_counter = 0
        test_content = "# Test Document\n\n" + "Test content line.\n" * 500  # ~8.5KB content
        
        def write_document_operation():
            nonlocal write_counter
            spec_id = spec_dirs[write_counter % len(spec_dirs)]
            write_counter += 1
            
            from eco_api.specs.models import SpecDocument, DocumentType, DocumentMetadata
            
            doc = SpecDocument(
                type=DocumentType.REQUIREMENTS,
                content=test_content,
                metadata=DocumentMetadata(
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    version="1.0.0",
                    checksum=f"checksum_{write_counter}"
                )
            )
            
            result = benchmark_runner.file_manager.save_document(spec_id, doc)
            
            if not result.success:
                raise Exception(f"Document write failed: {result.message}")
            
            return result
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=write_document_operation,
            operation_name="document_write",
            iterations=100,
            warmup_iterations=10
        )
        
        # Performance assertions
        assert result.sample_size >= 95, f"Too many failed iterations: {result.sample_size}/100"
        assert result.mean_time <= 0.1, f"Mean write time too high: {result.mean_time:.4f}s"
        assert result.percentile_95 <= 0.2, f"95th percentile too high: {result.percentile_95:.4f}s"
        
        print(f"\nDocument Write Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")
    
    def test_document_read_benchmark(self, benchmark_runner):
        """Benchmark document read performance."""
        
        # Pre-create documents
        spec_docs = []
        test_content = "# Test Document\n\n" + "Test content line.\n" * 500
        
        for i in range(50):
            spec_id, result = benchmark_runner.file_manager.create_spec_directory(f"read-benchmark-{i}")
            if result.success:
                from eco_api.specs.models import SpecDocument, DocumentType, DocumentMetadata
                
                doc = SpecDocument(
                    type=DocumentType.REQUIREMENTS,
                    content=test_content,
                    metadata=DocumentMetadata(
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        version="1.0.0",
                        checksum=f"checksum_{i}"
                    )
                )
                
                save_result = benchmark_runner.file_manager.save_document(spec_id, doc)
                if save_result.success:
                    spec_docs.append(spec_id)
        
        read_counter = 0
        
        def read_document_operation():
            nonlocal read_counter
            spec_id = spec_docs[read_counter % len(spec_docs)]
            read_counter += 1
            
            doc, result = benchmark_runner.file_manager.load_document(spec_id, DocumentType.REQUIREMENTS)
            
            if not result.success:
                raise Exception(f"Document read failed: {result.message}")
            
            if len(doc.content) < 1000:
                raise Exception(f"Document content too short: {len(doc.content)}")
            
            return doc
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=read_document_operation,
            operation_name="document_read",
            iterations=200,
            warmup_iterations=20
        )
        
        # Performance assertions
        assert result.sample_size >= 190, f"Too many failed iterations: {result.sample_size}/200"
        assert result.mean_time <= 0.05, f"Mean read time too high: {result.mean_time:.4f}s"
        assert result.percentile_95 <= 0.1, f"95th percentile too high: {result.percentile_95:.4f}s"
        
        print(f"\nDocument Read Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")


class TestTaskExecutionBenchmarks:
    """Benchmark tests for task execution operations."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def benchmark_runner(self, temp_workspace):
        """Create benchmark runner."""
        return BenchmarkRunner(temp_workspace)
    
    @pytest.fixture
    def execution_ready_spec(self, benchmark_runner):
        """Create a spec ready for task execution."""
        workflow_state, result = benchmark_runner.orchestrator.create_spec_workflow(
            "task execution benchmark feature", "task-exec-benchmark"
        )
        assert result.success
        
        spec_id = workflow_state.spec_id
        
        # Progress to execution phase
        benchmark_runner.orchestrator.approve_phase(spec_id, WorkflowPhase.REQUIREMENTS, True, "Approved")
        benchmark_runner.orchestrator.transition_workflow(spec_id, WorkflowPhase.DESIGN, approval=True)
        benchmark_runner.orchestrator.approve_phase(spec_id, WorkflowPhase.DESIGN, True, "Approved")
        benchmark_runner.orchestrator.transition_workflow(spec_id, WorkflowPhase.TASKS, approval=True)
        benchmark_runner.orchestrator.approve_phase(spec_id, WorkflowPhase.TASKS, True, "Approved")
        benchmark_runner.orchestrator.transition_workflow(spec_id, WorkflowPhase.EXECUTION, approval=True)
        
        return spec_id
    
    def test_context_loading_benchmark(self, benchmark_runner, execution_ready_spec):
        """Benchmark execution context loading performance."""
        
        def load_context_operation():
            context, result = benchmark_runner.task_engine.load_execution_context(execution_ready_spec)
            
            if not result.is_valid:
                raise Exception(f"Context loading failed: {result.errors}")
            
            if context is None:
                raise Exception("Context is None")
            
            return context
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=load_context_operation,
            operation_name="context_loading",
            iterations=100,
            warmup_iterations=10
        )
        
        # Performance assertions
        assert result.sample_size >= 95, f"Too many failed iterations: {result.sample_size}/100"
        assert result.mean_time <= 0.5, f"Mean context loading time too high: {result.mean_time:.3f}s"
        assert result.percentile_95 <= 1.0, f"95th percentile too high: {result.percentile_95:.3f}s"
        
        print(f"\nContext Loading Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")
    
    def test_progress_calculation_benchmark(self, benchmark_runner, execution_ready_spec):
        """Benchmark progress calculation performance."""
        
        def calculate_progress_operation():
            progress, result = benchmark_runner.task_engine.calculate_progress(execution_ready_spec)
            
            if not result.is_valid:
                raise Exception(f"Progress calculation failed: {result.errors}")
            
            if 'total_tasks' not in progress:
                raise Exception("Invalid progress data")
            
            return progress
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=calculate_progress_operation,
            operation_name="progress_calculation",
            iterations=100,
            warmup_iterations=10
        )
        
        # Performance assertions
        assert result.sample_size >= 95, f"Too many failed iterations: {result.sample_size}/100"
        assert result.mean_time <= 0.2, f"Mean progress calculation time too high: {result.mean_time:.3f}s"
        assert result.percentile_95 <= 0.5, f"95th percentile too high: {result.percentile_95:.3f}s"
        
        print(f"\nProgress Calculation Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")
    
    def test_task_status_update_benchmark(self, benchmark_runner, execution_ready_spec):
        """Benchmark task status update performance."""
        
        status_counter = 0
        
        def update_task_status_operation():
            nonlocal status_counter
            task_id = "1"  # Assume task 1 exists
            status = TaskStatus.IN_PROGRESS if status_counter % 2 == 0 else TaskStatus.NOT_STARTED
            status_counter += 1
            
            result = benchmark_runner.task_engine.update_task_status(execution_ready_spec, task_id, status)
            
            if not result.is_valid:
                raise Exception(f"Task status update failed: {result.errors}")
            
            return result
        
        # Run benchmark
        result = benchmark_runner.run_benchmark(
            operation_func=update_task_status_operation,
            operation_name="task_status_update",
            iterations=100,
            warmup_iterations=10
        )
        
        # Performance assertions
        assert result.sample_size >= 95, f"Too many failed iterations: {result.sample_size}/100"
        assert result.mean_time <= 0.2, f"Mean status update time too high: {result.mean_time:.3f}s"
        assert result.percentile_95 <= 0.5, f"95th percentile too high: {result.percentile_95:.3f}s"
        
        print(f"\nTask Status Update Benchmark Results:")
        print(f"  Sample size: {result.sample_size}")
        print(f"  Mean time: {result.mean_time*1000:.1f}ms")
        print(f"  95th percentile: {result.percentile_95*1000:.1f}ms")
        print(f"  Operations/sec: {result.operations_per_second:.1f}")


class TestScalabilityBenchmarks:
    """Benchmark tests for system scalability."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_scalability_with_spec_count(self, temp_workspace):
        """Benchmark performance scaling with number of specs."""
        orchestrator = WorkflowOrchestrator(temp_workspace)
        
        spec_counts = [10, 50, 100, 200]
        scalability_results = {}
        
        for spec_count in spec_counts:
            # Create specs
            created_specs = []
            creation_start = time.time()
            
            for i in range(spec_count):
                workflow_state, result = orchestrator.create_spec_workflow(
                    f"scalability test spec {i}", f"scalability-{spec_count}-{i}"
                )
                if result.success:
                    created_specs.append(workflow_state.spec_id)
            
            creation_time = time.time() - creation_start
            
            # Benchmark operations with this number of specs
            retrieval_times = []
            listing_times = []
            
            # Test retrieval performance
            for _ in range(20):
                if created_specs:
                    spec_id = created_specs[_ % len(created_specs)]
                    
                    start_time = time.time()
                    state = orchestrator.get_workflow_state(spec_id)
                    retrieval_time = time.time() - start_time
                    
                    if state:
                        retrieval_times.append(retrieval_time)
            
            # Test listing performance
            for _ in range(10):
                start_time = time.time()
                workflows = orchestrator.list_workflows()
                listing_time = time.time() - start_time
                
                if len(workflows) >= len(created_specs):
                    listing_times.append(listing_time)
            
            # Store results
            scalability_results[spec_count] = {
                'created_specs': len(created_specs),
                'creation_time': creation_time,
                'avg_retrieval_time': statistics.mean(retrieval_times) if retrieval_times else 0,
                'avg_listing_time': statistics.mean(listing_times) if listing_times else 0,
                'creation_rate': len(created_specs) / creation_time if creation_time > 0 else 0
            }
        
        # Analyze scalability
        print(f"\nScalability Benchmark Results:")
        for spec_count, metrics in scalability_results.items():
            print(f"  {spec_count} specs:")
            print(f"    Creation rate: {metrics['creation_rate']:.2f} specs/sec")
            print(f"    Retrieval time: {metrics['avg_retrieval_time']*1000:.1f}ms")
            print(f"    Listing time: {metrics['avg_listing_time']*1000:.1f}ms")
        
        # Scalability assertions
        # Retrieval time should not degrade significantly
        retrieval_10 = scalability_results[10]['avg_retrieval_time']
        retrieval_200 = scalability_results[200]['avg_retrieval_time']
        
        if retrieval_10 > 0:
            retrieval_degradation = retrieval_200 / retrieval_10
            assert retrieval_degradation <= 5, f"Retrieval performance degraded too much: {retrieval_degradation:.1f}x"
        
        # Listing time should scale reasonably
        listing_10 = scalability_results[10]['avg_listing_time']
        listing_200 = scalability_results[200]['avg_listing_time']
        
        if listing_10 > 0:
            listing_degradation = listing_200 / listing_10
            assert listing_degradation <= 20, f"Listing performance degraded too much: {listing_degradation:.1f}x"


class TestBenchmarkReporting:
    """Utilities for benchmark reporting and analysis."""
    
    def test_generate_benchmark_report(self, temp_workspace):
        """Generate comprehensive benchmark report."""
        # This test runs a subset of benchmarks and generates a report
        
        benchmark_runner = BenchmarkRunner(temp_workspace)
        report_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'python_version': f"{psutil.Process().exe}",
            },
            'benchmarks': {}
        }
        
        # Run key benchmarks
        benchmarks_to_run = [
            ('spec_creation', lambda: benchmark_runner.orchestrator.create_spec_workflow(
                "report test feature", f"report-test-{time.time()}"
            )),
            ('spec_listing', lambda: benchmark_runner.orchestrator.list_workflows()),
        ]
        
        for benchmark_name, operation in benchmarks_to_run:
            try:
                result = benchmark_runner.run_benchmark(
                    operation_func=operation,
                    operation_name=benchmark_name,
                    iterations=20,
                    warmup_iterations=2
                )
                
                report_data['benchmarks'][benchmark_name] = result.to_dict()
                
            except Exception as e:
                report_data['benchmarks'][benchmark_name] = {
                    'error': str(e),
                    'operation_name': benchmark_name
                }
        
        # Save report
        report_file = Path(temp_workspace) / "benchmark_report.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        # Verify report was created
        assert report_file.exists()
        assert report_file.stat().st_size > 100  # Should have substantial content
        
        print(f"\nBenchmark report saved to: {report_file}")
        print(f"Report contains {len(report_data['benchmarks'])} benchmark results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print output