"""
Unit tests for Phase 3: Intelligent Alerting System
Tests alert rules, alert manager, and API endpoints
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.monitoring.alerting import (
    AlertManager,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertType,
    log_alert_handler,
    console_alert_handler
)
from backend.monitoring.collector import MetricsCollector
from backend.routes.alerts import AlertResponse


class TestAlert:
    """Test Alert data structure"""
    
    def test_alert_creation(self):
        """Test creating an alert"""
        alert = Alert(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            organization_id="org-123",
            destination_name="cleverbrag"
        )
        
        assert alert.alert_type == AlertType.DESTINATION_DOWN
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.title == "Test Alert"
        assert alert.organization_id == "org-123"
        assert alert.destination_name == "cleverbrag"
        assert not alert.resolved
        assert alert.resolved_at is None
        assert isinstance(alert.timestamp, datetime)
    
    def test_alert_with_metadata(self):
        """Test alert with metadata"""
        metadata = {"error_count": 5, "last_error": "Connection failed"}
        
        alert = Alert(
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.WARNING,
            title="High Error Rate",
            message="Error rate exceeded threshold",
            organization_id="org-123",
            metadata=metadata
        )
        
        assert alert.metadata == metadata
        assert alert.metadata["error_count"] == 5


class TestAlertRule:
    """Test AlertRule configuration"""
    
    def test_alert_rule_creation(self):
        """Test creating an alert rule"""
        rule = AlertRule(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: metrics.get('health_status') == 0,
            title_template="Destination {destination_name} is down",
            message_template="Destination {destination_name} is not responding",
            cooldown_minutes=15
        )
        
        assert rule.alert_type == AlertType.DESTINATION_DOWN
        assert rule.severity == AlertSeverity.CRITICAL
        assert rule.cooldown_minutes == 15
        assert rule.enabled is True
    
    def test_alert_rule_condition(self):
        """Test alert rule condition evaluation"""
        rule = AlertRule(
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.WARNING,
            condition=lambda metrics: metrics.get('error_rate', 0) > 10,
            title_template="High error rate",
            message_template="Error rate is {error_rate}%"
        )
        
        # Test condition that should trigger
        assert rule.condition({"error_rate": 15}) is True
        
        # Test condition that should not trigger
        assert rule.condition({"error_rate": 5}) is False
        assert rule.condition({}) is False


class TestAlertManager:
    """Test AlertManager functionality"""
    
    def test_alert_manager_initialization(self):
        """Test alert manager initializes with default rules"""
        manager = AlertManager()
        
        assert len(manager._alert_rules) > 0
        assert len(manager._alert_handlers) == 0  # No default handlers in test
        assert manager._active_alerts == {}
        assert manager._alert_history == []
    
    def test_add_rule(self):
        """Test adding alert rules"""
        manager = AlertManager()
        initial_count = len(manager._alert_rules)
        
        rule = AlertRule(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: True,
            title_template="Test",
            message_template="Test message"
        )
        
        manager.add_rule(rule)
        assert len(manager._alert_rules) == initial_count + 1
    
    def test_add_handler(self):
        """Test adding alert handlers"""
        manager = AlertManager()
        
        def test_handler(alert: Alert):
            pass
        
        manager.add_handler(test_handler)
        assert len(manager._alert_handlers) == 1
    
    def test_evaluate_metrics_trigger_alert(self):
        """Test triggering an alert based on metrics"""
        manager = AlertManager()
        
        # Add a simple test rule
        test_rule = AlertRule(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: metrics.get('status') == 'down',
            title_template="Test destination {destination_name} down",
            message_template="Destination {destination_name} is down",
            cooldown_minutes=1
        )
        manager.add_rule(test_rule)
        
        # Mock handler to capture alerts
        captured_alerts = []
        def capture_handler(alert: Alert):
            captured_alerts.append(alert)
        manager.add_handler(capture_handler)
        
        # Trigger alert
        metrics = {"status": "down"}
        triggered = manager.evaluate_metrics(
            organization_id="org-123",
            destination_name="test-dest",
            metrics=metrics
        )
        
        assert len(triggered) == 1
        assert triggered[0].alert_type == AlertType.DESTINATION_DOWN
        assert triggered[0].severity == AlertSeverity.CRITICAL
        assert "test-dest" in triggered[0].title
        assert len(captured_alerts) == 1
    
    def test_evaluate_metrics_no_trigger(self):
        """Test not triggering alert when condition not met"""
        manager = AlertManager()
        
        # Add a test rule that won't trigger
        test_rule = AlertRule(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: metrics.get('status') == 'down',
            title_template="Test",
            message_template="Test"
        )
        manager.add_rule(test_rule)
        
        # Don't trigger alert
        metrics = {"status": "up"}
        triggered = manager.evaluate_metrics(
            organization_id="org-123",
            destination_name="test-dest",
            metrics=metrics
        )
        
        assert len(triggered) == 0
    
    def test_cooldown_period(self):
        """Test alert cooldown period"""
        manager = AlertManager()
        
        # Add rule with short cooldown
        test_rule = AlertRule(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: metrics.get('status') == 'down',
            title_template="Test",
            message_template="Test",
            cooldown_minutes=60  # 1 hour cooldown
        )
        manager.add_rule(test_rule)
        
        metrics = {"status": "down"}
        
        # First trigger should work
        triggered1 = manager.evaluate_metrics(
            organization_id="org-123",
            destination_name="test-dest",
            metrics=metrics
        )
        assert len(triggered1) == 1
        
        # Second trigger should be blocked by cooldown
        triggered2 = manager.evaluate_metrics(
            organization_id="org-123",
            destination_name="test-dest",
            metrics=metrics
        )
        assert len(triggered2) == 0
    
    def test_alert_resolution(self):
        """Test alert resolution when condition no longer met"""
        manager = AlertManager()
        
        # Add test rule
        test_rule = AlertRule(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            condition=lambda metrics: metrics.get('status') == 'down',
            title_template="Test",
            message_template="Test"
        )
        manager.add_rule(test_rule)
        
        # Trigger alert
        manager.evaluate_metrics(
            organization_id="org-123",
            destination_name="test-dest",
            metrics={"status": "down"}
        )
        
        # Verify alert is active
        active_alerts = manager.get_active_alerts(organization_id="org-123")
        assert len(active_alerts) == 1
        assert not active_alerts[0].resolved
        
        # Resolve condition
        manager.evaluate_metrics(
            organization_id="org-123",
            destination_name="test-dest",
            metrics={"status": "up"}
        )
        
        # Verify alert is resolved
        active_alerts = manager.get_active_alerts(organization_id="org-123")
        assert len(active_alerts) == 0  # Should be filtered out
    
    def test_get_active_alerts_filtering(self):
        """Test filtering active alerts"""
        manager = AlertManager()
        
        # Create test alerts
        alert1 = Alert(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            title="Alert 1",
            message="Message 1",
            organization_id="org-123"
        )
        
        alert2 = Alert(
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.WARNING,
            title="Alert 2",
            message="Message 2",
            organization_id="org-456"
        )
        
        # Add to active alerts
        manager._active_alerts["key1"] = alert1
        manager._active_alerts["key2"] = alert2
        
        # Test organization filtering
        org_123_alerts = manager.get_active_alerts(organization_id="org-123")
        assert len(org_123_alerts) == 1
        assert org_123_alerts[0].organization_id == "org-123"
        
        # Test severity filtering
        critical_alerts = manager.get_active_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].severity == AlertSeverity.CRITICAL
    
    def test_acknowledge_alert(self):
        """Test acknowledging alerts"""
        manager = AlertManager()
        
        # Create test alert
        alert = Alert(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            organization_id="org-123"
        )
        
        alert_key = "test_key"
        manager._active_alerts[alert_key] = alert
        
        # Acknowledge alert
        success = manager.acknowledge_alert(alert_key)
        assert success is True
        assert alert.metadata.get('acknowledged') is True
        
        # Try to acknowledge non-existent alert
        success = manager.acknowledge_alert("non_existent")
        assert success is False


class TestAlertHandlers:
    """Test alert handlers"""
    
    def test_log_alert_handler(self):
        """Test log-based alert handler"""
        alert = Alert(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            organization_id="org-123"
        )
        
        with patch('backend.monitoring.alerting.logger') as mock_logger:
            log_alert_handler(alert)
            mock_logger.log.assert_called_once()
    
    def test_console_alert_handler(self):
        """Test console alert handler"""
        alert = Alert(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            organization_id="org-123"
        )
        
        with patch('builtins.print') as mock_print:
            console_alert_handler(alert)
            assert mock_print.call_count > 0


class TestMetricsCollector:
    """Test MetricsCollector functionality"""
    
    def test_collector_initialization(self):
        """Test metrics collector initialization"""
        collector = MetricsCollector()
        
        assert not collector._running
        assert collector._collection_interval == 300
        assert collector._metrics_cache == {}
    
    def test_record_error(self):
        """Test recording errors"""
        collector = MetricsCollector()
        
        collector.record_error("cleverbrag", "ConnectionError")
        
        # Verify error was recorded
        key = "cleverbrag_ConnectionError"
        assert key in collector._error_counts
        assert len(collector._error_counts[key]) == 1
    
    def test_record_response_time(self):
        """Test recording response times"""
        collector = MetricsCollector()
        
        collector.record_response_time("cleverbrag", 1.5)
        
        # Verify response time was recorded
        key = "cleverbrag_response_time"
        assert key in collector._response_times
        assert len(collector._response_times[key]) == 1
        assert collector._response_times[key][0][1] == 1.5
    
    def test_get_error_rate(self):
        """Test calculating error rates"""
        collector = MetricsCollector()
        
        # Record some errors
        collector.record_error("cleverbrag", "error")
        collector.record_error("cleverbrag", "error")
        
        error_rate = collector.get_error_rate("cleverbrag", minutes=60)
        assert error_rate == 2
        
        # Test non-existent destination
        error_rate = collector.get_error_rate("nonexistent", minutes=60)
        assert error_rate == 0.0


class TestAlertResponse:
    """Test AlertResponse Pydantic model"""
    
    def test_from_alert_conversion(self):
        """Test converting Alert to AlertResponse"""
        alert = Alert(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            organization_id="org-123",
            destination_name="cleverbrag",
            cc_pair_id="cc-456"
        )
        
        response = AlertResponse.from_alert(alert)
        
        assert response.alert_type == alert.alert_type
        assert response.severity == alert.severity
        assert response.title == alert.title
        assert response.message == alert.message
        assert response.organization_id == alert.organization_id
        assert response.destination_name == alert.destination_name
        assert response.cc_pair_id == alert.cc_pair_id
        assert response.resolved == alert.resolved
        assert response.acknowledged is False
    
    def test_from_alert_with_acknowledgment(self):
        """Test converting acknowledged alert"""
        alert = Alert(
            alert_type=AlertType.DESTINATION_DOWN,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            organization_id="org-123",
            metadata={"acknowledged": True}
        )
        
        response = AlertResponse.from_alert(alert)
        assert response.acknowledged is True


class TestAlertEnums:
    """Test alert enum types"""
    
    def test_alert_severity_enum(self):
        """Test AlertSeverity enum values"""
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.INFO == "info"
    
    def test_alert_type_enum(self):
        """Test AlertType enum values"""
        assert AlertType.DESTINATION_DOWN == "destination_down"
        assert AlertType.DESTINATION_DEGRADED == "destination_degraded"
        assert AlertType.CC_PAIR_SYNC_FAILED == "cc_pair_sync_failed"
        assert AlertType.CC_PAIR_SYNC_SLOW == "cc_pair_sync_slow"
        assert AlertType.HIGH_ERROR_RATE == "high_error_rate"
        assert AlertType.RATE_LIMIT_EXCEEDED == "rate_limit_exceeded"
        assert AlertType.HEALTH_CHECK_FAILED == "health_check_failed"
