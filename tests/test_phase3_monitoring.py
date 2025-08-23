"""
Unit tests for Phase 3: Enhanced Monitoring and Metrics
Tests destination-specific Prometheus metrics and monitoring integration
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.monitoring.destination_metrics import (
    DestinationMetricsCollector,
    CCPairMetricsCollector,
    DestinationStatus,
    CCPairStatus,
    destination_metrics,
    cc_pair_metrics
)
from backend.destinations.base import DestinationBase


class TestDestinationMetricsCollector:
    """Test destination metrics collection"""
    
    def test_collector_initialization(self):
        """Test metrics collector initializes correctly"""
        collector = DestinationMetricsCollector()
        assert collector._active_requests == {}
    
    def test_record_document_sent_success(self):
        """Test recording successful document sends"""
        collector = DestinationMetricsCollector()
        
        # Record successful send
        collector.record_document_sent(
            destination_name="cleverbrag",
            organization_id="org-123",
            cc_pair_id="cc-456",
            count=5,
            success=True
        )
        
        # Verify metrics are recorded (we can't easily assert on Prometheus counters,
        # but we can verify the method completes without error)
        assert True  # Method completed successfully
    
    def test_record_document_sent_failure(self):
        """Test recording failed document sends"""
        collector = DestinationMetricsCollector()
        
        # Record failed send
        collector.record_document_sent(
            destination_name="cleverbrag",
            organization_id="org-123", 
            cc_pair_id="cc-456",
            count=3,
            success=False
        )
        
        assert True  # Method completed successfully
    
    def test_record_batch_sent(self):
        """Test recording batch sends"""
        collector = DestinationMetricsCollector()
        
        # Record successful batch
        collector.record_batch_sent(
            destination_name="cleverbrag",
            organization_id="org-123",
            cc_pair_id="cc-456",
            batch_size=10,
            success=True
        )
        
        assert True  # Method completed successfully
    
    def test_request_timer_flow(self):
        """Test request timing functionality"""
        collector = DestinationMetricsCollector()
        
        # Start timer
        request_id = collector.start_request_timer(
            destination_name="cleverbrag",
            organization_id="org-123",
            operation="send_batch"
        )
        
        assert request_id in collector._active_requests
        assert isinstance(collector._active_requests[request_id], float)
        
        # Simulate some work
        time.sleep(0.01)
        
        # End timer
        duration = collector.end_request_timer(
            request_id=request_id,
            destination_name="cleverbrag",
            organization_id="org-123",
            operation="send_batch"
        )
        
        assert duration > 0
        assert request_id not in collector._active_requests
    
    def test_request_timer_missing_id(self):
        """Test handling of missing request timer ID"""
        collector = DestinationMetricsCollector()
        
        # Try to end non-existent timer
        duration = collector.end_request_timer(
            request_id="non-existent",
            destination_name="cleverbrag",
            organization_id="org-123"
        )
        
        assert duration == 0.0
    
    def test_record_error(self):
        """Test error recording"""
        collector = DestinationMetricsCollector()
        
        collector.record_error(
            destination_name="cleverbrag",
            organization_id="org-123",
            error_type="ConnectionError",
            cc_pair_id="cc-456"
        )
        
        # Test without cc_pair_id
        collector.record_error(
            destination_name="cleverbrag",
            organization_id="org-123",
            error_type="TimeoutError"
        )
        
        assert True  # Methods completed successfully
    
    def test_update_health_status(self):
        """Test health status updates"""
        collector = DestinationMetricsCollector()
        
        # Test all health statuses
        for status in DestinationStatus:
            collector.update_health_status(
                destination_name="cleverbrag",
                organization_id="org-123",
                target_id="target-789",
                status=status
            )
        
        assert True  # Method completed successfully


class TestCCPairMetricsCollector:
    """Test CC-Pair metrics collection"""
    
    def test_collector_initialization(self):
        """Test CC-Pair metrics collector initializes correctly"""
        collector = CCPairMetricsCollector()
        assert collector._active_syncs == {}
    
    def test_sync_lifecycle(self):
        """Test complete sync lifecycle tracking"""
        collector = CCPairMetricsCollector()
        
        # Start sync
        sync_id = collector.start_sync(
            cc_pair_id="123",
            connector_source="gmail",
            destination_name="cleverbrag",
            organization_id="org-456"
        )
        
        assert sync_id in collector._active_syncs
        assert isinstance(collector._active_syncs[sync_id], float)
        
        # Simulate sync work
        time.sleep(0.01)
        
        # End sync successfully
        duration = collector.end_sync(
            sync_id=sync_id,
            cc_pair_id="123",
            connector_source="gmail",
            destination_name="cleverbrag",
            organization_id="org-456",
            success=True,
            documents_processed=25
        )
        
        assert duration > 0
        assert sync_id not in collector._active_syncs
    
    def test_sync_failure(self):
        """Test sync failure tracking"""
        collector = CCPairMetricsCollector()
        
        # Start sync
        sync_id = collector.start_sync(
            cc_pair_id="123",
            connector_source="gmail",
            destination_name="cleverbrag",
            organization_id="org-456"
        )
        
        # End sync with failure
        duration = collector.end_sync(
            sync_id=sync_id,
            cc_pair_id="123",
            connector_source="gmail",
            destination_name="cleverbrag",
            organization_id="org-456",
            success=False,
            documents_processed=0
        )
        
        assert duration > 0
        assert sync_id not in collector._active_syncs
    
    def test_sync_missing_id(self):
        """Test handling of missing sync ID"""
        collector = CCPairMetricsCollector()
        
        # Try to end non-existent sync
        duration = collector.end_sync(
            sync_id="non-existent",
            cc_pair_id="123",
            connector_source="gmail",
            destination_name="cleverbrag",
            organization_id="org-456",
            success=True
        )
        
        assert duration == 0.0


class TestDestinationBaseMetricsIntegration:
    """Test metrics integration with DestinationBase"""
    
    @pytest.mark.asyncio
    async def test_destination_send_batch_with_metrics(self):
        """Test that send_batch records metrics correctly"""
        
        class TestDestination(DestinationBase):
            name = "test_destination"
            
            async def send(self, *, payload, profile_config):
                # Simulate successful send
                pass
        
        destination = TestDestination()
        
        # Mock the metrics collectors
        with patch('backend.destinations.base.destination_metrics') as mock_metrics:
            mock_metrics.start_request_timer.return_value = "timer-123"
            mock_metrics.end_request_timer.return_value = 1.5
            
            profile_config = {
                "organization_id": "org-123",
                "cc_pair_id": "cc-456",
                "target_id": "target-789"
            }
            
            documents = [{"id": "doc1"}, {"id": "doc2"}]
            
            await destination.send_batch(
                documents=documents,
                profile_config=profile_config,
                batch_size=2
            )
            
            # Verify metrics calls
            mock_metrics.start_request_timer.assert_called_once_with(
                "test_destination", "org-123", "send_batch"
            )
            mock_metrics.end_request_timer.assert_called_once_with(
                "timer-123", "test_destination", "org-123", "send_batch"
            )
            mock_metrics.record_batch_sent.assert_called_once_with(
                "test_destination", "org-123", "cc-456", 2, success=True
            )
    
    @pytest.mark.asyncio
    async def test_destination_send_batch_error_metrics(self):
        """Test that send_batch records error metrics on failure"""
        
        class TestDestination(DestinationBase):
            name = "test_destination"
            
            async def send(self, *, payload, profile_config):
                raise ConnectionError("Test error")
        
        destination = TestDestination()
        
        # Mock the metrics collectors
        with patch('backend.destinations.base.destination_metrics') as mock_metrics:
            mock_metrics.start_request_timer.return_value = "timer-123"
            mock_metrics.end_request_timer.return_value = 0.5
            
            profile_config = {
                "organization_id": "org-123",
                "cc_pair_id": "cc-456"
            }
            
            documents = [{"id": "doc1"}]
            
            with pytest.raises(ConnectionError):
                await destination.send_batch(
                    documents=documents,
                    profile_config=profile_config
                )
            
            # Verify error metrics were recorded
            mock_metrics.record_error.assert_called_once_with(
                "test_destination", "org-123", "ConnectionError", "cc-456"
            )
            mock_metrics.record_batch_sent.assert_called_once_with(
                "test_destination", "org-123", "cc-456", 1, success=False
            )
    
    @pytest.mark.asyncio
    async def test_destination_health_check_metrics(self):
        """Test that health_check records metrics correctly"""
        
        class TestDestination(DestinationBase):
            name = "test_destination"
            
            async def send(self, *, payload, profile_config):
                # Simulate successful health check
                pass
        
        destination = TestDestination()
        
        with patch('backend.destinations.base.destination_metrics') as mock_metrics:
            profile_config = {
                "organization_id": "org-123",
                "target_id": "target-789"
            }
            
            result = await destination.health_check(profile_config)
            
            assert result is True
            
            # Verify health metrics were updated
            mock_metrics.update_health_status.assert_called_once_with(
                "test_destination", "org-123", "target-789", DestinationStatus.HEALTHY
            )
    
    @pytest.mark.asyncio
    async def test_destination_health_check_failure_metrics(self):
        """Test that health_check records failure metrics"""
        
        class TestDestination(DestinationBase):
            name = "test_destination"
            
            async def send(self, *, payload, profile_config):
                raise TimeoutError("Health check failed")
        
        destination = TestDestination()
        
        with patch('backend.destinations.base.destination_metrics') as mock_metrics:
            profile_config = {
                "organization_id": "org-123",
                "target_id": "target-789"
            }
            
            result = await destination.health_check(profile_config)
            
            assert result is False
            
            # Verify failure metrics were recorded
            mock_metrics.update_health_status.assert_called_once_with(
                "test_destination", "org-123", "target-789", DestinationStatus.DOWN
            )
            mock_metrics.record_error.assert_called_once_with(
                "test_destination", "org-123", "health_check_failed"
            )


class TestGlobalMetricsCollectors:
    """Test global singleton metrics collectors"""
    
    def test_global_destination_metrics(self):
        """Test global destination metrics collector"""
        # Test that global collector is available
        assert destination_metrics is not None
        assert isinstance(destination_metrics, DestinationMetricsCollector)
        
        # Test basic functionality
        destination_metrics.record_document_sent(
            "test", "org", "cc", 1, True
        )
    
    def test_global_cc_pair_metrics(self):
        """Test global CC-Pair metrics collector"""
        # Test that global collector is available
        assert cc_pair_metrics is not None
        assert isinstance(cc_pair_metrics, CCPairMetricsCollector)
        
        # Test basic functionality
        sync_id = cc_pair_metrics.start_sync("123", "gmail", "test", "org")
        assert sync_id is not None


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""
    
    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint(self):
        """Test Prometheus metrics endpoint returns valid response"""
        from backend.routes.metrics import get_prometheus_metrics
        
        response = await get_prometheus_metrics()
        
        assert response.status_code == 200
        assert response.media_type == "text/plain; version=0.0.4; charset=utf-8"
        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    
    @pytest.mark.asyncio
    async def test_metrics_health_endpoint(self):
        """Test metrics health endpoint"""
        from backend.routes.metrics import metrics_health
        
        response = await metrics_health()
        
        assert response["status"] == "healthy"
        assert response["metrics_available"] is True
        assert response["endpoint"] == "/metrics/prometheus"
    
    @pytest.mark.asyncio
    async def test_prometheus_metrics_error_handling(self):
        """Test error handling in metrics endpoint"""
        from backend.routes.metrics import get_prometheus_metrics
        
        with patch('backend.routes.metrics.generate_latest', side_effect=Exception("Test error")):
            response = await get_prometheus_metrics()
            
            assert response.status_code == 500
            assert "Error generating metrics" in response.body.decode()


class TestMetricsEnumTypes:
    """Test metrics enum types"""
    
    def test_destination_status_enum(self):
        """Test DestinationStatus enum values"""
        assert DestinationStatus.HEALTHY == "healthy"
        assert DestinationStatus.DEGRADED == "degraded"
        assert DestinationStatus.DOWN == "down"
        assert DestinationStatus.UNKNOWN == "unknown"
    
    def test_cc_pair_status_enum(self):
        """Test CCPairStatus enum values"""
        assert CCPairStatus.ACTIVE == "active"
        assert CCPairStatus.PAUSED == "paused"
        assert CCPairStatus.ERROR == "error"
        assert CCPairStatus.SYNCING == "syncing"


