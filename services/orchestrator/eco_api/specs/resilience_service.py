"""
System resilience and data protection service for spec-driven workflows.

This module provides backup and recovery mechanisms, transaction-like operations,
and system health monitoring for the spec workflow system.
"""

import asyncio
import json
import shutil
import tempfile
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from pydantic import BaseModel, Field
import logging
import hashlib
import os
import time
from contextlib import asynccontextmanager

from .models import WorkflowPhase, WorkflowStatus, SpecMetadata, DocumentMetadata


class BackupType(str, Enum):
    """Types of backups."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(str, Enum):
    """Status of backup operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"


class RecoveryType(str, Enum):
    """Types of recovery operations."""
    FULL_RESTORE = "full_restore"
    PARTIAL_RESTORE = "partial_restore"
    POINT_IN_TIME = "point_in_time"
    FILE_RECOVERY = "file_recovery"


class SystemHealthStatus(str, Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class BackupMetadata(BaseModel):
    """Metadata for backup operations."""
    id: str
    spec_id: str
    backup_type: BackupType
    created_at: datetime
    size_bytes: int
    checksum: str
    status: BackupStatus
    file_count: int
    compression_ratio: Optional[float] = None
    retention_until: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class RecoveryPoint(BaseModel):
    """A point-in-time recovery checkpoint."""
    id: str
    spec_id: str
    timestamp: datetime
    phase: WorkflowPhase
    status: WorkflowStatus
    backup_id: str
    description: str
    auto_created: bool = True


class TransactionContext(BaseModel):
    """Context for transaction-like operations."""
    id: str
    spec_id: str
    operation: str
    started_at: datetime
    timeout_seconds: int = 300
    rollback_data: Dict[str, Any] = Field(default_factory=dict)
    checkpoints: List[str] = Field(default_factory=list)
    completed: bool = False
    rolled_back: bool = False


class SystemHealthMetrics(BaseModel):
    """System health monitoring metrics."""
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    active_specs: int
    active_transactions: int
    backup_queue_size: int
    error_rate_per_hour: float
    response_time_ms: float
    status: SystemHealthStatus


class HealthCheck(BaseModel):
    """Individual health check result."""
    name: str
    status: SystemHealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = Field(default_factory=dict)


class ResilienceService:
    """
    Service for system resilience and data protection.
    
    Provides backup and recovery mechanisms, transaction-like operations,
    and system health monitoring for robust spec workflow management.
    """
    
    def __init__(self, base_path: str = ".kiro/specs", backup_path: str = ".kiro/backups"):
        self.logger = logging.getLogger(__name__)
        self.base_path = Path(base_path)
        self.backup_path = Path(backup_path)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory tracking
        self._active_transactions: Dict[str, TransactionContext] = {}
        self._backup_metadata: Dict[str, BackupMetadata] = {}
        self._recovery_points: Dict[str, List[RecoveryPoint]] = {}
        self._health_checks: List[Callable] = []
        self._health_history: List[SystemHealthMetrics] = []
        
        # Configuration
        self.backup_retention_days = 30
        self.max_backup_size_mb = 1000
        self.health_check_interval = 300  # 5 minutes
        self.transaction_timeout = 300  # 5 minutes
        
        # Initialize health checks
        self._setup_health_checks()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _setup_health_checks(self) -> None:
        """Set up default health checks."""
        self._health_checks.extend([
            self._check_disk_space,
            self._check_file_system_integrity,
            self._check_backup_system,
            self._check_transaction_health,
            self._check_spec_consistency
        ])
    
    def _start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks."""
        # In a real implementation, these would be proper async tasks
        # For now, we'll implement the methods but not start actual background tasks
        pass
    
    async def create_backup(
        self,
        spec_id: str,
        backup_type: BackupType = BackupType.FULL,
        tags: Optional[List[str]] = None
    ) -> BackupMetadata:
        """
        Create a backup of a spec.
        
        Args:
            spec_id: ID of the spec to backup
            backup_type: Type of backup to create
            tags: Optional tags for the backup
            
        Returns:
            BackupMetadata for the created backup
        """
        import uuid
        
        backup_id = str(uuid.uuid4())
        if tags is None:
            tags = []
        
        self.logger.info(f"Creating {backup_type} backup for spec {spec_id}")
        
        try:
            # Create backup directory
            backup_dir = self.backup_path / backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Get spec directory
            spec_dir = self.base_path / spec_id
            if not spec_dir.exists():
                raise FileNotFoundError(f"Spec directory not found: {spec_dir}")
            
            # Perform backup based on type
            if backup_type == BackupType.FULL:
                await self._create_full_backup(spec_dir, backup_dir)
            elif backup_type == BackupType.INCREMENTAL:
                await self._create_incremental_backup(spec_id, spec_dir, backup_dir)
            elif backup_type == BackupType.SNAPSHOT:
                await self._create_snapshot_backup(spec_dir, backup_dir)
            else:
                raise ValueError(f"Unsupported backup type: {backup_type}")
            
            # Calculate backup metadata
            size_bytes = self._calculate_directory_size(backup_dir)
            checksum = await self._calculate_backup_checksum(backup_dir)
            file_count = len(list(backup_dir.rglob("*")))
            
            # Create backup metadata
            backup_metadata = BackupMetadata(
                id=backup_id,
                spec_id=spec_id,
                backup_type=backup_type,
                created_at=datetime.utcnow(),
                size_bytes=size_bytes,
                checksum=checksum,
                status=BackupStatus.COMPLETED,
                file_count=file_count,
                retention_until=datetime.utcnow() + timedelta(days=self.backup_retention_days),
                tags=tags
            )
            
            # Store metadata
            self._backup_metadata[backup_id] = backup_metadata
            await self._save_backup_metadata(backup_metadata)
            
            self.logger.info(f"Backup {backup_id} created successfully")
            return backup_metadata
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            
            # Clean up failed backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
            
            # Create failed backup metadata
            failed_metadata = BackupMetadata(
                id=backup_id,
                spec_id=spec_id,
                backup_type=backup_type,
                created_at=datetime.utcnow(),
                size_bytes=0,
                checksum="",
                status=BackupStatus.FAILED,
                file_count=0,
                tags=tags
            )
            
            self._backup_metadata[backup_id] = failed_metadata
            raise
    
    async def _create_full_backup(self, source_dir: Path, backup_dir: Path) -> None:
        """Create a full backup by copying all files."""
        shutil.copytree(source_dir, backup_dir / "data", dirs_exist_ok=True)
    
    async def _create_incremental_backup(
        self,
        spec_id: str,
        source_dir: Path,
        backup_dir: Path
    ) -> None:
        """Create an incremental backup based on the last backup."""
        # Find the last backup
        last_backup = self._get_last_backup(spec_id)
        
        if not last_backup:
            # No previous backup, create full backup
            await self._create_full_backup(source_dir, backup_dir)
            return
        
        # Compare files and copy only changed ones
        last_backup_time = last_backup.created_at
        
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                file_stat = file_path.stat()
                if datetime.fromtimestamp(file_stat.st_mtime) > last_backup_time:
                    # File was modified since last backup
                    relative_path = file_path.relative_to(source_dir)
                    dest_path = backup_dir / "data" / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest_path)
    
    async def _create_snapshot_backup(self, source_dir: Path, backup_dir: Path) -> None:
        """Create a snapshot backup with compression."""
        import tarfile
        
        snapshot_file = backup_dir / "snapshot.tar.gz"
        
        with tarfile.open(snapshot_file, "w:gz") as tar:
            tar.add(source_dir, arcname="data")
    
    def _get_last_backup(self, spec_id: str) -> Optional[BackupMetadata]:
        """Get the most recent backup for a spec."""
        spec_backups = [
            backup for backup in self._backup_metadata.values()
            if backup.spec_id == spec_id and backup.status == BackupStatus.COMPLETED
        ]
        
        if not spec_backups:
            return None
        
        return max(spec_backups, key=lambda b: b.created_at)
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of a directory in bytes."""
        total_size = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    async def _calculate_backup_checksum(self, backup_dir: Path) -> str:
        """Calculate checksum for backup verification."""
        hasher = hashlib.sha256()
        
        for file_path in sorted(backup_dir.rglob("*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
        
        return hasher.hexdigest()
    
    async def _save_backup_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to disk."""
        metadata_file = self.backup_path / f"{metadata.id}.metadata.json"
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata.dict(), f, indent=2, default=str)
    
    async def restore_from_backup(
        self,
        backup_id: str,
        recovery_type: RecoveryType = RecoveryType.FULL_RESTORE,
        target_spec_id: Optional[str] = None
    ) -> bool:
        """
        Restore a spec from backup.
        
        Args:
            backup_id: ID of the backup to restore from
            recovery_type: Type of recovery to perform
            target_spec_id: Optional target spec ID (for restore to different location)
            
        Returns:
            True if restore was successful, False otherwise
        """
        if backup_id not in self._backup_metadata:
            raise ValueError(f"Backup not found: {backup_id}")
        
        backup_metadata = self._backup_metadata[backup_id]
        
        if backup_metadata.status != BackupStatus.COMPLETED:
            raise ValueError(f"Cannot restore from backup with status: {backup_metadata.status}")
        
        spec_id = target_spec_id or backup_metadata.spec_id
        
        self.logger.info(f"Restoring spec {spec_id} from backup {backup_id}")
        
        try:
            # Verify backup integrity
            if not await self._verify_backup_integrity(backup_id):
                raise ValueError("Backup integrity check failed")
            
            # Create transaction for rollback capability
            async with self.create_transaction(spec_id, f"restore_from_backup_{backup_id}"):
                # Perform restore based on type
                if recovery_type == RecoveryType.FULL_RESTORE:
                    await self._perform_full_restore(backup_id, spec_id)
                elif recovery_type == RecoveryType.PARTIAL_RESTORE:
                    await self._perform_partial_restore(backup_id, spec_id)
                else:
                    raise ValueError(f"Unsupported recovery type: {recovery_type}")
            
            self.logger.info(f"Restore completed successfully for spec {spec_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return False
    
    async def _verify_backup_integrity(self, backup_id: str) -> bool:
        """Verify the integrity of a backup."""
        backup_metadata = self._backup_metadata[backup_id]
        backup_dir = self.backup_path / backup_id
        
        if not backup_dir.exists():
            return False
        
        # Recalculate checksum and compare
        current_checksum = await self._calculate_backup_checksum(backup_dir)
        return current_checksum == backup_metadata.checksum
    
    async def _perform_full_restore(self, backup_id: str, spec_id: str) -> None:
        """Perform a full restore from backup."""
        backup_dir = self.backup_path / backup_id
        spec_dir = self.base_path / spec_id
        
        # Remove existing spec directory if it exists
        if spec_dir.exists():
            shutil.rmtree(spec_dir)
        
        # Copy backup data to spec directory
        backup_data_dir = backup_dir / "data"
        if backup_data_dir.exists():
            shutil.copytree(backup_data_dir, spec_dir)
        else:
            # Handle snapshot backup
            snapshot_file = backup_dir / "snapshot.tar.gz"
            if snapshot_file.exists():
                import tarfile
                with tarfile.open(snapshot_file, "r:gz") as tar:
                    tar.extractall(spec_dir.parent)
    
    async def _perform_partial_restore(self, backup_id: str, spec_id: str) -> None:
        """Perform a partial restore from backup."""
        # This would allow selective file restoration
        # For now, implement as full restore
        await self._perform_full_restore(backup_id, spec_id)
    
    @asynccontextmanager
    async def create_transaction(self, spec_id: str, operation: str, timeout: int = 300):
        """
        Create a transaction context for atomic operations.
        
        Args:
            spec_id: ID of the spec being operated on
            operation: Description of the operation
            timeout: Transaction timeout in seconds
            
        Yields:
            TransactionContext for the operation
        """
        import uuid
        
        transaction_id = str(uuid.uuid4())
        
        # Create transaction context
        transaction = TransactionContext(
            id=transaction_id,
            spec_id=spec_id,
            operation=operation,
            started_at=datetime.utcnow(),
            timeout_seconds=timeout
        )
        
        # Store rollback data
        await self._capture_rollback_data(transaction)
        
        # Add to active transactions
        self._active_transactions[transaction_id] = transaction
        
        try:
            self.logger.info(f"Starting transaction {transaction_id} for spec {spec_id}")
            yield transaction
            
            # Mark as completed
            transaction.completed = True
            self.logger.info(f"Transaction {transaction_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Transaction {transaction_id} failed: {e}")
            
            # Perform rollback
            await self._rollback_transaction(transaction)
            raise
            
        finally:
            # Clean up transaction
            if transaction_id in self._active_transactions:
                del self._active_transactions[transaction_id]
    
    async def _capture_rollback_data(self, transaction: TransactionContext) -> None:
        """Capture data needed for transaction rollback."""
        spec_dir = self.base_path / transaction.spec_id
        
        if spec_dir.exists():
            # Create a temporary backup for rollback
            temp_backup_dir = tempfile.mkdtemp(prefix=f"rollback_{transaction.id}_")
            shutil.copytree(spec_dir, temp_backup_dir, dirs_exist_ok=True)
            
            transaction.rollback_data["backup_path"] = temp_backup_dir
            transaction.rollback_data["original_exists"] = True
        else:
            transaction.rollback_data["original_exists"] = False
    
    async def _rollback_transaction(self, transaction: TransactionContext) -> None:
        """Rollback a failed transaction."""
        self.logger.info(f"Rolling back transaction {transaction.id}")
        
        spec_dir = self.base_path / transaction.spec_id
        
        try:
            if transaction.rollback_data.get("original_exists", False):
                # Restore from rollback backup
                backup_path = transaction.rollback_data.get("backup_path")
                if backup_path and Path(backup_path).exists():
                    if spec_dir.exists():
                        shutil.rmtree(spec_dir)
                    shutil.copytree(backup_path, spec_dir)
            else:
                # Remove created directory
                if spec_dir.exists():
                    shutil.rmtree(spec_dir)
            
            transaction.rolled_back = True
            self.logger.info(f"Transaction {transaction.id} rolled back successfully")
            
        except Exception as e:
            self.logger.error(f"Rollback failed for transaction {transaction.id}: {e}")
        
        finally:
            # Clean up rollback backup
            backup_path = transaction.rollback_data.get("backup_path")
            if backup_path and Path(backup_path).exists():
                shutil.rmtree(backup_path, ignore_errors=True)
    
    async def create_recovery_point(
        self,
        spec_id: str,
        description: str,
        auto_created: bool = True
    ) -> RecoveryPoint:
        """Create a recovery point for a spec."""
        import uuid
        
        # Create backup first
        backup_metadata = await self.create_backup(
            spec_id,
            BackupType.SNAPSHOT,
            tags=["recovery_point"]
        )
        
        # Create recovery point
        recovery_point = RecoveryPoint(
            id=str(uuid.uuid4()),
            spec_id=spec_id,
            timestamp=datetime.utcnow(),
            phase=WorkflowPhase.REQUIREMENTS,  # This should be determined from spec state
            status=WorkflowStatus.IN_PROGRESS,  # This should be determined from spec state
            backup_id=backup_metadata.id,
            description=description,
            auto_created=auto_created
        )
        
        # Store recovery point
        if spec_id not in self._recovery_points:
            self._recovery_points[spec_id] = []
        
        self._recovery_points[spec_id].append(recovery_point)
        
        # Keep only recent recovery points (limit to 10 per spec)
        self._recovery_points[spec_id] = sorted(
            self._recovery_points[spec_id],
            key=lambda rp: rp.timestamp,
            reverse=True
        )[:10]
        
        return recovery_point
    
    async def restore_to_recovery_point(self, recovery_point_id: str) -> bool:
        """Restore a spec to a specific recovery point."""
        # Find recovery point
        recovery_point = None
        for spec_recovery_points in self._recovery_points.values():
            for rp in spec_recovery_points:
                if rp.id == recovery_point_id:
                    recovery_point = rp
                    break
            if recovery_point:
                break
        
        if not recovery_point:
            raise ValueError(f"Recovery point not found: {recovery_point_id}")
        
        # Restore from the associated backup
        return await self.restore_from_backup(
            recovery_point.backup_id,
            RecoveryType.FULL_RESTORE,
            recovery_point.spec_id
        )
    
    async def perform_health_check(self) -> List[HealthCheck]:
        """Perform comprehensive system health check."""
        health_checks = []
        
        for check_func in self._health_checks:
            try:
                check_result = await check_func()
                health_checks.append(check_result)
            except Exception as e:
                health_checks.append(HealthCheck(
                    name=check_func.__name__,
                    status=SystemHealthStatus.CRITICAL,
                    message=f"Health check failed: {e}",
                    timestamp=datetime.utcnow()
                ))
        
        return health_checks
    
    async def _check_disk_space(self) -> HealthCheck:
        """Check available disk space."""
        import shutil
        
        total, used, free = shutil.disk_usage(self.base_path)
        usage_percent = (used / total) * 100
        
        if usage_percent > 90:
            status = SystemHealthStatus.CRITICAL
            message = f"Disk usage critical: {usage_percent:.1f}%"
        elif usage_percent > 80:
            status = SystemHealthStatus.WARNING
            message = f"Disk usage high: {usage_percent:.1f}%"
        else:
            status = SystemHealthStatus.HEALTHY
            message = f"Disk usage normal: {usage_percent:.1f}%"
        
        return HealthCheck(
            name="disk_space",
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
            details={
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "usage_percent": usage_percent
            }
        )
    
    async def _check_file_system_integrity(self) -> HealthCheck:
        """Check file system integrity."""
        corrupted_files = []
        
        # Check spec directories
        for spec_dir in self.base_path.iterdir():
            if spec_dir.is_dir():
                try:
                    # Basic integrity checks
                    required_files = ["requirements.md", "design.md", "tasks.md"]
                    for req_file in required_files:
                        file_path = spec_dir / req_file
                        if file_path.exists():
                            # Try to read the file
                            with open(file_path, 'r', encoding='utf-8') as f:
                                f.read()
                except Exception as e:
                    corrupted_files.append(f"{spec_dir.name}: {e}")
        
        if corrupted_files:
            status = SystemHealthStatus.WARNING
            message = f"Found {len(corrupted_files)} file integrity issues"
        else:
            status = SystemHealthStatus.HEALTHY
            message = "File system integrity check passed"
        
        return HealthCheck(
            name="file_system_integrity",
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
            details={"corrupted_files": corrupted_files}
        )
    
    async def _check_backup_system(self) -> HealthCheck:
        """Check backup system health."""
        if not self.backup_path.exists():
            return HealthCheck(
                name="backup_system",
                status=SystemHealthStatus.CRITICAL,
                message="Backup directory does not exist",
                timestamp=datetime.utcnow()
            )
        
        # Check recent backups
        recent_backups = [
            backup for backup in self._backup_metadata.values()
            if (datetime.utcnow() - backup.created_at).days < 7
        ]
        
        failed_backups = [
            backup for backup in recent_backups
            if backup.status == BackupStatus.FAILED
        ]
        
        if len(failed_backups) > len(recent_backups) * 0.5:
            status = SystemHealthStatus.CRITICAL
            message = f"High backup failure rate: {len(failed_backups)}/{len(recent_backups)}"
        elif failed_backups:
            status = SystemHealthStatus.WARNING
            message = f"Some backup failures: {len(failed_backups)}/{len(recent_backups)}"
        else:
            status = SystemHealthStatus.HEALTHY
            message = f"Backup system healthy: {len(recent_backups)} recent backups"
        
        return HealthCheck(
            name="backup_system",
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
            details={
                "recent_backups": len(recent_backups),
                "failed_backups": len(failed_backups)
            }
        )
    
    async def _check_transaction_health(self) -> HealthCheck:
        """Check transaction system health."""
        current_time = datetime.utcnow()
        
        # Check for stuck transactions
        stuck_transactions = []
        for transaction in self._active_transactions.values():
            age_seconds = (current_time - transaction.started_at).total_seconds()
            if age_seconds > transaction.timeout_seconds:
                stuck_transactions.append(transaction.id)
        
        if stuck_transactions:
            status = SystemHealthStatus.WARNING
            message = f"Found {len(stuck_transactions)} stuck transactions"
        else:
            status = SystemHealthStatus.HEALTHY
            message = f"Transaction system healthy: {len(self._active_transactions)} active"
        
        return HealthCheck(
            name="transaction_health",
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
            details={
                "active_transactions": len(self._active_transactions),
                "stuck_transactions": stuck_transactions
            }
        )
    
    async def _check_spec_consistency(self) -> HealthCheck:
        """Check spec consistency across the system."""
        inconsistent_specs = []
        
        # Check each spec directory
        for spec_dir in self.base_path.iterdir():
            if spec_dir.is_dir():
                try:
                    # Check for metadata file
                    metadata_file = spec_dir / ".spec-metadata.json"
                    if not metadata_file.exists():
                        inconsistent_specs.append(f"{spec_dir.name}: missing metadata")
                        continue
                    
                    # Validate metadata
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check required fields
                    required_fields = ["id", "feature_name", "current_phase", "status"]
                    for field in required_fields:
                        if field not in metadata:
                            inconsistent_specs.append(f"{spec_dir.name}: missing {field} in metadata")
                
                except Exception as e:
                    inconsistent_specs.append(f"{spec_dir.name}: {e}")
        
        if inconsistent_specs:
            status = SystemHealthStatus.WARNING
            message = f"Found {len(inconsistent_specs)} spec consistency issues"
        else:
            status = SystemHealthStatus.HEALTHY
            message = "Spec consistency check passed"
        
        return HealthCheck(
            name="spec_consistency",
            status=status,
            message=message,
            timestamp=datetime.utcnow(),
            details={"inconsistent_specs": inconsistent_specs}
        )
    
    def get_system_metrics(self) -> SystemHealthMetrics:
        """Get current system health metrics."""
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(self.base_path))
        
        # Calculate application-specific metrics
        active_specs = len([d for d in self.base_path.iterdir() if d.is_dir()])
        active_transactions = len(self._active_transactions)
        backup_queue_size = len([b for b in self._backup_metadata.values() 
                               if b.status == BackupStatus.PENDING])
        
        # Calculate error rate (simplified)
        error_rate = 0.0  # Would be calculated from actual error logs
        
        # Calculate response time (simplified)
        response_time = 50.0  # Would be calculated from actual metrics
        
        # Determine overall status
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = SystemHealthStatus.CRITICAL
        elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
            status = SystemHealthStatus.WARNING
        else:
            status = SystemHealthStatus.HEALTHY
        
        metrics = SystemHealthMetrics(
            timestamp=datetime.utcnow(),
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory.percent,
            disk_usage_percent=disk.percent,
            active_specs=active_specs,
            active_transactions=active_transactions,
            backup_queue_size=backup_queue_size,
            error_rate_per_hour=error_rate,
            response_time_ms=response_time,
            status=status
        )
        
        # Store in history
        self._health_history.append(metrics)
        
        # Keep only recent history (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self._health_history = [
            m for m in self._health_history
            if m.timestamp > cutoff_time
        ]
        
        return metrics
    
    def cleanup_old_backups(self) -> int:
        """Clean up old backups based on retention policy."""
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        for backup_id, backup_metadata in list(self._backup_metadata.items()):
            if (backup_metadata.retention_until and 
                current_time > backup_metadata.retention_until):
                
                # Remove backup files
                backup_dir = self.backup_path / backup_id
                if backup_dir.exists():
                    shutil.rmtree(backup_dir, ignore_errors=True)
                
                # Remove metadata
                metadata_file = self.backup_path / f"{backup_id}.metadata.json"
                if metadata_file.exists():
                    metadata_file.unlink(missing_ok=True)
                
                # Remove from memory
                del self._backup_metadata[backup_id]
                cleaned_count += 1
        
        self.logger.info(f"Cleaned up {cleaned_count} old backups")
        return cleaned_count
    
    def get_backup_list(self, spec_id: Optional[str] = None) -> List[BackupMetadata]:
        """Get list of available backups."""
        backups = list(self._backup_metadata.values())
        
        if spec_id:
            backups = [b for b in backups if b.spec_id == spec_id]
        
        return sorted(backups, key=lambda b: b.created_at, reverse=True)
    
    def get_recovery_points(self, spec_id: str) -> List[RecoveryPoint]:
        """Get available recovery points for a spec."""
        return self._recovery_points.get(spec_id, [])
    
    def get_health_history(self, hours: int = 24) -> List[SystemHealthMetrics]:
        """Get system health history for the specified number of hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            m for m in self._health_history
            if m.timestamp > cutoff_time
        ]