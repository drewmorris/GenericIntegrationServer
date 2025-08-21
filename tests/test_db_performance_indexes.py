"""
Unit tests for database performance indexes and query optimization
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from backend.db.query_optimization import (
    get_cc_pairs_with_optimized_query,
    get_active_index_attempts_optimized,
    get_cc_pairs_due_for_sync_optimized,
    get_index_attempt_statistics_optimized
)
from backend.db import models as m


class TestDatabaseIndexes:
    """Test that our optimized queries work correctly"""
    
    @pytest.mark.asyncio
    async def test_get_cc_pairs_with_optimized_query(self):
        """Test optimized CC-Pair query with various filters"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        
        # Mock CC-Pair data
        mock_cc_pair = MagicMock(spec=m.ConnectorCredentialPair)
        mock_cc_pair.id = 1
        mock_cc_pair.name = "Test CC-Pair"
        mock_cc_pair.status = m.ConnectorCredentialPairStatus.ACTIVE
        
        mock_scalars.all.return_value = [mock_cc_pair]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        # Test query execution
        result = await get_cc_pairs_with_optimized_query(
            db=mock_db,
            organization_id="test-org-id",
            status=m.ConnectorCredentialPairStatus.ACTIVE,
            skip=0,
            limit=10
        )
        
        # Verify query was executed
        mock_db.execute.assert_called_once()
        assert len(result) == 1
        assert result[0].id == 1
    
    @pytest.mark.asyncio
    async def test_get_active_index_attempts_optimized(self):
        """Test optimized active index attempts query"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        
        # Mock IndexAttempt data
        mock_attempt = MagicMock(spec=m.IndexAttempt)
        mock_attempt.id = 1
        mock_attempt.status = m.IndexingStatus.IN_PROGRESS
        mock_attempt.connector_credential_pair_id = 1
        
        mock_scalars.all.return_value = [mock_attempt]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        # Test query execution
        result = await get_active_index_attempts_optimized(
            db=mock_db,
            cc_pair_id=1,
            organization_id="test-org-id"
        )
        
        # Verify query was executed
        mock_db.execute.assert_called_once()
        assert len(result) == 1
        assert result[0].status == m.IndexingStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_get_cc_pairs_due_for_sync_optimized(self):
        """Test optimized due-for-sync query"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        
        # Mock CC-Pair data
        mock_cc_pair = MagicMock(spec=m.ConnectorCredentialPair)
        mock_cc_pair.id = 1
        mock_cc_pair.status = m.ConnectorCredentialPairStatus.ACTIVE
        mock_cc_pair.last_successful_index_time = None  # Never synced
        
        mock_scalars.all.return_value = [mock_cc_pair]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result
        
        # Test query execution
        result = await get_cc_pairs_due_for_sync_optimized(
            db=mock_db,
            organization_id="test-org-id"
        )
        
        # Verify query was executed
        mock_db.execute.assert_called_once()
        assert len(result) == 1
        assert result[0].last_successful_index_time is None
    
    @pytest.mark.asyncio
    async def test_get_index_attempt_statistics_optimized(self):
        """Test optimized statistics query"""
        mock_db = AsyncMock()
        
        # Mock status count results
        mock_status_result = MagicMock()
        mock_status_row = MagicMock()
        mock_status_row.status = m.IndexingStatus.SUCCESS
        mock_status_row.count = 5
        mock_status_result.__iter__ = lambda self: iter([mock_status_row])
        
        # Mock latest attempt result
        mock_latest_result = MagicMock()
        mock_latest_attempt = MagicMock(spec=m.IndexAttempt)
        mock_latest_attempt.id = 10
        mock_latest_attempt.status = m.IndexingStatus.SUCCESS
        mock_latest_result.scalar_one_or_none.return_value = mock_latest_attempt
        
        # Configure mock to return different results for different queries
        mock_db.execute.side_effect = [mock_status_result, mock_latest_result]
        
        # Test query execution
        result = await get_index_attempt_statistics_optimized(
            db=mock_db,
            cc_pair_id=1
        )
        
        # Verify both queries were executed
        assert mock_db.execute.call_count == 2
        
        # Verify result structure
        assert 'status_counts' in result
        assert 'latest_attempt' in result
        assert 'total_attempts' in result
        assert result['status_counts'][m.IndexingStatus.SUCCESS] == 5
        assert result['latest_attempt'].id == 10
        assert result['total_attempts'] == 5


class TestIndexMigrationValidation:
    """Test that our migration indexes are properly defined"""
    
    def test_migration_file_exists(self):
        """Verify the migration file exists and is readable"""
        import os
        migration_path = "backend/db/migrations/versions/4821d79eafac_add_cc_pair_performance_indexes.py"
        assert os.path.exists(migration_path), f"Migration file not found: {migration_path}"
    
    def test_migration_has_required_indexes(self):
        """Verify the migration contains all required index definitions"""
        with open("backend/db/migrations/versions/4821d79eafac_add_cc_pair_performance_indexes.py", 'r') as f:
            content = f.read()
        
        # Check for key indexes
        required_indexes = [
            'idx_connector_source',
            'idx_connector_time_created',
            'idx_cc_pair_connector_id',
            'idx_cc_pair_organization_id',
            'idx_cc_pair_status',
            'idx_cc_pair_time_created',
            'idx_cc_pair_status_org_time',
            'idx_index_attempt_cc_pair_id',
            'idx_index_attempt_status',
            'idx_index_attempt_time_created',
            'idx_index_attempt_cc_pair_time',
            'idx_index_attempt_celery_task_id',
            'idx_index_attempt_status_cc_pair'
        ]
        
        for index_name in required_indexes:
            assert index_name in content, f"Required index {index_name} not found in migration"
        
        # Check for proper if_not_exists usage (idempotent migrations)
        assert 'if_not_exists=True' in content, "Migration should use if_not_exists=True for idempotency"
        assert 'if_exists=True' in content, "Migration should use if_exists=True for downgrade idempotency"
