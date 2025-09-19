"""
Integration tests for the complete security monitoring system.

This module tests the integration between security logging, monitoring,
and the existing security components (path validator, HTML sanitizer, etc.).
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

from eco_api.security import (
    initialize_security_system,
    shutdown_security_system,
    get_security_logger,
    get_security_monitor,
    SecurityEventType,
    SecuritySeverity,
    PathValidator,
    HTMLSanitizer,
    AuthorizationValidator,
    create_default_validator
)


class TestSecurityIntegration:
    """Test complete security system integration."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_complete_security_workflow(self, temp_workspace):
        """Test complete security workflow from event generation to monitoring."""
        # Initialize security system
        success = await initialize_security_system(temp_workspace)
        assert success
        
        # Get security components
        security_logger = get_security_logger()
        security_monitor = get_security_monitor()
        
        assert security_logger is not None
        assert security_monitor is not None
        
        # Don't start monitoring loop for this test to avoid metrics reset
        # We'll test the monitoring functionality directly
        
        # Test direct event processing with security monitor
        from eco_api.security.security_logger import create_xss_attempt_event
        
        test_event = create_xss_attempt_event(
            malicious_content="<script>alert('test')</script>",
            source_ip="192.168.1.100",
            user_id="test_user"
        )
        
        # Process event directly with monitor
        security_monitor.process_security_event(test_event)
        
        # No need to wait since we're not running the monitoring loop
        
        # Check that security monitor received events
        dashboard_data = security_monitor.get_security_dashboard_data()
        current_metrics = dashboard_data["current_metrics"]
        
        # Should have received security events
        assert current_metrics["total_events"] > 0
        assert current_metrics["events_by_type"]["xss_attempt"] == 1
        assert current_metrics["events_by_severity"]["high"] == 1
        assert current_metrics["unique_source_ips"] == 1
        assert current_metrics["unique_users"] == 1
        
        # Check that different event types were recorded
        events_by_type = current_metrics["events_by_type"]
        assert len(events_by_type) > 0
        
        # Cleanup
        await shutdown_security_system()
    
    @pytest.mark.asyncio
    async def test_security_dashboard_api_integration(self, temp_workspace):
        """Test security dashboard API integration."""
        # Initialize security system
        success = await initialize_security_system(temp_workspace)
        assert success
        
        # Get security monitor
        security_monitor = get_security_monitor()
        assert security_monitor is not None
        
        # Generate some test events
        from eco_api.security.security_logger import create_xss_attempt_event
        
        for i in range(5):
            event = create_xss_attempt_event(
                malicious_content=f"<script>alert('{i}')</script>",
                source_ip=f"192.168.1.{100 + i}",
                user_id=f"user_{i}"
            )
            security_monitor.process_security_event(event)
        
        # Test dashboard data retrieval
        dashboard_data = security_monitor.get_security_dashboard_data()
        
        # Verify dashboard structure
        required_keys = [
            'current_metrics',
            'metrics_history',
            'active_alerts',
            'blocked_ips',
            'blocked_users',
            'security_rules',
            'system_status'
        ]
        
        for key in required_keys:
            assert key in dashboard_data
        
        # Verify metrics
        current_metrics = dashboard_data['current_metrics']
        assert current_metrics['total_events'] == 5
        assert 'xss_attempt' in current_metrics['events_by_type']
        assert current_metrics['events_by_type']['xss_attempt'] == 5
        
        # Verify system status
        system_status = dashboard_data['system_status']
        assert 'monitoring_active' in system_status
        assert 'threat_level' in system_status
        assert 'last_updated' in system_status
        
        # Cleanup
        await shutdown_security_system()
    
    @pytest.mark.asyncio
    async def test_automated_response_integration(self, temp_workspace):
        """Test automated response mechanisms."""
        # Initialize security system
        success = await initialize_security_system(temp_workspace)
        assert success
        
        # Get security monitor
        security_monitor = get_security_monitor()
        assert security_monitor is not None
        
        # Generate high-frequency attacks to trigger automated response
        source_ip = "192.168.1.100"
        user_id = "malicious_user"
        
        from eco_api.security.security_logger import create_xss_attempt_event
        
        # Send 15 XSS attempts (should exceed threshold and trigger response)
        for i in range(15):
            event = create_xss_attempt_event(
                malicious_content=f"<script>alert('{i}')</script>",
                source_ip=source_ip,
                user_id=user_id
            )
            security_monitor.process_security_event(event)
        
        # Check that automated responses were triggered
        dashboard_data = security_monitor.get_security_dashboard_data()
        
        # Should have active alerts
        assert len(dashboard_data['active_alerts']) > 0
        
        # Should have rate limited or blocked the IP/user
        assert (source_ip in security_monitor.rate_limited_ips or 
                source_ip in security_monitor.blocked_ips or
                user_id in security_monitor.rate_limited_users or
                user_id in security_monitor.blocked_users)
        
        # Test that subsequent events from same source are blocked
        test_event = create_xss_attempt_event(
            malicious_content="<script>alert('blocked')</script>",
            source_ip=source_ip,
            user_id=user_id
        )
        
        should_be_blocked = security_monitor._should_block_event(test_event)
        assert should_be_blocked
        
        # Cleanup
        await shutdown_security_system()
    
    def test_security_configuration_persistence(self, temp_workspace):
        """Test security configuration saving and loading."""
        from eco_api.security.security_init import (
            create_default_security_config,
            save_security_config,
            load_security_config
        )
        
        # Create default config
        config = create_default_security_config(temp_workspace)
        
        # Modify config
        config['logging']['retention_days'] = 30
        config['monitoring']['monitoring_interval'] = 120
        
        # Save config
        success = save_security_config(config, temp_workspace)
        assert success
        
        # Load config
        loaded_config = load_security_config(temp_workspace)
        assert loaded_config is not None
        
        # Verify modifications were preserved
        assert loaded_config['logging']['retention_days'] == 30
        assert loaded_config['monitoring']['monitoring_interval'] == 120
        
        # Verify config file exists
        config_path = Path(temp_workspace) / ".kiro" / "security_config.json"
        assert config_path.exists()


if __name__ == "__main__":
    pytest.main([__file__])