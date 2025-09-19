"""
Tests for the resilience service.

This module tests backup and recovery mechanisms, transaction-like operations,
and system health monitoring for the spec workflow system.
"""

import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from eco_api.specs.resilience_service import (
    ResilienceService,
    BackupType,
    BackupStatus,
    RecoveryType,
    SystemHealthStatus,
    BackupMetadata,
    RecoveryPoint,
    TransactionContext,
    SystemHealthMetrics,
    HealthCheck
)
from eco_api.specs.models import WorkflowPhase, WorkflowStatus


class TestResilienceService:
    """Test cases for ResilienceService."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        base_dir = tempfile.mkdtemp(prefix="test_specs_")
        backup_dir = tempfile.mkdtemp(prefix="test_backups_")
        
        yield base_dir, backup_dir
        
        # Cleanup
        shutil.rmtree(base_dir, ignore_errors=True)
        shutil.rmtree(backup_dir, ignore_errors=True)
    
    @pytest.fixture
    def resilience_service(self, temp_dirs):
        """Create a ResilienceService instance for testing."""
        base_dir, backup_dir = temp_dirs
        return ResilienceService(base_path=base_dir, backup_path=backup_dir)
    
    @pytest.fixture
    def sample_spec_dir(self, temp_dirs):
        """Create a sample spec directory for testing."""
        base_dir, _ = temp_dirs
        spec_dir = Path(base_dir) / "test-spec"
        spec_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sample files
        (spec_dir / "requirements.md").write_text("# Requirements\n\nSample requirements.")
        (spec_dir / "design.md").write_text("# Design\n\nSample design.")
        (spec_dir / "tasks.md").write_text("# Tasks\n\nSample tasks.")
        
        # Create metadata
        metadata = {
            "id": "test-spec",
            "feature_name": "test-spec",
            "current_phase": "requirements",
            "status": "in_progress"
        }
        (spec_dir / ".spec-metadata.json").write_text(json.dumps(metadata, indent=2))
        
        return spec_dir
    
    @pytest.mark.asyncio
    async def test_create_full_backup(self, resilience_service, sample_spec_dir):
        """Test creating a full backup."""
        spec_id = "test-spec"
        
        backup_metadata = await resilience_service.create_backup(
            spec_id=spec_id,
            backup_type=BackupType.FULL,
            tags=["test"]
        )
        
        assert backup_metadata.spec_id == spec_id
        assert backup_metadata.backup_type == BackupType.FULL
        assert backup_metadata.status == BackupStatus.COMPLETED
        assert backup_metadata.file_count > 0
        assert backup_metadata.size_bytes > 0
        assert len(backup_metadata.checksum) == 64  # SHA-256 hex length
        assert "test" in backup_metadata.tags
        
        # Verify backup files exist
        backup_dir = Path(resilience_service.backup_path) / backup_metadata.id
        assert backup_dir.exists()
        assert (backup_dir / "data").exists()
        assert (backup_dir / "data" / "requirements.md").exists()
    
    @pytest.mark.asyncio
    async def test_create_snapshot_backup(self, resilience_service, sample_spec_dir):
        """Test creating a snapshot backup."""
        spec_id = "test-spec"
        
        backup_metadata = await resilience_service.create_backup(
            spec_id=spec_id,
            backup_type=BackupType.SNAPSHOT
        )
        
        assert backup_metadata.backup_type == BackupType.SNAPSHOT
        assert backup_metadata.status == BackupStatus.COMPLETED
        
        # Verify snapshot file exists
        backup_dir = Path(resilience_service.backup_path) / backup_metadata.id
        assert backup_dir.exists()
        assert (backup_dir / "snapshot.tar.gz").exists()
    
    @pytest.mark.asyncio
    async def test_create_backup_nonexistent_spec(self, resilience_service):
        """Test creating backup for nonexistent spec."""
        with pytest.raises(FileNotFoundError):
            await resilience_service.create_backup("nonexistent-spec")
    
    @pytest.mark.asyncio
    async def test_create_incremental_backup(self, resilience_service, sample_spec_dir):
        """Test creating incremental backup."""
        spec_id = "test-spec"
        
        # Create initial full backup
        full_backup = await resilience_service.create_backup(
            spec_id=spec_id,
            backup_type=BackupType.FULL
        )
        
        # Modify a file
        (sample_spec_dir / "requirements.md").write_text("# Updated Requirements\n\nUpdated content.")
        
        # Create incremental backup
        incremental_backup = await resilience_service.create_backup(
            spec_id=spec_id,
            backup_type=BackupType.INCREMENTAL
        )
        
        assert incremental_backup.backup_type == BackupType.INCREMENTAL
        assert incremental_backup.status == BackupStatus.COMPLETED
        
        # Incremental backup should be smaller than full backup
        assert incremental_backup.size_bytes <= full_backup.size_bytes
    
    @pytest.mark.asyncio
    async def test_restore_from_backup(self, resilience_service, sample_spec_dir):
        """Test restoring from backup."""
        spec_id = "test-spec"
        
        # Create backup
        backup_metadata = await resilience_service.create_backup(spec_id)
        
        # Modify original files
        (sample_spec_dir / "requirements.md").write_text("Modified content")
        
        # Restore from backup
        success = await resilience_service.restore_from_backup(backup_metadata.id)
        
        assert success
        
        # Verify restoration
        restored_content = (sample_spec_dir / "requirements.md").read_text()
        assert "Sample requirements" in restored_content
        assert "Modified content" not in restored_content
    
    @pytest.mark.asyncio
    async def test_restore_to_different_spec(self, resilience_service, sample_spec_dir):
        """Test restoring backup to different spec ID."""
        original_spec_id = "test-spec"
        target_spec_id = "restored-spec"
        
        # Create backup
        backup_metadata = await resilience_service.create_backup(original_spec_id)
        
        # Restore to different location
        success = await resilience_service.restore_from_backup(
            backup_metadata.id,
            target_spec_id=target_spec_id
        )
        
        assert success
        
        # Verify restoration in new location
        target_dir = Path(resilience_service.base_path) / target_spec_id
        assert target_dir.exists()
        assert (target_dir / "requirements.md").exists()
    
    @pytest.mark.asyncio
    async def test_backup_integrity_verification(self, resilience_service, sample_spec_dir):
        """Test backup integrity verification."""
        spec_id = "test-spec"
        
        # Create backup
        backup_metadata = await resilience_service.create_backup(spec_id)
        
        # Verify integrity
        is_valid = await resilience_service._verify_backup_integrity(backup_metadata.id)
        assert is_valid
        
        # Corrupt backup and verify it fails
        backup_dir = Path(resilience_service.backup_path) / backup_metadata.id
        (backup_dir / "data" / "requirements.md").write_text("Corrupted content")
        
        is_valid = await resilience_service._verify_backup_integrity(backup_metadata.id)
        assert not is_valid
    
    @pytest.mark.asyncio
    async def test_transaction_context_success(self, resilience_service, sample_spec_dir):
        """Test successful transaction context."""
        spec_id = "test-spec"
        
        async with resilience_service.create_transaction(spec_id, "test_operation") as transaction:
            assert transaction.spec_id == spec_id
            assert transaction.operation == "test_operation"
            assert not transaction.completed
            assert not transaction.rolled_back
            
            # Perform some operation
            (sample_spec_dir / "new_file.txt").write_text("New content")
        
        # Transaction should be completed
        assert transaction.completed
        assert not transaction.rolled_back
        
        # File should exist
        assert (sample_spec_dir / "new_file.txt").exists()
    
    @pytest.mark.asyncio
    async def test_transaction_context_rollback(self, resilience_service, sample_spec_dir):
        """Test transaction rollback on failure."""
        spec_id = "test-spec"
        
        # Record original state
        original_files = list(sample_spec_dir.iterdir())
        
        try:
            async with resilience_service.create_transaction(spec_id, "test_operation") as transaction:
                # Create a new file
                (sample_spec_dir / "new_file.txt").write_text("New content")
                
                # Simulate failure
                raise ValueError("Simulated failure")
        
        except ValueError:
            pass  # Expected
        
        # Transaction should be rolled back
        assert transaction.rolled_back
        
        # New file should not exist (rolled back)
        assert not (sample_spec_dir / "new_file.txt").exists()
        
        # Original files should still exist
        current_files = list(sample_spec_dir.iterdir())
        assert len(current_files) == len(original_files)
    
    @pytest.mark.asyncio
    async def test_create_recovery_point(self, resilience_service, sample_spec_dir):
        """Test creating recovery points."""
        spec_id = "test-spec"
        
        recovery_point = await resilience_service.create_recovery_point(
            spec_id=spec_id,
            description="Test recovery point",
            auto_created=False
        )
        
        assert recovery_point.spec_id == spec_id
        assert recovery_point.description == "Test recovery point"
        assert not recovery_point.auto_created
        assert recovery_point.backup_id in resilience_service._backup_metadata
        
        # Verify recovery point is stored
        recovery_points = resilience_service.get_recovery_points(spec_id)
        assert len(recovery_points) == 1
        assert recovery_points[0].id == recovery_point.id
    
    @pytest.mark.asyncio
    async def test_restore_to_recovery_point(self, resilience_service, sample_spec_dir):
        """Test restoring to a recovery point."""
        spec_id = "test-spec"
        
        # Store original content
        original_content = (sample_spec_dir / "requirements.md").read_text()
        
        # Create recovery point
        recovery_point = await resilience_service.create_recovery_point(
            spec_id=spec_id,
            description="Before modification"
        )
        
        # Modify files
        (sample_spec_dir / "requirements.md").write_text("Modified requirements")
        
        # Restore to recovery point
        success = await resilience_service.restore_to_recovery_point(recovery_point.id)
        
        assert success
        
        # Verify restoration
        content = (sample_spec_dir / "requirements.md").read_text()
        assert original_content in content or "Sample requirements" in content
        assert "Modified requirements" not in content
    
    @pytest.mark.asyncio
    async def test_health_check_disk_space(self, resilience_service):
        """Test disk space health check."""
        health_check = await resilience_service._check_disk_space()
        
        assert health_check.name == "disk_space"
        assert health_check.status in [SystemHealthStatus.HEALTHY, SystemHealthStatus.WARNING, SystemHealthStatus.CRITICAL]
        assert "usage" in health_check.message.lower()
        assert "total_bytes" in health_check.details
        assert "usage_percent" in health_check.details
    
    @pytest.mark.asyncio
    async def test_health_check_file_system_integrity(self, resilience_service, sample_spec_dir):
        """Test file system integrity health check."""
        health_check = await resilience_service._check_file_system_integrity()
        
        assert health_check.name == "file_system_integrity"
        assert health_check.status in [SystemHealthStatus.HEALTHY, SystemHealthStatus.WARNING]
        assert "integrity" in health_check.message.lower()
    
    @pytest.mark.asyncio
    async def test_health_check_backup_system(self, resilience_service):
        """Test backup system health check."""
        health_check = await resilience_service._check_backup_system()
        
        assert health_check.name == "backup_system"
        assert health_check.status in [SystemHealthStatus.HEALTHY, SystemHealthStatus.WARNING, SystemHealthStatus.CRITICAL]
        assert "backup" in health_check.message.lower()
    
    @pytest.mark.asyncio
    async def test_health_check_transaction_health(self, resilience_service):
        """Test transaction health check."""
        health_check = await resilience_service._check_transaction_health()
        
        assert health_check.name == "transaction_health"
        assert health_check.status in [SystemHealthStatus.HEALTHY, SystemHealthStatus.WARNING]
        assert "transaction" in health_check.message.lower()
        assert "active_transactions" in health_check.details
    
    @pytest.mark.asyncio
    async def test_health_check_spec_consistency(self, resilience_service, sample_spec_dir):
        """Test spec consistency health check."""
        health_check = await resilience_service._check_spec_consistency()
        
        assert health_check.name == "spec_consistency"
        assert health_check.status in [SystemHealthStatus.HEALTHY, SystemHealthStatus.WARNING]
        assert "consistency" in health_check.message.lower()
    
    @pytest.mark.asyncio
    async def test_perform_comprehensive_health_check(self, resilience_service, sample_spec_dir):
        """Test comprehensive health check."""
        health_checks = await resilience_service.perform_health_check()
        
        assert len(health_checks) > 0
        
        # Check that all expected health checks are present
        check_names = [check.name for check in health_checks]
        expected_checks = [
            "disk_space",
            "file_system_integrity", 
            "backup_system",
            "transaction_health",
            "spec_consistency"
        ]
        
        for expected_check in expected_checks:
            assert expected_check in check_names
    
    def test_get_system_metrics(self, resilience_service):
        """Test getting system metrics."""
        # Mock psutil if available, otherwise skip the test
        try:
            import psutil
            with patch('psutil.cpu_percent') as mock_cpu, \
                 patch('psutil.virtual_memory') as mock_memory, \
                 patch('psutil.disk_usage') as mock_disk:
                
                mock_cpu.return_value = 45.0
                mock_memory.return_value = MagicMock(percent=60.0)
                mock_disk.return_value = MagicMock(percent=70.0)
                
                metrics = resilience_service.get_system_metrics()
                
                assert isinstance(metrics, SystemHealthMetrics)
                assert metrics.cpu_usage_percent == 45.0
                assert metrics.memory_usage_percent == 60.0
                assert metrics.disk_usage_percent == 70.0
                assert metrics.status == SystemHealthStatus.HEALTHY
                assert metrics.active_specs >= 0
                assert metrics.active_transactions >= 0
        except ImportError:
            pytest.skip("psutil not available")
    
    def test_cleanup_old_backups(self, resilience_service):
        """Test cleanup of old backups."""
        # Create some test backup metadata with old retention dates
        old_backup = BackupMetadata(
            id="old-backup",
            spec_id="test-spec",
            backup_type=BackupType.FULL,
            created_at=datetime.utcnow() - timedelta(days=40),
            size_bytes=1000,
            checksum="test-checksum",
            status=BackupStatus.COMPLETED,
            file_count=5,
            retention_until=datetime.utcnow() - timedelta(days=10)
        )
        
        recent_backup = BackupMetadata(
            id="recent-backup",
            spec_id="test-spec",
            backup_type=BackupType.FULL,
            created_at=datetime.utcnow() - timedelta(days=5),
            size_bytes=1000,
            checksum="test-checksum",
            status=BackupStatus.COMPLETED,
            file_count=5,
            retention_until=datetime.utcnow() + timedelta(days=20)
        )
        
        resilience_service._backup_metadata["old-backup"] = old_backup
        resilience_service._backup_metadata["recent-backup"] = recent_backup
        
        # Run cleanup
        cleaned_count = resilience_service.cleanup_old_backups()
        
        assert cleaned_count == 1
        assert "old-backup" not in resilience_service._backup_metadata
        assert "recent-backup" in resilience_service._backup_metadata
    
    def test_get_backup_list(self, resilience_service):
        """Test getting backup list."""
        # Create test backup metadata
        backup1 = BackupMetadata(
            id="backup-1",
            spec_id="spec-1",
            backup_type=BackupType.FULL,
            created_at=datetime.utcnow() - timedelta(hours=2),
            size_bytes=1000,
            checksum="checksum-1",
            status=BackupStatus.COMPLETED,
            file_count=5
        )
        
        backup2 = BackupMetadata(
            id="backup-2",
            spec_id="spec-2",
            backup_type=BackupType.FULL,
            created_at=datetime.utcnow() - timedelta(hours=1),
            size_bytes=2000,
            checksum="checksum-2",
            status=BackupStatus.COMPLETED,
            file_count=8
        )
        
        resilience_service._backup_metadata["backup-1"] = backup1
        resilience_service._backup_metadata["backup-2"] = backup2
        
        # Get all backups
        all_backups = resilience_service.get_backup_list()
        assert len(all_backups) == 2
        assert all_backups[0].id == "backup-2"  # Most recent first
        assert all_backups[1].id == "backup-1"
        
        # Get backups for specific spec
        spec1_backups = resilience_service.get_backup_list(spec_id="spec-1")
        assert len(spec1_backups) == 1
        assert spec1_backups[0].id == "backup-1"
    
    def test_get_recovery_points(self, resilience_service):
        """Test getting recovery points."""
        spec_id = "test-spec"
        
        # Create test recovery points
        recovery_point1 = RecoveryPoint(
            id="rp-1",
            spec_id=spec_id,
            timestamp=datetime.utcnow() - timedelta(hours=2),
            phase=WorkflowPhase.REQUIREMENTS,
            status=WorkflowStatus.IN_PROGRESS,
            backup_id="backup-1",
            description="First recovery point"
        )
        
        recovery_point2 = RecoveryPoint(
            id="rp-2",
            spec_id=spec_id,
            timestamp=datetime.utcnow() - timedelta(hours=1),
            phase=WorkflowPhase.DESIGN,
            status=WorkflowStatus.IN_PROGRESS,
            backup_id="backup-2",
            description="Second recovery point"
        )
        
        resilience_service._recovery_points[spec_id] = [recovery_point1, recovery_point2]
        
        # Get recovery points
        recovery_points = resilience_service.get_recovery_points(spec_id)
        assert len(recovery_points) == 2
        assert recovery_points[0].id in ["rp-1", "rp-2"]
        assert recovery_points[1].id in ["rp-1", "rp-2"]
    
    def test_get_health_history(self, resilience_service):
        """Test getting health history."""
        # Create test health metrics
        old_metrics = SystemHealthMetrics(
            timestamp=datetime.utcnow() - timedelta(hours=25),
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            disk_usage_percent=70.0,
            active_specs=5,
            active_transactions=2,
            backup_queue_size=1,
            error_rate_per_hour=0.5,
            response_time_ms=100.0,
            status=SystemHealthStatus.HEALTHY
        )
        
        recent_metrics = SystemHealthMetrics(
            timestamp=datetime.utcnow() - timedelta(hours=1),
            cpu_usage_percent=45.0,
            memory_usage_percent=55.0,
            disk_usage_percent=65.0,
            active_specs=6,
            active_transactions=1,
            backup_queue_size=0,
            error_rate_per_hour=0.2,
            response_time_ms=80.0,
            status=SystemHealthStatus.HEALTHY
        )
        
        resilience_service._health_history = [old_metrics, recent_metrics]
        
        # Get recent history (24 hours)
        recent_history = resilience_service.get_health_history(hours=24)
        assert len(recent_history) == 1
        assert recent_history[0].timestamp == recent_metrics.timestamp
        
        # Get longer history (48 hours)
        longer_history = resilience_service.get_health_history(hours=48)
        assert len(longer_history) == 2
    
    @pytest.mark.asyncio
    async def test_transaction_timeout_handling(self, resilience_service, sample_spec_dir):
        """Test transaction timeout handling."""
        spec_id = "test-spec"
        
        # Create transaction with short timeout
        transaction = TransactionContext(
            id="test-transaction",
            spec_id=spec_id,
            operation="test_operation",
            started_at=datetime.utcnow() - timedelta(seconds=400),  # Older than default timeout
            timeout_seconds=300
        )
        
        resilience_service._active_transactions["test-transaction"] = transaction
        
        # Check transaction health
        health_check = await resilience_service._check_transaction_health()
        
        assert health_check.status == SystemHealthStatus.WARNING
        assert "stuck" in health_check.message.lower()
        assert "test-transaction" in health_check.details["stuck_transactions"]
    
    def test_backup_metadata_persistence(self, resilience_service, sample_spec_dir):
        """Test backup metadata persistence."""
        # This test would verify that backup metadata is properly saved and loaded
        # For now, we'll test the structure
        backup_metadata = BackupMetadata(
            id="test-backup",
            spec_id="test-spec",
            backup_type=BackupType.FULL,
            created_at=datetime.utcnow(),
            size_bytes=1000,
            checksum="test-checksum",
            status=BackupStatus.COMPLETED,
            file_count=5
        )
        
        # Test serialization
        metadata_dict = backup_metadata.dict()
        assert "id" in metadata_dict
        assert "spec_id" in metadata_dict
        assert "backup_type" in metadata_dict
        
        # Test that it can be converted to JSON
        json_str = json.dumps(metadata_dict, default=str)
        assert json_str is not None
        
        # Test deserialization
        loaded_dict = json.loads(json_str)
        assert loaded_dict["id"] == backup_metadata.id