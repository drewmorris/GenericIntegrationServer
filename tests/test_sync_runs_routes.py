"""
Tests for sync runs routes
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from backend.routes.sync_runs import list_runs
from backend.db.models import SyncRun, ConnectorProfile


class TestSyncRunsRoutes:
    """Test sync runs route functions"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def sample_profile_id(self):
        """Sample profile ID"""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def sample_org_id(self):
        """Sample organization ID"""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def sample_sync_runs(self):
        """Sample sync runs"""
        now = datetime.now(timezone.utc)
        return [
            SyncRun(
                id=uuid.uuid4(),
                profile_id=uuid.uuid4(),
                status="completed",
                started_at=now,
                finished_at=now,
                records_synced=100
            ),
            SyncRun(
                id=uuid.uuid4(),
                profile_id=uuid.uuid4(),
                status="running",
                started_at=now,
                finished_at=None,
                records_synced=50
            ),
            SyncRun(
                id=uuid.uuid4(),
                profile_id=uuid.uuid4(),
                status="failed",
                started_at=now,
                finished_at=now,
                records_synced=0
            )
        ]
    
    @pytest.mark.asyncio
    async def test_list_runs_success(self, mock_db, sample_profile_id, sample_org_id, sample_sync_runs):
        """Test successful sync runs listing"""
        # Mock profile verification (profile exists)
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = ConnectorProfile(
            id=sample_profile_id,
            organization_id=sample_org_id
        )
        
        # Mock sync runs query
        runs_result = MagicMock()
        runs_scalars = MagicMock()
        runs_scalars.all.return_value = sample_sync_runs
        runs_result.scalars.return_value = runs_scalars
        
        # Set up mock db execute to return different results for different queries
        mock_db.execute.side_effect = [profile_result, runs_result]
        
        result = await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert len(result) == 3
        
        # Check first run (completed)
        assert result[0]["id"] == str(sample_sync_runs[0].id)
        assert result[0]["status"] == "completed"
        assert result[0]["records_synced"] == 100
        assert result[0]["started_at"] is not None
        assert result[0]["finished_at"] is not None
        
        # Check second run (running)
        assert result[1]["id"] == str(sample_sync_runs[1].id)
        assert result[1]["status"] == "running"
        assert result[1]["records_synced"] == 50
        assert result[1]["started_at"] is not None
        assert result[1]["finished_at"] is None
        
        # Check third run (failed)
        assert result[2]["id"] == str(sample_sync_runs[2].id)
        assert result[2]["status"] == "failed"
        assert result[2]["records_synced"] == 0
        assert result[2]["started_at"] is not None
        assert result[2]["finished_at"] is not None
        
        # Verify database calls
        assert mock_db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_runs_profile_not_found(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync runs listing when profile doesn't exist"""
        # Mock profile verification (profile not found)
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = profile_result
        
        with pytest.raises(HTTPException) as exc_info:
            await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert exc_info.value.status_code == 404
        assert "Profile not found" in str(exc_info.value.detail)
        
        # Should only call execute once (for profile verification)
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_runs_profile_wrong_org(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync runs listing when profile belongs to different org"""
        # Mock profile verification (profile exists but for different org)
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = None  # Query filters by org_id
        mock_db.execute.return_value = profile_result
        
        with pytest.raises(HTTPException) as exc_info:
            await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert exc_info.value.status_code == 404
        assert "Profile not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_list_runs_no_runs(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync runs listing when profile has no runs"""
        # Mock profile verification (profile exists)
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = ConnectorProfile(
            id=sample_profile_id,
            organization_id=sample_org_id
        )
        
        # Mock sync runs query (no runs)
        runs_result = MagicMock()
        runs_scalars = MagicMock()
        runs_scalars.all.return_value = []
        runs_result.scalars.return_value = runs_scalars
        
        mock_db.execute.side_effect = [profile_result, runs_result]
        
        result = await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert result == []
        assert mock_db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_runs_single_run(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync runs listing with single run"""
        now = datetime.now(timezone.utc)
        single_run = SyncRun(
            id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            status="completed",
            started_at=now,
            finished_at=now,
            records_synced=250
        )
        
        # Mock profile verification
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = ConnectorProfile(
            id=sample_profile_id,
            organization_id=sample_org_id
        )
        
        # Mock sync runs query
        runs_result = MagicMock()
        runs_scalars = MagicMock()
        runs_scalars.all.return_value = [single_run]
        runs_result.scalars.return_value = runs_scalars
        
        mock_db.execute.side_effect = [profile_result, runs_result]
        
        result = await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert len(result) == 1
        assert result[0]["id"] == str(single_run.id)
        assert result[0]["status"] == "completed"
        assert result[0]["records_synced"] == 250
        assert result[0]["started_at"] == now.isoformat()
        assert result[0]["finished_at"] == now.isoformat()
    
    @pytest.mark.asyncio
    async def test_list_runs_datetime_formatting(self, mock_db, sample_profile_id, sample_org_id):
        """Test that datetime fields are properly formatted"""
        start_time = datetime(2023, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        end_time = datetime(2023, 1, 15, 11, 45, 30, tzinfo=timezone.utc)
        
        sync_run = SyncRun(
            id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            status="completed",
            started_at=start_time,
            finished_at=end_time,
            records_synced=75
        )
        
        # Mock profile verification
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = ConnectorProfile(
            id=sample_profile_id,
            organization_id=sample_org_id
        )
        
        # Mock sync runs query
        runs_result = MagicMock()
        runs_scalars = MagicMock()
        runs_scalars.all.return_value = [sync_run]
        runs_result.scalars.return_value = runs_scalars
        
        mock_db.execute.side_effect = [profile_result, runs_result]
        
        result = await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert len(result) == 1
        assert result[0]["started_at"] == "2023-01-15T10:30:45+00:00"
        assert result[0]["finished_at"] == "2023-01-15T11:45:30+00:00"
    
    @pytest.mark.asyncio
    async def test_list_runs_null_finished_at(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync runs with null finished_at (running jobs)"""
        start_time = datetime.now(timezone.utc)
        
        sync_run = SyncRun(
            id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            status="running",
            started_at=start_time,
            finished_at=None,  # Still running
            records_synced=25
        )
        
        # Mock profile verification
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = ConnectorProfile(
            id=sample_profile_id,
            organization_id=sample_org_id
        )
        
        # Mock sync runs query
        runs_result = MagicMock()
        runs_scalars = MagicMock()
        runs_scalars.all.return_value = [sync_run]
        runs_result.scalars.return_value = runs_scalars
        
        mock_db.execute.side_effect = [profile_result, runs_result]
        
        result = await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert len(result) == 1
        assert result[0]["status"] == "running"
        assert result[0]["started_at"] is not None
        assert result[0]["finished_at"] is None
        assert result[0]["records_synced"] == 25
    
    @pytest.mark.asyncio
    async def test_list_runs_various_statuses(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync runs with various status values"""
        now = datetime.now(timezone.utc)
        
        runs = [
            SyncRun(id=uuid.uuid4(), profile_id=uuid.uuid4(), status="pending", 
                   started_at=now, finished_at=None, records_synced=0),
            SyncRun(id=uuid.uuid4(), profile_id=uuid.uuid4(), status="running", 
                   started_at=now, finished_at=None, records_synced=10),
            SyncRun(id=uuid.uuid4(), profile_id=uuid.uuid4(), status="completed", 
                   started_at=now, finished_at=now, records_synced=100),
            SyncRun(id=uuid.uuid4(), profile_id=uuid.uuid4(), status="failed", 
                   started_at=now, finished_at=now, records_synced=5),
            SyncRun(id=uuid.uuid4(), profile_id=uuid.uuid4(), status="cancelled", 
                   started_at=now, finished_at=now, records_synced=0)
        ]
        
        # Mock profile verification
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = ConnectorProfile(
            id=sample_profile_id,
            organization_id=sample_org_id
        )
        
        # Mock sync runs query
        runs_result = MagicMock()
        runs_scalars = MagicMock()
        runs_scalars.all.return_value = runs
        runs_result.scalars.return_value = runs_scalars
        
        mock_db.execute.side_effect = [profile_result, runs_result]
        
        result = await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert len(result) == 5
        statuses = [run["status"] for run in result]
        assert set(statuses) == {"pending", "running", "completed", "failed", "cancelled"}
    
    @pytest.mark.asyncio
    async def test_list_runs_return_format(self, mock_db, sample_profile_id, sample_org_id):
        """Test that the return format is correct"""
        now = datetime.now(timezone.utc)
        sync_run = SyncRun(
            id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            status="completed",
            started_at=now,
            finished_at=now,
            records_synced=42
        )
        
        # Mock profile verification
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = ConnectorProfile(
            id=sample_profile_id,
            organization_id=sample_org_id
        )
        
        # Mock sync runs query
        runs_result = MagicMock()
        runs_scalars = MagicMock()
        runs_scalars.all.return_value = [sync_run]
        runs_result.scalars.return_value = runs_scalars
        
        mock_db.execute.side_effect = [profile_result, runs_result]
        
        result = await list_runs(sample_profile_id, mock_db, sample_org_id)
        
        assert isinstance(result, list)
        assert len(result) == 1
        
        run_dict = result[0]
        assert isinstance(run_dict, dict)
        
        # Check all expected keys are present
        expected_keys = {"id", "status", "started_at", "finished_at", "records_synced"}
        assert set(run_dict.keys()) == expected_keys
        
        # Check types
        assert isinstance(run_dict["id"], str)
        assert isinstance(run_dict["status"], str)
        assert isinstance(run_dict["started_at"], str)
        assert isinstance(run_dict["records_synced"], int)
        # finished_at can be str or None
        assert run_dict["finished_at"] is None or isinstance(run_dict["finished_at"], str)
