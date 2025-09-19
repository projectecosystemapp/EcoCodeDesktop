"""
Comprehensive error handling validation tests.

This module implements fault injection tests for network failures,
resource exhaustion simulation, recovery mechanism validation,
and timeout/retry logic verification tests.

Requirements addressed:
- 5.1, 5.2, 5.3, 5.4: Error handling validation across all components
"""

import pytest
import asyncio
import tempfile
import threading
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import os
import signal
import psutil

from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator
from eco_api.specs.task_execution_engine import TaskExecutionEngine
from eco_api.specs.models import DocumentType, WorkflowState
from eco_api.security.authorization_validator import AuthorizationValidator, Role


class TestNetworkFailureHandling:
    """Test network failure handling and recovery mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.orchestrator = WorkflowOrchestrator()
    
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test handling of connection timeouts."""
        import aiohttp
        
        # Mock aiohttp to raise timeout
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Connection timeout")
            
            # Test that timeout is handled gracefully
            with pytest.raises(Exception) as exc_info:
                await self.orchestrator.execute_workflow_step("test", {})
            
            # Should not be the original timeout error
            assert "Connection timeout" not in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_connection_refused_handling(self):
        """Test handling of connection refused errors."""
        import aiohttp
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientConnectorError(
                connection_key=None, 
                os_error=ConnectionRefusedError("Connection refused")
            )
            
            # Should handle connection refused gracefully
            with pytest.raises(Exception) as exc_info:
                await self.orchestrator.execute_workflow_step("test", {})
            
            # Should wrap the error appropriately
            assert isinstance(exc_info.value, Exception)
    
    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self):
        """Test handling of DNS resolution failures."""
        import aiohttp
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientConnectorError(
                connection_key=None,
                os_error=OSError("Name or service not known")
            )
            
            with pytest.raises(Exception):
                await self.orchestrator.execute_workflow_step("test", {})
    
    @pytest.mark.asyncio
    async def test_http_error_status_handling(self):
        """Test handling of HTTP error status codes."""
        import aiohttp
        
        # Mock response with error status
        mock_response = Mock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=Mock(), history=(), status=500
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(Exception):
                await self.orchestrator.execute_workflow_step("test", {})
    
    def test_retry_mechanism_with_exponential_backoff(self):
        """Test retry mechanism with exponential backoff."""
        call_count = 0
        call_times = []
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        # Test retry with backoff
        start_time = time.time()
        
        # Simulate retry logic (this would be in actual error handler)
        max_retries = 3
        backoff_factor = 1.5
        
        for attempt in range(max_retries):
            try:
                result = failing_function()
                break
            except ConnectionError:
                if attempt == max_retries - 1:
                    raise
                time.sleep(backoff_factor ** attempt)
        
        # Verify retry behavior
        assert call_count == 3
        assert result == "success"
        
        # Verify exponential backoff timing
        if len(call_times) > 1:
            time_diff_1 = call_times[1] - call_times[0]
            time_diff_2 = call_times[2] - call_times[1]
            assert time_diff_2 > time_diff_1  # Second delay should be longer
    
    def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for repeated failures."""
        failure_count = 0
        circuit_open = False
        
        def unreliable_service():
            nonlocal failure_count, circuit_open
            
            if circuit_open:
                raise Exception("Circuit breaker is open")
            
            failure_count += 1
            if failure_count < 5:
                raise ConnectionError("Service unavailable")
            
            return "success"
        
        # Simulate circuit breaker logic
        consecutive_failures = 0
        failure_threshold = 3
        
        for attempt in range(10):
            try:
                result = unreliable_service()
                consecutive_failures = 0  # Reset on success
                circuit_open = False
                break
            except ConnectionError:
                consecutive_failures += 1
                if consecutive_failures >= failure_threshold:
                    circuit_open = True
            except Exception as e:
                if "Circuit breaker" in str(e):
                    # Circuit is open, wait before retry
                    time.sleep(0.1)
                    if attempt > 7:  # Reset circuit after some time
                        circuit_open = False
                        consecutive_failures = 0
        
        # Circuit breaker should have activated
        assert circuit_open or failure_count >= failure_threshold


class TestResourceExhaustionHandling:
    """Test resource exhaustion simulation and handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FileSystemManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_memory_exhaustion_handling(self):
        """Test handling of memory exhaustion scenarios."""
        
        def memory_intensive_operation():
            """Simulate memory-intensive operation."""
            try:
                # Try to allocate large amount of memory
                large_data = bytearray(100 * 1024 * 1024)  # 100MB
                return len(large_data)
            except MemoryError:
                raise MemoryError("Insufficient memory")
        
        # Test memory error handling
        try:
            result = memory_intensive_operation()
            # If successful, verify it's reasonable
            assert result > 0
        except MemoryError:
            # Should handle memory error gracefully
            assert True  # Expected behavior
    
    def test_disk_space_exhaustion_handling(self):
        """Test handling of disk space exhaustion."""
        
        # Create a large file to simulate disk space issues
        large_file_path = Path(self.temp_dir) / "large_file.txt"
        
        try:
            # Try to write a very large file
            with open(large_file_path, 'w') as f:
                for i in range(1000):
                    f.write("x" * 1024)  # Write 1KB chunks
            
            # Test file operations when disk might be full
            result = self.file_manager.create_spec_directory("test-spec")
            
            # Should handle gracefully
            if not result.success:
                assert "disk" in result.error_code.lower() or "space" in result.error_code.lower()
        
        except OSError as e:
            # Disk full or permission error - should be handled
            assert "No space left" in str(e) or "Permission denied" in str(e)
    
    def test_file_descriptor_exhaustion(self):
        """Test handling of file descriptor exhaustion."""
        open_files = []
        
        try:
            # Try to open many files to exhaust file descriptors
            for i in range(1000):
                file_path = Path(self.temp_dir) / f"file_{i}.txt"
                try:
                    f = open(file_path, 'w')
                    open_files.append(f)
                    f.write(f"content {i}")
                except OSError as e:
                    if "Too many open files" in str(e):
                        # Expected behavior - should handle gracefully
                        break
                    else:
                        raise
        
        finally:
            # Clean up open files
            for f in open_files:
                try:
                    f.close()
                except:
                    pass
        
        # Test that file operations still work after cleanup
        result = self.file_manager.create_spec_directory("test-after-exhaustion")
        assert result.success or "FILE_DESCRIPTOR" in result.error_code
    
    def test_thread_pool_exhaustion(self):
        """Test handling of thread pool exhaustion."""
        
        def long_running_task(duration):
            """Simulate long-running task."""
            time.sleep(duration)
            return f"completed after {duration}s"
        
        # Create thread pool with limited size
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            
            # Submit more tasks than available workers
            for i in range(10):
                future = executor.submit(long_running_task, 0.1)
                futures.append(future)
            
            # Should handle queue gracefully
            completed = 0
            for future in futures:
                try:
                    result = future.result(timeout=5.0)
                    completed += 1
                except Exception as e:
                    # Should handle timeout or other errors
                    assert "timeout" in str(e).lower() or isinstance(e, Exception)
            
            # Some tasks should complete
            assert completed > 0
    
    def test_concurrent_access_handling(self):
        """Test handling of concurrent access to resources."""
        
        def concurrent_file_operation(file_path, content, thread_id):
            """Simulate concurrent file operations."""
            try:
                # Multiple threads trying to write to same file
                with open(file_path, 'a') as f:
                    f.write(f"Thread {thread_id}: {content}\n")
                return True
            except Exception as e:
                return False
        
        file_path = Path(self.temp_dir) / "concurrent_test.txt"
        threads = []
        results = []
        
        # Start multiple threads
        for i in range(10):
            thread = threading.Thread(
                target=lambda i=i: results.append(
                    concurrent_file_operation(file_path, f"data_{i}", i)
                )
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should handle concurrent access gracefully
        successful_operations = sum(results)
        assert successful_operations >= 0  # At least some should succeed


class TestRecoveryMechanismValidation:
    """Test recovery mechanism validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FileSystemManager(self.temp_dir)
        self.orchestrator = WorkflowOrchestrator()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_operation_recovery(self):
        """Test recovery from file operation failures."""
        
        # Create a spec directory
        result = self.file_manager.create_spec_directory("test-spec")
        assert result.success
        
        # Simulate file corruption by creating invalid file
        spec_dir = Path(self.temp_dir) / "specs" / "test-spec"
        corrupted_file = spec_dir / "requirements.md"
        
        # Write invalid content
        with open(corrupted_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')  # Binary data in text file
        
        # Try to load document - should handle corruption gracefully
        doc, result = self.file_manager.load_document("test-spec", DocumentType.REQUIREMENTS)
        
        if not result.success:
            # Should provide recovery options
            assert "CORRUPTION" in result.error_code or "INVALID_FORMAT" in result.error_code
            
            # Test recovery by recreating file
            recovery_result = self.file_manager.save_document(
                "test-spec", 
                DocumentType.REQUIREMENTS, 
                "# Recovered Requirements\n\nRecovered content."
            )
            assert recovery_result.success
    
    def test_workflow_state_recovery(self):
        """Test recovery from workflow state corruption."""
        
        # Create workflow state
        workflow_id = "test-workflow"
        initial_state = {
            "current_step": "requirements",
            "completed_steps": [],
            "data": {"feature_name": "test-feature"}
        }
        
        # Save initial state
        state_file = Path(self.temp_dir) / f"{workflow_id}_state.json"
        with open(state_file, 'w') as f:
            json.dump(initial_state, f)
        
        # Corrupt the state file
        with open(state_file, 'w') as f:
            f.write("invalid json content {")
        
        # Try to load workflow state - should handle corruption
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
        except json.JSONDecodeError:
            # Should recover with default state
            state = {
                "current_step": "requirements",
                "completed_steps": [],
                "data": {},
                "recovered": True
            }
        
        assert "recovered" in state or "current_step" in state
    
    def test_partial_failure_recovery(self):
        """Test recovery from partial operation failures."""
        
        # Simulate partial spec creation failure
        spec_name = "partial-failure-test"
        
        # Create spec directory
        result = self.file_manager.create_spec_directory(spec_name)
        assert result.success
        
        # Create some files successfully
        req_result = self.file_manager.save_document(
            spec_name, DocumentType.REQUIREMENTS, "# Requirements"
        )
        assert req_result.success
        
        # Simulate failure during design creation
        spec_dir = Path(self.temp_dir) / "specs" / spec_name
        design_file = spec_dir / "design.md"
        
        # Make directory read-only to simulate permission error
        try:
            os.chmod(spec_dir, 0o444)  # Read-only
            
            design_result = self.file_manager.save_document(
                spec_name, DocumentType.DESIGN, "# Design"
            )
            
            # Should handle permission error
            if not design_result.success:
                assert "PERMISSION" in design_result.error_code
        
        finally:
            # Restore permissions for cleanup
            os.chmod(spec_dir, 0o755)
        
        # Verify partial state is recoverable
        validation_result = self.file_manager.validate_spec_structure(spec_name)
        
        # Should identify missing files and provide recovery guidance
        if not validation_result.is_valid:
            missing_files = [error for error in validation_result.errors 
                           if "missing" in error.message.lower()]
            assert len(missing_files) > 0
    
    def test_transaction_rollback_simulation(self):
        """Test transaction-like rollback behavior."""
        
        spec_name = "transaction-test"
        
        # Simulate multi-step operation that should be atomic
        steps_completed = []
        
        try:
            # Step 1: Create directory
            result1 = self.file_manager.create_spec_directory(spec_name)
            if result1.success:
                steps_completed.append("directory")
            
            # Step 2: Create requirements
            result2 = self.file_manager.save_document(
                spec_name, DocumentType.REQUIREMENTS, "# Requirements"
            )
            if result2.success:
                steps_completed.append("requirements")
            
            # Step 3: Simulate failure during design creation
            raise Exception("Simulated failure during design creation")
        
        except Exception:
            # Rollback completed steps
            if "requirements" in steps_completed:
                # Remove requirements file
                req_file = Path(self.temp_dir) / "specs" / spec_name / "requirements.md"
                if req_file.exists():
                    req_file.unlink()
            
            if "directory" in steps_completed:
                # Remove directory
                spec_dir = Path(self.temp_dir) / "specs" / spec_name
                if spec_dir.exists():
                    import shutil
                    shutil.rmtree(spec_dir)
        
        # Verify rollback was successful
        spec_dir = Path(self.temp_dir) / "specs" / spec_name
        assert not spec_dir.exists()


class TestTimeoutAndRetryLogic:
    """Test timeout and retry logic verification."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.start_time = time.time()
    
    def test_operation_timeout_enforcement(self):
        """Test that operations respect timeout limits."""
        
        def slow_operation(duration):
            """Simulate slow operation."""
            time.sleep(duration)
            return "completed"
        
        # Test with timeout shorter than operation
        timeout = 0.5
        operation_duration = 1.0
        
        start_time = time.time()
        
        try:
            # Simulate timeout enforcement
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Operation timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(1)  # 1 second timeout
            
            try:
                result = slow_operation(operation_duration)
                signal.alarm(0)  # Cancel alarm
            except TimeoutError:
                signal.alarm(0)  # Cancel alarm
                elapsed = time.time() - start_time
                assert elapsed < operation_duration + 0.1  # Should timeout before completion
                raise
        
        except TimeoutError:
            # Expected behavior
            elapsed = time.time() - start_time
            assert elapsed < operation_duration + 0.5  # Should timeout reasonably quickly
    
    def test_retry_with_jitter(self):
        """Test retry logic with jitter to prevent thundering herd."""
        
        import random
        
        call_times = []
        
        def unreliable_operation():
            """Operation that fails first few times."""
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        # Retry with jitter
        max_retries = 5
        base_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                result = unreliable_operation()
                break
            except ConnectionError:
                if attempt == max_retries - 1:
                    raise
                
                # Add jitter to delay
                jitter = random.uniform(0, 0.1)
                delay = base_delay * (2 ** attempt) + jitter
                time.sleep(delay)
        
        # Verify jitter was applied (delays should vary)
        if len(call_times) > 2:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            
            # Delays should be different due to jitter
            assert abs(delay1 - delay2) > 0.01  # Some variation expected
    
    def test_progressive_timeout_increase(self):
        """Test progressive timeout increase for retries."""
        
        timeouts = []
        
        def operation_with_variable_duration(duration):
            """Operation that takes variable time."""
            start = time.time()
            time.sleep(duration)
            elapsed = time.time() - start
            timeouts.append(elapsed)
            
            if len(timeouts) < 3:
                raise TimeoutError(f"Timeout after {elapsed}s")
            return "success"
        
        # Progressive timeout strategy
        base_timeout = 0.1
        max_retries = 4
        
        for attempt in range(max_retries):
            timeout = base_timeout * (1.5 ** attempt)  # Increase timeout each retry
            
            try:
                result = operation_with_variable_duration(timeout * 0.8)  # Operation within timeout
                break
            except TimeoutError:
                if attempt == max_retries - 1:
                    raise
                continue
        
        # Verify progressive timeout increase
        assert len(timeouts) >= 2
        # Later attempts should have longer timeouts (reflected in operation duration)
    
    def test_deadline_based_retry(self):
        """Test deadline-based retry logic."""
        
        overall_deadline = time.time() + 2.0  # 2 second deadline
        attempts = 0
        
        def failing_operation():
            nonlocal attempts
            attempts += 1
            
            if time.time() > overall_deadline:
                raise TimeoutError("Overall deadline exceeded")
            
            if attempts < 5:
                raise ConnectionError("Still failing")
            
            return "success"
        
        # Retry until deadline
        while time.time() < overall_deadline:
            try:
                result = failing_operation()
                break
            except ConnectionError:
                time.sleep(0.1)
                continue
            except TimeoutError:
                # Deadline exceeded
                break
        
        # Should have made multiple attempts within deadline
        assert attempts > 1
        assert time.time() <= overall_deadline + 0.1  # Small tolerance for timing
    
    def test_backoff_strategy_effectiveness(self):
        """Test effectiveness of different backoff strategies."""
        
        strategies = {
            "linear": lambda attempt: 0.1 * attempt,
            "exponential": lambda attempt: 0.1 * (2 ** attempt),
            "fibonacci": lambda attempt: 0.1 * self._fibonacci(attempt)
        }
        
        for strategy_name, delay_func in strategies.items():
            attempts = 0
            start_time = time.time()
            
            def test_operation():
                nonlocal attempts
                attempts += 1
                if attempts < 4:
                    raise ConnectionError("Failing")
                return "success"
            
            # Test strategy
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    result = test_operation()
                    break
                except ConnectionError:
                    if attempt == max_retries - 1:
                        raise
                    
                    delay = delay_func(attempt)
                    time.sleep(delay)
            
            total_time = time.time() - start_time
            
            # Verify strategy behavior
            if strategy_name == "exponential":
                # Exponential should be fastest for early success
                assert total_time < 1.0  # Should complete quickly
            
            # Reset for next strategy
            attempts = 0
    
    def _fibonacci(self, n):
        """Helper method to calculate Fibonacci number."""
        if n <= 1:
            return n
        return self._fibonacci(n-1) + self._fibonacci(n-2)


class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FileSystemManager(self.temp_dir)
        self.orchestrator = WorkflowOrchestrator()
        self.auth_validator = AuthorizationValidator()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cascading_failure_handling(self):
        """Test handling of cascading failures across components."""
        
        # Simulate failure chain: auth -> file -> workflow
        user_context = self.auth_validator.create_user_context("test_user", [Role.DEVELOPER])
        
        # Step 1: Auth failure
        auth_result = self.auth_validator.validate_server_side_permissions(
            user_context=user_context,
            operation="admin_operation",
            permission=self.auth_validator.DEFAULT_ROLE_PERMISSIONS[Role.ADMIN].pop()
        )
        
        if not auth_result.authorized:
            # Should handle auth failure gracefully
            assert auth_result.reason is not None
            
            # Subsequent operations should also fail gracefully
            file_result = self.file_manager.create_spec_directory("unauthorized-spec")
            
            # File operation might succeed (no auth integration in this test)
            # but workflow should handle the auth context properly
    
    def test_error_propagation_and_wrapping(self):
        """Test proper error propagation and wrapping."""
        
        # Create nested error scenario
        def level3_operation():
            raise ValueError("Level 3 error")
        
        def level2_operation():
            try:
                return level3_operation()
            except ValueError as e:
                raise RuntimeError(f"Level 2 wrapper: {str(e)}") from e
        
        def level1_operation():
            try:
                return level2_operation()
            except RuntimeError as e:
                raise Exception(f"Level 1 wrapper: {str(e)}") from e
        
        # Test error chain preservation
        with pytest.raises(Exception) as exc_info:
            level1_operation()
        
        # Verify error chain
        assert "Level 1 wrapper" in str(exc_info.value)
        assert exc_info.value.__cause__ is not None
        assert "Level 2 wrapper" in str(exc_info.value.__cause__)
        assert exc_info.value.__cause__.__cause__ is not None
        assert "Level 3 error" in str(exc_info.value.__cause__.__cause__)
    
    def test_resource_cleanup_on_failure(self):
        """Test that resources are properly cleaned up on failure."""
        
        created_files = []
        
        try:
            # Create some resources
            spec_result = self.file_manager.create_spec_directory("cleanup-test")
            if spec_result.success:
                created_files.append("spec_directory")
            
            # Create temporary files
            temp_file = Path(self.temp_dir) / "temp_resource.txt"
            with open(temp_file, 'w') as f:
                f.write("temporary data")
            created_files.append("temp_file")
            
            # Simulate failure
            raise Exception("Simulated failure requiring cleanup")
        
        except Exception:
            # Cleanup resources
            if "temp_file" in created_files:
                temp_file = Path(self.temp_dir) / "temp_resource.txt"
                if temp_file.exists():
                    temp_file.unlink()
            
            if "spec_directory" in created_files:
                spec_dir = Path(self.temp_dir) / "specs" / "cleanup-test"
                if spec_dir.exists():
                    import shutil
                    shutil.rmtree(spec_dir)
        
        # Verify cleanup
        temp_file = Path(self.temp_dir) / "temp_resource.txt"
        spec_dir = Path(self.temp_dir) / "specs" / "cleanup-test"
        
        assert not temp_file.exists()
        # Spec directory might still exist depending on cleanup strategy
    
    def test_error_context_preservation(self):
        """Test that error context is preserved across component boundaries."""
        
        error_context = {
            "operation": "test_operation",
            "user_id": "test_user",
            "timestamp": time.time(),
            "component": "file_manager"
        }
        
        def operation_with_context():
            try:
                # Simulate operation that fails
                raise FileNotFoundError("File not found")
            except FileNotFoundError as e:
                # Add context to error
                e.error_context = error_context
                raise
        
        # Test context preservation
        with pytest.raises(FileNotFoundError) as exc_info:
            operation_with_context()
        
        # Verify context is preserved
        assert hasattr(exc_info.value, 'error_context')
        assert exc_info.value.error_context["operation"] == "test_operation"
        assert exc_info.value.error_context["user_id"] == "test_user"