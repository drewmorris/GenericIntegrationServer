"""
Tests for CC-Pair database models and operations
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import models as m
from backend.db import cc_pairs as cc_pair_ops
from backend.schemas.cc_pairs import (
    ConnectorCreate, ConnectorUpdate,
    ConnectorCredentialPairCreate, ConnectorCredentialPairUpdate,
    IndexAttemptCreate, IndexAttemptUpdate
)


class TestConnectorModel:
    """Test Connector model functionality"""
    
    def test_connector_creation(self):
        """Test creating a Connector instance"""
        now = datetime.utcnow()
        connector = m.Connector(
            name="Test Slack Connector",
            source="slack",
            input_type="POLL",
            connector_specific_config={"workspace": "test"},
            refresh_freq=3600,
            prune_freq=86400,
            time_created=now,
            time_updated=now
        )
        
        assert connector.name == "Test Slack Connector"
        assert connector.source == "slack"
        assert connector.input_type == "POLL"
        assert connector.connector_specific_config == {"workspace": "test"}
        assert connector.refresh_freq == 3600
        assert connector.prune_freq == 86400
        assert isinstance(connector.time_created, datetime)
        assert isinstance(connector.time_updated, datetime)


class TestConnectorCredentialPairModel:
    """Test ConnectorCredentialPair model functionality"""
    
    def test_cc_pair_creation(self):
        """Test creating a CC-Pair instance"""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        cred_id = uuid.uuid4()
        now = datetime.utcnow()
        
        cc_pair = m.ConnectorCredentialPair(
            name="Test CC-Pair",
            connector_id=1,
            credential_id=cred_id,
            organization_id=org_id,
            creator_id=user_id,
            status=m.ConnectorCredentialPairStatus.ACTIVE,
            access_type=m.AccessType.PRIVATE,
            total_docs_indexed=0,
            in_repeated_error_state=False,
            time_created=now,
            time_updated=now
        )
        
        assert cc_pair.name == "Test CC-Pair"
        assert cc_pair.connector_id == 1
        assert cc_pair.credential_id == cred_id
        assert cc_pair.organization_id == org_id
        assert cc_pair.creator_id == user_id
        assert cc_pair.status == m.ConnectorCredentialPairStatus.ACTIVE
        assert cc_pair.access_type == m.AccessType.PRIVATE
        assert cc_pair.total_docs_indexed == 0
        assert cc_pair.in_repeated_error_state is False
        assert isinstance(cc_pair.time_created, datetime)
        assert isinstance(cc_pair.time_updated, datetime)


class TestIndexAttemptModel:
    """Test IndexAttempt model functionality"""
    
    def test_index_attempt_creation(self):
        """Test creating an IndexAttempt instance"""
        now = datetime.utcnow()
        attempt = m.IndexAttempt(
            connector_credential_pair_id=1,
            status=m.IndexingStatus.IN_PROGRESS,
            from_beginning=True,
            celery_task_id="test-task-123",
            new_docs_indexed=0,
            total_docs_indexed=0,
            docs_removed_from_index=0,
            completed_batches=0,
            total_chunks=0,
            heartbeat_counter=0,
            last_heartbeat_value=0,
            cancellation_requested=False,
            time_created=now,
            time_updated=now
        )
        
        assert attempt.connector_credential_pair_id == 1
        assert attempt.status == m.IndexingStatus.IN_PROGRESS
        assert attempt.from_beginning is True
        assert attempt.celery_task_id == "test-task-123"
        assert attempt.new_docs_indexed == 0
        assert attempt.total_docs_indexed == 0
        assert attempt.docs_removed_from_index == 0
        assert attempt.completed_batches == 0
        assert attempt.total_chunks == 0
        assert attempt.heartbeat_counter == 0
        assert attempt.last_heartbeat_value == 0
        assert attempt.cancellation_requested is False
        assert isinstance(attempt.time_created, datetime)


@pytest.mark.asyncio
class TestConnectorOperations:
    """Test connector database operations"""
    
    async def test_create_connector(self):
        """Test creating a connector"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_connector = m.Connector(id=1, name="Test", source="slack", input_type="POLL")
        
        with patch('backend.db.cc_pairs.m.Connector', return_value=mock_connector):
            connector_data = ConnectorCreate(
                name="Test Connector",
                source="slack",
                input_type="POLL",
                connector_specific_config={"test": "value"}
            )
            
            result = await cc_pair_ops.create_connector(mock_db, connector_data)
            
            assert result == mock_connector
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_get_connector(self):
        """Test getting a connector by ID"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_connector = m.Connector(
            id=1, name="Test", source="slack", input_type="POLL",
            time_created=now, time_updated=now
        )
        
        # Mock the database execute result properly
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connector
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_connector(mock_db, 1)
        
        assert result == mock_connector
        mock_db.execute.assert_called_once()
    
    async def test_get_connectors(self):
        """Test getting multiple connectors"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_connectors = [
            m.Connector(id=1, name="Test1", source="slack", input_type="POLL", time_created=now, time_updated=now),
            m.Connector(id=2, name="Test2", source="gmail", input_type="LOAD_STATE", time_created=now, time_updated=now)
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_connectors
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_connectors(mock_db)
        
        assert result == mock_connectors
        mock_db.execute.assert_called_once()
    
    async def test_update_connector(self):
        """Test updating a connector"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_connector = m.Connector(id=1, name="Old Name", source="slack", input_type="POLL")
        
        with patch('backend.db.cc_pairs.get_connector', return_value=mock_connector):
            update_data = ConnectorUpdate(name="New Name")
            
            result = await cc_pair_ops.update_connector(mock_db, 1, update_data)
            
            assert result == mock_connector
            assert mock_connector.name == "New Name"
            assert isinstance(mock_connector.time_updated, datetime)
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_update_connector_not_found(self):
        """Test updating a non-existent connector"""
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.db.cc_pairs.get_connector', return_value=None):
            update_data = ConnectorUpdate(name="New Name")
            
            result = await cc_pair_ops.update_connector(mock_db, 999, update_data)
            
            assert result is None
    
    async def test_delete_connector_success(self):
        """Test deleting a connector with no CC-Pairs"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_connector = m.Connector(id=1, name="Test", source="slack", input_type="POLL", time_created=now, time_updated=now)
        
        # Mock no CC-Pairs exist - return None for the CC-Pair check query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch('backend.db.cc_pairs.get_connector', return_value=mock_connector):
            result = await cc_pair_ops.delete_connector(mock_db, 1)
            
            assert result is True
            mock_db.delete.assert_called_once_with(mock_connector)
    
    async def test_delete_connector_with_cc_pairs(self):
        """Test deleting a connector that has CC-Pairs (should fail)"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_connector = m.Connector(id=1, name="Test", source="slack", input_type="POLL", time_created=now, time_updated=now)
        mock_cc_pair = m.ConnectorCredentialPair(
            id=1, name="Test CC-Pair", connector_id=1,
            credential_id=uuid.uuid4(), organization_id=uuid.uuid4(),
            time_created=now, time_updated=now
        )
        
        # Mock CC-Pair exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_cc_pair
        mock_db.execute.return_value = mock_result
        
        with patch('backend.db.cc_pairs.get_connector', return_value=mock_connector):
            with pytest.raises(ValueError, match="Cannot delete connector with existing CC-Pairs"):
                await cc_pair_ops.delete_connector(mock_db, 1)


@pytest.mark.asyncio
class TestCCPairOperations:
    """Test CC-Pair database operations"""
    
    async def test_create_cc_pair(self):
        """Test creating a CC-Pair"""
        mock_db = AsyncMock(spec=AsyncSession)
        org_id = uuid.uuid4()
        cred_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        mock_cc_pair = m.ConnectorCredentialPair(
            id=1, name="Test CC-Pair", connector_id=1,
            credential_id=cred_id, organization_id=org_id
        )
        
        with patch('backend.db.cc_pairs.m.ConnectorCredentialPair', return_value=mock_cc_pair):
            cc_pair_data = ConnectorCredentialPairCreate(
                name="Test CC-Pair",
                connector_id=1,
                credential_id=cred_id,
                organization_id=org_id,
                creator_id=user_id
            )
            
            result = await cc_pair_ops.create_cc_pair(mock_db, cc_pair_data)
            
            assert result == mock_cc_pair
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_get_cc_pair(self):
        """Test getting a CC-Pair by ID"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_cc_pair = m.ConnectorCredentialPair(
            id=1, name="Test CC-Pair", connector_id=1,
            credential_id=uuid.uuid4(), organization_id=uuid.uuid4(),
            time_created=now, time_updated=now
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_cc_pair
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_cc_pair(mock_db, 1)
        
        assert result == mock_cc_pair
        mock_db.execute.assert_called_once()
    
    async def test_get_cc_pairs_with_filters(self):
        """Test getting CC-Pairs with various filters"""
        mock_db = AsyncMock(spec=AsyncSession)
        org_id = uuid.uuid4()
        cred_id = uuid.uuid4()
        now = datetime.utcnow()
        
        mock_cc_pairs = [
            m.ConnectorCredentialPair(
                id=1, name="Test1", organization_id=org_id, connector_id=1,
                credential_id=cred_id, time_created=now, time_updated=now
            ),
            m.ConnectorCredentialPair(
                id=2, name="Test2", organization_id=org_id, connector_id=1,
                credential_id=cred_id, time_created=now, time_updated=now
            )
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_cc_pairs
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_cc_pairs(
            mock_db,
            organization_id=org_id,
            connector_id=1,
            credential_id=cred_id,
            status=m.ConnectorCredentialPairStatus.ACTIVE,
            skip=0,
            limit=10
        )
        
        assert result == mock_cc_pairs
        mock_db.execute.assert_called_once()
    
    async def test_update_cc_pair(self):
        """Test updating a CC-Pair"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_cc_pair = m.ConnectorCredentialPair(id=1, name="Old Name")
        
        with patch('backend.db.cc_pairs.get_cc_pair', return_value=mock_cc_pair):
            update_data = ConnectorCredentialPairUpdate(name="New Name")
            
            result = await cc_pair_ops.update_cc_pair(mock_db, 1, update_data)
            
            assert result == mock_cc_pair
            assert mock_cc_pair.name == "New Name"
            assert isinstance(mock_cc_pair.time_updated, datetime)
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_delete_cc_pair(self):
        """Test deleting a CC-Pair"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_cc_pair = m.ConnectorCredentialPair(
            id=1, name="Test CC-Pair", connector_id=1,
            credential_id=uuid.uuid4(), organization_id=uuid.uuid4(),
            time_created=now, time_updated=now
        )
        
        with patch('backend.db.cc_pairs.get_cc_pair', return_value=mock_cc_pair):
            result = await cc_pair_ops.delete_cc_pair(mock_db, 1)
            
            assert result is True
            mock_db.delete.assert_called_once_with(mock_cc_pair)


@pytest.mark.asyncio
class TestIndexAttemptOperations:
    """Test IndexAttempt database operations"""
    
    async def test_create_index_attempt(self):
        """Test creating an IndexAttempt"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_attempt = m.IndexAttempt(id=1, connector_credential_pair_id=1)
        
        with patch('backend.db.cc_pairs.m.IndexAttempt', return_value=mock_attempt):
            attempt_data = IndexAttemptCreate(
                connector_credential_pair_id=1,
                from_beginning=True
            )
            
            result = await cc_pair_ops.create_index_attempt(mock_db, attempt_data)
            
            assert result == mock_attempt
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_get_index_attempt(self):
        """Test getting an IndexAttempt by ID"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_attempt = m.IndexAttempt(
            id=1, connector_credential_pair_id=1,
            time_created=now, time_updated=now
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_attempt
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_index_attempt(mock_db, 1)
        
        assert result == mock_attempt
        mock_db.execute.assert_called_once()
    
    async def test_get_index_attempts_with_filters(self):
        """Test getting IndexAttempts with filters"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_attempts = [
            m.IndexAttempt(id=1, connector_credential_pair_id=1, time_created=now, time_updated=now),
            m.IndexAttempt(id=2, connector_credential_pair_id=1, time_created=now, time_updated=now)
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_attempts
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_index_attempts(
            mock_db,
            cc_pair_id=1,
            status=m.IndexingStatus.SUCCESS,
            skip=0,
            limit=10
        )
        
        assert result == mock_attempts
        mock_db.execute.assert_called_once()
    
    async def test_update_index_attempt(self):
        """Test updating an IndexAttempt"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_attempt = m.IndexAttempt(id=1, status=m.IndexingStatus.IN_PROGRESS)
        
        with patch('backend.db.cc_pairs.get_index_attempt', return_value=mock_attempt):
            update_data = IndexAttemptUpdate(status=m.IndexingStatus.SUCCESS)
            
            result = await cc_pair_ops.update_index_attempt(mock_db, 1, update_data)
            
            assert result == mock_attempt
            assert mock_attempt.status == m.IndexingStatus.SUCCESS
            assert isinstance(mock_attempt.time_updated, datetime)
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_cancel_index_attempt_success(self):
        """Test canceling a running IndexAttempt"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_attempt = m.IndexAttempt(
            id=1, 
            status=m.IndexingStatus.IN_PROGRESS,
            cancellation_requested=False
        )
        
        with patch('backend.db.cc_pairs.get_index_attempt', return_value=mock_attempt):
            result = await cc_pair_ops.cancel_index_attempt(mock_db, 1)
            
            assert result is True
            assert mock_attempt.cancellation_requested is True
            assert mock_attempt.status == m.IndexingStatus.CANCELED
            assert isinstance(mock_attempt.time_updated, datetime)
            mock_db.flush.assert_called_once()
    
    async def test_cancel_index_attempt_already_completed(self):
        """Test canceling a completed IndexAttempt (should fail)"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_attempt = m.IndexAttempt(id=1, status=m.IndexingStatus.SUCCESS)
        
        with patch('backend.db.cc_pairs.get_index_attempt', return_value=mock_attempt):
            result = await cc_pair_ops.cancel_index_attempt(mock_db, 1)
            
            assert result is False
    
    async def test_get_latest_index_attempt(self):
        """Test getting the latest IndexAttempt for a CC-Pair"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_attempt = m.IndexAttempt(
            id=1, connector_credential_pair_id=1,
            time_created=now, time_updated=now
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_attempt
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_latest_index_attempt(mock_db, 1)
        
        assert result == mock_attempt
        mock_db.execute.assert_called_once()
    
    async def test_get_active_index_attempts(self):
        """Test getting active IndexAttempts for a CC-Pair"""
        mock_db = AsyncMock(spec=AsyncSession)
        now = datetime.utcnow()
        mock_attempts = [
            m.IndexAttempt(id=1, status=m.IndexingStatus.IN_PROGRESS, connector_credential_pair_id=1, time_created=now, time_updated=now),
            m.IndexAttempt(id=2, status=m.IndexingStatus.NOT_STARTED, connector_credential_pair_id=1, time_created=now, time_updated=now)
        ]
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_attempts
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        result = await cc_pair_ops.get_active_index_attempts(mock_db, 1)
        
        assert result == mock_attempts
        mock_db.execute.assert_called_once()
