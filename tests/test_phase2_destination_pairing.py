"""
Unit tests for Phase 2: Enhanced Destination Connectors with 1:1 source-destination pairing
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.db import models as m
from backend.schemas.cc_pairs import ConnectorCredentialPairCreate
from backend.db.cc_pairs import create_cc_pair
from backend.destinations.base import DestinationBase
from backend.destinations.cleverbrag import CleverBragDestination
from backend.orchestrator.cc_pair_tasks import _send_to_destinations


class TestDestinationPairing:
    """Test 1:1 source-destination pairing functionality"""
    
    @pytest.mark.asyncio
    async def test_cc_pair_with_destination_creation(self):
        """Test creating CC-Pair with destination target"""
        mock_db = AsyncMock()
        
        # Mock destination target ID
        destination_id = uuid.uuid4()
        
        cc_pair_data = ConnectorCredentialPairCreate(
            name="Gmail to CleverBrag",
            connector_id=1,
            credential_id=uuid.uuid4(),
            destination_target_id=destination_id,
            organization_id=uuid.uuid4(),
            creator_id=uuid.uuid4(),
        )
        
        # Mock the created CC-Pair object
        mock_cc_pair = MagicMock(spec=m.ConnectorCredentialPair)
        mock_cc_pair.destination_target_id = destination_id
        
        # Mock database operations to return our mock object
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test CC-Pair creation with destination
        with patch('backend.db.cc_pairs.m.ConnectorCredentialPair', return_value=mock_cc_pair):
            await create_cc_pair(mock_db, cc_pair_data)
        
        # Verify destination is properly linked
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_to_specific_destination(self):
        """Test sending documents to CC-Pair's specific destination"""
        mock_session = AsyncMock()
        
        # Mock CC-Pair with destination
        destination_id = uuid.uuid4()
        cc_pair = MagicMock(spec=m.ConnectorCredentialPair)
        cc_pair.id = 1
        cc_pair.destination_target_id = destination_id
        cc_pair.organization_id = uuid.uuid4()
        
        # Mock destination target
        mock_target = MagicMock(spec=m.DestinationTarget)
        mock_target.id = destination_id
        mock_target.name = "cleverbrag"
        mock_target.config = {"cleverbrag": {"api_key": "test-key"}}
        
        # Mock database query for destination target
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_target
        mock_session.execute.return_value = mock_result
        
        # Mock destination class
        mock_destination = AsyncMock()
        
        with patch('backend.destinations.get_destination') as mock_get_dest:
            mock_get_dest.return_value = lambda: mock_destination
            
            # Test sending documents
            docs = [{"id": "doc1", "content": "test"}]
            await _send_to_destinations(mock_session, cc_pair, docs)
            
            # Verify destination was called correctly (either send or send_batch)
            if mock_destination.send_batch.call_count > 0:
                mock_destination.send_batch.assert_called_once()
                call_args = mock_destination.send_batch.call_args
                assert call_args.kwargs['documents'] == docs
                assert call_args.kwargs['profile_config'] == mock_target.config
            else:
                mock_destination.send.assert_called_once()
                call_args = mock_destination.send.call_args
                assert call_args.kwargs['payload'] == docs
                assert call_args.kwargs['profile_config'] == mock_target.config
    
    @pytest.mark.asyncio
    async def test_cc_pair_without_destination(self):
        """Test CC-Pair without destination configured"""
        mock_session = AsyncMock()
        
        # Mock CC-Pair without destination
        cc_pair = MagicMock(spec=m.ConnectorCredentialPair)
        cc_pair.id = 1
        cc_pair.destination_target_id = None
        
        # Test sending documents (should log warning and return)
        docs = [{"id": "doc1", "content": "test"}]
        
        with patch('backend.orchestrator.cc_pair_tasks.logger') as mock_logger:
            await _send_to_destinations(mock_session, cc_pair, docs)
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once_with(
                "No destination target configured for CC-Pair %s", cc_pair.id
            )
            
            # Verify no database queries were made
            mock_session.execute.assert_not_called()


class TestEnhancedDestinationBase:
    """Test enhanced destination base class functionality"""
    
    def test_destination_initialization(self):
        """Test destination initialization with health tracking"""
        
        class TestDestination(DestinationBase):
            name = "test"
            
            async def send(self, *, payload, profile_config):
                pass
        
        dest = TestDestination()
        
        # Verify initial health state
        assert dest._health_status is True
        assert dest._error_count == 0
        assert dest._last_health_check is None
        assert dest._last_error_time is None
    
    @pytest.mark.asyncio
    async def test_batch_processing_success(self):
        """Test successful batch processing"""
        
        class TestDestination(DestinationBase):
            name = "test"
            
            def __init__(self):
                super().__init__()
                self.send_calls = []
            
            async def send(self, *, payload, profile_config):
                self.send_calls.append(list(payload))
        
        dest = TestDestination()
        
        # Test batch processing
        docs = [{"id": f"doc{i}"} for i in range(5)]
        config = {"test": "config"}
        
        await dest.send_batch(documents=docs, profile_config=config, batch_size=2)
        
        # Verify batching worked correctly
        assert len(dest.send_calls) == 3  # 5 docs / 2 batch_size = 3 batches
        assert len(dest.send_calls[0]) == 2  # First batch: 2 docs
        assert len(dest.send_calls[1]) == 2  # Second batch: 2 docs
        assert len(dest.send_calls[2]) == 1  # Third batch: 1 doc
        
        # Verify error count reset on success
        assert dest._error_count == 0
    
    @pytest.mark.asyncio
    async def test_batch_processing_error_tracking(self):
        """Test error tracking during batch processing"""
        
        class TestDestination(DestinationBase):
            name = "test"
            
            async def send(self, *, payload, profile_config):
                raise Exception("Test error")
        
        dest = TestDestination()
        
        # Test batch processing with errors
        docs = [{"id": "doc1"}]
        config = {"test": "config"}
        
        with pytest.raises(Exception, match="Test error"):
            await dest.send_batch(documents=docs, profile_config=config)
        
        # Verify error tracking
        assert dest._error_count == 1
        assert dest._last_error_time is not None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        
        class TestDestination(DestinationBase):
            name = "test"
            
            async def send(self, *, payload, profile_config):
                pass  # Successful send
        
        dest = TestDestination()
        config = {"test": "config"}
        
        # Test health check
        is_healthy = await dest.health_check(config)
        
        # Verify health status
        assert is_healthy is True
        assert dest._health_status is True
        assert dest._last_health_check is not None
        
        # Verify health status response
        status = dest.get_health_status()
        assert status["destination"] == "test"
        assert status["healthy"] is True
        assert status["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check"""
        
        class TestDestination(DestinationBase):
            name = "test"
            
            async def send(self, *, payload, profile_config):
                raise Exception("Health check failed")
        
        dest = TestDestination()
        config = {"test": "config"}
        
        # Test health check
        is_healthy = await dest.health_check(config)
        
        # Verify health status
        assert is_healthy is False
        assert dest._health_status is False
        assert dest._last_health_check is not None
        
        # Verify health status response
        status = dest.get_health_status()
        assert status["destination"] == "test"
        assert status["healthy"] is False


class TestCleverBragEnhancements:
    """Test CleverBrag destination enhancements"""
    
    @pytest.mark.asyncio
    async def test_cleverbrag_health_check_success(self):
        """Test CleverBrag health check with valid API"""
        dest = CleverBragDestination()
        config = {
            "cleverbrag": {
                "api_key": "test-key",
                "base_url": "https://api.test.com"
            }
        }
        
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Test health check
            is_healthy = await dest.health_check(config)
            
            # Verify health check
            assert is_healthy is True
            mock_client.get.assert_called_once_with(
                "https://api.test.com/v3/health",
                headers={"X-API-Key": "test-key"}
            )
    
    @pytest.mark.asyncio
    async def test_cleverbrag_health_check_test_mode(self):
        """Test CleverBrag health check in test mode"""
        dest = CleverBragDestination()
        config = {
            "cleverbrag": {
                "api_key": "dummy"  # Test mode
            }
        }
        
        # Test health check (should return True without HTTP call)
        is_healthy = await dest.health_check(config)
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_cleverbrag_health_check_missing_api_key(self):
        """Test CleverBrag health check with missing API key"""
        dest = CleverBragDestination()
        config = {"cleverbrag": {}}  # No API key
        
        # Test health check
        is_healthy = await dest.health_check(config)
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_cleverbrag_batch_processing(self):
        """Test CleverBrag batch processing with smaller batch size"""
        dest = CleverBragDestination()
        config = {"cleverbrag": {"api_key": "dummy"}}
        
        # Mock the parent send_batch method
        with patch.object(DestinationBase, 'send_batch') as mock_parent_batch:
            docs = [{"id": f"doc{i}"} for i in range(25)]
            
            await dest.send_batch(documents=docs, profile_config=config)
            
            # Verify parent method called with CleverBrag-specific batch size
            mock_parent_batch.assert_called_once_with(
                documents=docs,
                profile_config=config,
                batch_size=10  # CleverBrag default
            )


class TestDestinationRoutes:
    """Test enhanced destination API routes"""
    
    @pytest.mark.asyncio
    async def test_destination_health_endpoint(self):
        """Test destination health check endpoint"""
        from backend.routes.destinations import check_destination_health
        
        # Mock database and dependencies
        mock_db = AsyncMock()
        org_id = str(uuid.uuid4())
        destination_name = "cleverbrag"
        
        # Mock destination target
        mock_target = MagicMock(spec=m.DestinationTarget)
        mock_target.id = uuid.uuid4()
        mock_target.name = destination_name
        mock_target.config = {"cleverbrag": {"api_key": "test-key"}}
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_target
        mock_db.execute.return_value = mock_result
        
        # Mock destination health check
        with patch('backend.routes.destinations.get_destination') as mock_get_dest:
            mock_destination = AsyncMock()
            mock_destination.health_check.return_value = True
            mock_destination.get_health_status.return_value = {
                "destination": destination_name,
                "healthy": True,
                "error_count": 0
            }
            mock_get_dest.return_value = lambda: mock_destination
            
            # Test health check endpoint
            result = await check_destination_health(destination_name, mock_db, org_id)
            
            # Verify response
            assert result["destination_name"] == destination_name
            assert result["target_id"] == str(mock_target.id)
            assert result["healthy"] is True
            assert "status" in result
    
    @pytest.mark.asyncio
    async def test_destination_test_config_endpoint(self):
        """Test destination configuration test endpoint"""
        from backend.routes.destinations import test_destination_config
        
        destination_name = "cleverbrag"
        config = {"cleverbrag": {"api_key": "test-key"}}
        
        # Mock destination
        with patch('backend.routes.destinations.get_destination') as mock_get_dest:
            mock_destination = AsyncMock()
            mock_destination.health_check.return_value = True
            mock_destination.get_health_status.return_value = {
                "destination": destination_name,
                "healthy": True
            }
            mock_get_dest.return_value = lambda: mock_destination
            
            # Test config test endpoint
            result = await test_destination_config(destination_name, config)
            
            # Verify response
            assert result["destination_name"] == destination_name
            assert result["config_valid"] is True
            assert "status" in result
