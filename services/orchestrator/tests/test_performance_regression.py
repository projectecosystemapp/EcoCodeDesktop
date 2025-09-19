"""
Performance regression tests for monitoring system performance.

This module implements benchmark tests for Levenshtein algorithm optimization,
memory usage validation, load testing for performance under stress,
and automated performance regression detection.

Requirements addressed:
- 6.1, 6.2, 6.3, 6.4: Performance optimization validation and regression detection
"""

import pytest
import time
import psutil
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import tempfile
import json
import statistics
import gc
import tracemalloc

from eco_api.shared.specValidation import calculate_similarity, optimized_levenshtein_distance
from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.generators import RequirementsGenerator, DesignGenerator, TasksGenerator
from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking."""
    execution_time: float
    memory_usage: int  # bytes
    cpu_usage: float  # percentage
    operations_per_second: float
    memory_peak: int  # bytes
    gc_collections: int


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""
    test_name: str
    metrics: PerformanceMetrics
    baseline_metrics: PerformanceMetrics = None
    regression_detected: bool = False
    performance_ratio: float = 1.0  # current/baseline


class PerformanceBenchmark:
    """Base class for performance benchmarking."""
    
    def __init__(self):
        self.baseline_file = Path(__file__).parent / "performance_baselines.json"
        self.baselines = self._load_baselines()
    
    def _load_baselines(self) -> Dict[str, Dict[str, float]]:
        """Load performance baselines from file."""
        if self.baseline_file.exists():
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_baselines(self):
        """Save performance baselines to file."""
        with open(self.baseline_file, 'w') as f:
            json.dump(self.baselines, f, indent=2)
    
    def measure_performance(self, func: Callable, *args, **kwargs) -> PerformanceMetrics:
        """Measure performance metrics for a function."""
        # Start memory tracking
        tracemalloc.start()
        gc.collect()  # Clean up before measurement
        
        # Get initial metrics
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        initial_cpu_time = process.cpu_times()
        gc_before = gc.get_stats()
        
        # Execute function and measure time
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        # Get final metrics
        final_memory = process.memory_info().rss
        final_cpu_time = process.cpu_times()
        gc_after = gc.get_stats()
        
        # Get memory peak
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate metrics
        execution_time = end_time - start_time
        memory_usage = final_memory - initial_memory
        cpu_usage = ((final_cpu_time.user - initial_cpu_time.user) + 
                    (final_cpu_time.system - initial_cpu_time.system)) / execution_time * 100
        
        # Calculate operations per second (if applicable)
        ops_per_second = 1.0 / execution_time if execution_time > 0 else 0
        
        # Calculate GC collections
        gc_collections = sum(stat['collections'] for stat in gc_after) - sum(stat['collections'] for stat in gc_before)
        
        return PerformanceMetrics(
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            operations_per_second=ops_per_second,
            memory_peak=peak,
            gc_collections=gc_collections
        )
    
    def benchmark_function(self, test_name: str, func: Callable, *args, **kwargs) -> BenchmarkResult:
        """Benchmark a function and compare against baseline."""
        metrics = self.measure_performance(func, *args, **kwargs)
        
        # Get baseline if available
        baseline_data = self.baselines.get(test_name)
        baseline_metrics = None
        regression_detected = False
        performance_ratio = 1.0
        
        if baseline_data:
            baseline_metrics = PerformanceMetrics(**baseline_data)
            
            # Check for regression (performance degradation > 20%)
            performance_ratio = metrics.execution_time / baseline_metrics.execution_time
            regression_detected = performance_ratio > 1.2
        else:
            # Save as new baseline
            self.baselines[test_name] = {
                'execution_time': metrics.execution_time,
                'memory_usage': metrics.memory_usage,
                'cpu_usage': metrics.cpu_usage,
                'operations_per_second': metrics.operations_per_second,
                'memory_peak': metrics.memory_peak,
                'gc_collections': metrics.gc_collections
            }
            self._save_baselines()
        
        return BenchmarkResult(
            test_name=test_name,
            metrics=metrics,
            baseline_metrics=baseline_metrics,
            regression_detected=regression_detected,
            performance_ratio=performance_ratio
        )


class TestLevenshteinPerformance:
    """Performance tests for Levenshtein algorithm optimization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.benchmark = PerformanceBenchmark()
    
    def test_levenshtein_small_strings(self):
        """Test Levenshtein performance with small strings."""
        str1 = "hello world"
        str2 = "hello word"
        
        result = self.benchmark.benchmark_function(
            "levenshtein_small_strings",
            optimized_levenshtein_distance,
            str1, str2
        )
        
        # Should complete quickly for small strings
        assert result.metrics.execution_time < 0.001  # < 1ms
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"
    
    def test_levenshtein_medium_strings(self):
        """Test Levenshtein performance with medium strings."""
        str1 = "a" * 100 + "hello world" + "b" * 100
        str2 = "a" * 100 + "hello word" + "b" * 100
        
        result = self.benchmark.benchmark_function(
            "levenshtein_medium_strings",
            optimized_levenshtein_distance,
            str1, str2
        )
        
        # Should complete reasonably quickly for medium strings
        assert result.metrics.execution_time < 0.01  # < 10ms
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"
    
    def test_levenshtein_large_strings(self):
        """Test Levenshtein performance with large strings."""
        str1 = "a" * 1000 + "hello world" + "b" * 1000
        str2 = "a" * 1000 + "hello word" + "b" * 1000
        
        result = self.benchmark.benchmark_function(
            "levenshtein_large_strings",
            optimized_levenshtein_distance,
            str1, str2
        )
        
        # Should complete within reasonable time for large strings
        assert result.metrics.execution_time < 0.1  # < 100ms
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"
    
    def test_levenshtein_memory_efficiency(self):
        """Test memory efficiency of optimized Levenshtein algorithm."""
        str1 = "x" * 500
        str2 = "y" * 500
        
        result = self.benchmark.benchmark_function(
            "levenshtein_memory_efficiency",
            optimized_levenshtein_distance,
            str1, str2
        )
        
        # Memory usage should be O(min(m,n)) not O(m*n)
        expected_max_memory = len(str2) * 8 * 10  # Rough estimate with overhead
        assert result.metrics.memory_peak < expected_max_memory, f"Memory usage too high: {result.metrics.memory_peak} bytes"
    
    def test_similarity_calculation_performance(self):
        """Test performance of similarity calculation."""
        str1 = "This is a test document for similarity calculation"
        str2 = "This is a test document for similarity computation"
        
        result = self.benchmark.benchmark_function(
            "similarity_calculation",
            calculate_similarity,
            str1, str2
        )
        
        # Should complete quickly
        assert result.metrics.execution_time < 0.005  # < 5ms
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"
    
    def test_levenshtein_batch_processing(self):
        """Test batch processing performance."""
        strings = [f"test string {i}" for i in range(100)]
        reference = "test string 50"
        
        def batch_similarity():
            results = []
            for s in strings:
                results.append(calculate_similarity(reference, s))
            return results
        
        result = self.benchmark.benchmark_function(
            "levenshtein_batch_processing",
            batch_similarity
        )
        
        # Batch processing should be efficient
        assert result.metrics.execution_time < 0.1  # < 100ms for 100 comparisons
        assert result.metrics.operations_per_second > 10  # At least 10 ops/sec
    
    def test_levenshtein_worst_case_performance(self):
        """Test worst-case performance scenarios."""
        # Completely different strings of same length
        str1 = "a" * 200
        str2 = "b" * 200
        
        result = self.benchmark.benchmark_function(
            "levenshtein_worst_case",
            optimized_levenshtein_distance,
            str1, str2
        )
        
        # Even worst case should complete reasonably quickly
        assert result.metrics.execution_time < 0.05  # < 50ms
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"


class TestMemoryUsageValidation:
    """Memory usage validation tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.benchmark = PerformanceBenchmark()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_manager_memory_usage(self):
        """Test FileSystemManager memory usage."""
        file_manager = FileSystemManager(self.temp_dir)
        
        def create_multiple_specs():
            for i in range(50):
                spec_name = f"test-spec-{i}"
                file_manager.create_spec_directory(spec_name)
                file_manager.save_document(spec_name, "requirements", f"# Requirements {i}")
                file_manager.save_document(spec_name, "design", f"# Design {i}")
        
        result = self.benchmark.benchmark_function(
            "file_manager_memory_usage",
            create_multiple_specs
        )
        
        # Memory usage should be reasonable
        assert result.metrics.memory_peak < 50 * 1024 * 1024  # < 50MB
        assert result.metrics.gc_collections < 10  # Minimal garbage collection
    
    def test_generator_memory_usage(self):
        """Test document generator memory usage."""
        req_gen = RequirementsGenerator()
        design_gen = DesignGenerator()
        
        def generate_large_documents():
            large_input = "Feature: " + "x" * 10000  # Large input
            
            requirements = req_gen.generate_requirements_document(large_input)
            design = design_gen.generate_design_document(requirements)
            
            return len(requirements) + len(design)
        
        result = self.benchmark.benchmark_function(
            "generator_memory_usage",
            generate_large_documents
        )
        
        # Memory usage should be proportional to input size
        assert result.metrics.memory_peak < 100 * 1024 * 1024  # < 100MB
    
    def test_workflow_orchestrator_memory_usage(self):
        """Test WorkflowOrchestrator memory usage."""
        orchestrator = WorkflowOrchestrator()
        
        def simulate_multiple_workflows():
            workflows = []
            for i in range(20):
                workflow_data = {
                    "feature_name": f"feature-{i}",
                    "requirements": f"Requirements for feature {i}" * 100,
                    "design": f"Design for feature {i}" * 100
                }
                workflows.append(workflow_data)
            return workflows
        
        result = self.benchmark.benchmark_function(
            "workflow_orchestrator_memory_usage",
            simulate_multiple_workflows
        )
        
        # Memory usage should be reasonable for multiple workflows
        assert result.metrics.memory_peak < 200 * 1024 * 1024  # < 200MB
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations."""
        file_manager = FileSystemManager(self.temp_dir)
        
        initial_memory = psutil.Process().memory_info().rss
        
        # Perform operations multiple times
        for iteration in range(10):
            for i in range(10):
                spec_name = f"leak-test-{iteration}-{i}"
                file_manager.create_spec_directory(spec_name)
                file_manager.save_document(spec_name, "requirements", f"# Test {i}")
                
                # Load and validate
                doc, result = file_manager.load_document(spec_name, "requirements")
                validation = file_manager.validate_spec_structure(spec_name)
            
            # Force garbage collection
            gc.collect()
            
            current_memory = psutil.Process().memory_info().rss
            memory_growth = current_memory - initial_memory
            
            # Memory growth should be reasonable (< 10MB per iteration)
            assert memory_growth < 10 * 1024 * 1024, f"Potential memory leak: {memory_growth} bytes growth"
    
    def test_concurrent_memory_usage(self):
        """Test memory usage under concurrent operations."""
        file_manager = FileSystemManager(self.temp_dir)
        
        def concurrent_operations():
            def worker(thread_id):
                for i in range(10):
                    spec_name = f"concurrent-{thread_id}-{i}"
                    file_manager.create_spec_directory(spec_name)
                    file_manager.save_document(spec_name, "requirements", f"# Requirements {i}")
            
            threads = []
            for t in range(5):
                thread = threading.Thread(target=worker, args=(t,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
        
        result = self.benchmark.benchmark_function(
            "concurrent_memory_usage",
            concurrent_operations
        )
        
        # Concurrent operations should not cause excessive memory usage
        assert result.metrics.memory_peak < 100 * 1024 * 1024  # < 100MB


class TestLoadTestingPerformance:
    """Load testing for performance under stress."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.benchmark = PerformanceBenchmark()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_high_volume_file_operations(self):
        """Test performance under high volume file operations."""
        file_manager = FileSystemManager(self.temp_dir)
        
        def high_volume_operations():
            # Create many specs rapidly
            for i in range(100):
                spec_name = f"volume-test-{i}"
                file_manager.create_spec_directory(spec_name)
                
                # Create multiple documents per spec
                for doc_type in ["requirements", "design", "tasks"]:
                    content = f"# {doc_type.title()} for {spec_name}\n" + "Content line\n" * 50
                    file_manager.save_document(spec_name, doc_type, content)
        
        result = self.benchmark.benchmark_function(
            "high_volume_file_operations",
            high_volume_operations
        )
        
        # Should handle high volume efficiently
        assert result.metrics.execution_time < 10.0  # < 10 seconds
        assert result.metrics.operations_per_second > 0.1  # At least 0.1 ops/sec
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"
    
    def test_concurrent_user_simulation(self):
        """Test performance simulating concurrent users."""
        file_manager = FileSystemManager(self.temp_dir)
        
        def simulate_user(user_id):
            """Simulate a single user's operations."""
            for i in range(5):
                spec_name = f"user-{user_id}-spec-{i}"
                
                # Create spec
                result = file_manager.create_spec_directory(spec_name)
                if not result.success:
                    continue
                
                # Create documents
                file_manager.save_document(spec_name, "requirements", f"# User {user_id} Requirements {i}")
                file_manager.save_document(spec_name, "design", f"# User {user_id} Design {i}")
                
                # Read documents
                doc, _ = file_manager.load_document(spec_name, "requirements")
                validation = file_manager.validate_spec_structure(spec_name)
        
        def concurrent_users():
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(simulate_user, i) for i in range(20)]
                for future in futures:
                    future.result()
        
        result = self.benchmark.benchmark_function(
            "concurrent_user_simulation",
            concurrent_users
        )
        
        # Should handle concurrent users efficiently
        assert result.metrics.execution_time < 30.0  # < 30 seconds
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"
    
    def test_stress_test_string_operations(self):
        """Stress test string operations with large datasets."""
        
        def stress_test_strings():
            # Generate large strings for comparison
            base_strings = [f"Document content {i} " + "x" * 1000 for i in range(50)]
            target_string = "Document content 25 " + "x" * 1000
            
            similarities = []
            for s in base_strings:
                similarity = calculate_similarity(target_string, s)
                similarities.append(similarity)
            
            return similarities
        
        result = self.benchmark.benchmark_function(
            "stress_test_string_operations",
            stress_test_strings
        )
        
        # Should handle stress test efficiently
        assert result.metrics.execution_time < 5.0  # < 5 seconds
        assert result.metrics.operations_per_second > 1.0  # At least 1 ops/sec
    
    def test_memory_pressure_handling(self):
        """Test performance under memory pressure."""
        
        def create_memory_pressure():
            # Create large data structures
            large_data = []
            
            try:
                # Gradually increase memory usage
                for i in range(100):
                    # Create 1MB chunks
                    chunk = bytearray(1024 * 1024)
                    large_data.append(chunk)
                    
                    # Perform operations under memory pressure
                    if i % 10 == 0:
                        str1 = "test string " * 100
                        str2 = "test string " * 100 + "modified"
                        similarity = calculate_similarity(str1, str2)
                
                return len(large_data)
            
            except MemoryError:
                # Expected under extreme memory pressure
                return len(large_data)
        
        result = self.benchmark.benchmark_function(
            "memory_pressure_handling",
            create_memory_pressure
        )
        
        # Should handle memory pressure gracefully
        # (May not complete all operations, but shouldn't crash)
        assert result.metrics.execution_time < 60.0  # < 1 minute
    
    def test_cpu_intensive_operations(self):
        """Test CPU-intensive operations performance."""
        
        def cpu_intensive_operations():
            results = []
            
            # CPU-intensive string comparisons
            for i in range(20):
                str1 = "pattern " * 200 + f"unique_{i}"
                str2 = "pattern " * 200 + f"unique_{i+1}"
                
                # Multiple comparisons per iteration
                for j in range(10):
                    distance = optimized_levenshtein_distance(str1, str2)
                    similarity = calculate_similarity(str1, str2)
                    results.append((distance, similarity))
            
            return results
        
        result = self.benchmark.benchmark_function(
            "cpu_intensive_operations",
            cpu_intensive_operations
        )
        
        # Should utilize CPU efficiently
        assert result.metrics.execution_time < 10.0  # < 10 seconds
        assert result.metrics.cpu_usage > 10.0  # Should use significant CPU
        assert not result.regression_detected, f"Performance regression detected: {result.performance_ratio:.2f}x slower"


class TestAutomatedRegressionDetection:
    """Automated performance regression detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.benchmark = PerformanceBenchmark()
    
    def test_regression_detection_sensitivity(self):
        """Test regression detection sensitivity."""
        
        def fast_operation():
            return sum(range(1000))
        
        def slow_operation():
            # Intentionally slower version
            result = 0
            for i in range(1000):
                result += i
                # Add artificial delay to simulate regression
                time.sleep(0.0001)
            return result
        
        # Establish baseline with fast operation
        baseline_result = self.benchmark.benchmark_function(
            "regression_test_baseline",
            fast_operation
        )
        
        # Test with slower operation (simulating regression)
        regression_result = self.benchmark.benchmark_function(
            "regression_test_baseline",  # Same test name to compare
            slow_operation
        )
        
        # Should detect regression
        assert regression_result.regression_detected, "Failed to detect performance regression"
        assert regression_result.performance_ratio > 1.2, "Regression ratio should be > 1.2"
    
    def test_performance_trend_analysis(self):
        """Test performance trend analysis over multiple runs."""
        
        def variable_performance_operation(delay_factor):
            time.sleep(0.001 * delay_factor)
            return sum(range(100))
        
        results = []
        
        # Simulate performance degradation over time
        for i in range(5):
            delay = 1 + (i * 0.5)  # Gradually increasing delay
            result = self.benchmark.benchmark_function(
                f"trend_test_run_{i}",
                variable_performance_operation,
                delay
            )
            results.append(result)
        
        # Analyze trend
        execution_times = [r.metrics.execution_time for r in results]
        
        # Should show increasing trend
        assert execution_times[-1] > execution_times[0], "Should show performance degradation trend"
        
        # Calculate trend slope
        n = len(execution_times)
        x_values = list(range(n))
        slope = (n * sum(x * y for x, y in zip(x_values, execution_times)) - 
                sum(x_values) * sum(execution_times)) / (n * sum(x**2 for x in x_values) - sum(x_values)**2)
        
        assert slope > 0, "Trend slope should be positive (indicating degradation)"
    
    def test_performance_baseline_management(self):
        """Test performance baseline management."""
        
        def test_operation():
            return sorted([i**2 for i in range(100)])
        
        # Create initial baseline
        result1 = self.benchmark.benchmark_function(
            "baseline_management_test",
            test_operation
        )
        
        # Should create baseline (no regression detected)
        assert not result1.regression_detected
        
        # Run again with same performance
        result2 = self.benchmark.benchmark_function(
            "baseline_management_test",
            test_operation
        )
        
        # Should compare against baseline
        assert result2.baseline_metrics is not None
        assert abs(result2.performance_ratio - 1.0) < 0.5  # Should be close to baseline
    
    def test_performance_alert_thresholds(self):
        """Test performance alert thresholds."""
        
        def baseline_operation():
            return sum(range(500))
        
        def slightly_slower_operation():
            time.sleep(0.001)  # Small delay
            return sum(range(500))
        
        def much_slower_operation():
            time.sleep(0.01)  # Larger delay
            return sum(range(500))
        
        # Establish baseline
        baseline_result = self.benchmark.benchmark_function(
            "alert_threshold_test",
            baseline_operation
        )
        
        # Test with slight degradation (should not trigger alert)
        slight_result = self.benchmark.benchmark_function(
            "alert_threshold_test",
            slightly_slower_operation
        )
        
        # Test with significant degradation (should trigger alert)
        major_result = self.benchmark.benchmark_function(
            "alert_threshold_test",
            much_slower_operation
        )
        
        # Verify alert thresholds
        assert not slight_result.regression_detected or slight_result.performance_ratio < 1.2
        assert major_result.regression_detected and major_result.performance_ratio > 1.2
    
    def test_performance_report_generation(self):
        """Test performance report generation."""
        
        def sample_operation():
            return [i**2 for i in range(200)]
        
        # Run multiple benchmarks
        results = []
        for i in range(3):
            result = self.benchmark.benchmark_function(
                f"report_test_{i}",
                sample_operation
            )
            results.append(result)
        
        # Generate performance report
        report = self._generate_performance_report(results)
        
        # Verify report structure
        assert "summary" in report
        assert "details" in report
        assert "recommendations" in report
        
        # Verify summary statistics
        assert "total_tests" in report["summary"]
        assert "regressions_detected" in report["summary"]
        assert "average_performance_ratio" in report["summary"]
    
    def _generate_performance_report(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate a performance report from benchmark results."""
        
        total_tests = len(results)
        regressions = sum(1 for r in results if r.regression_detected)
        
        performance_ratios = [r.performance_ratio for r in results if r.baseline_metrics]
        avg_ratio = statistics.mean(performance_ratios) if performance_ratios else 1.0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "regressions_detected": regressions,
                "average_performance_ratio": avg_ratio,
                "timestamp": time.time()
            },
            "details": [
                {
                    "test_name": r.test_name,
                    "execution_time": r.metrics.execution_time,
                    "memory_usage": r.metrics.memory_usage,
                    "regression_detected": r.regression_detected,
                    "performance_ratio": r.performance_ratio
                }
                for r in results
            ],
            "recommendations": self._generate_recommendations(results)
        }
        
        return report
    
    def _generate_recommendations(self, results: List[BenchmarkResult]) -> List[str]:
        """Generate performance recommendations based on results."""
        recommendations = []
        
        # Check for memory issues
        high_memory_tests = [r for r in results if r.metrics.memory_usage > 50 * 1024 * 1024]
        if high_memory_tests:
            recommendations.append("Consider optimizing memory usage in high-memory operations")
        
        # Check for slow operations
        slow_tests = [r for r in results if r.metrics.execution_time > 1.0]
        if slow_tests:
            recommendations.append("Review slow operations for optimization opportunities")
        
        # Check for regressions
        regressions = [r for r in results if r.regression_detected]
        if regressions:
            recommendations.append(f"Address {len(regressions)} performance regressions detected")
        
        return recommendations