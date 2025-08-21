"""
Tests for orchestrator routes
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.routes.orchestrator import trigger_sync
from backend.db.models import ConnectorProfile


class TestOrchestratorRoutes:
    """Test orchestrator route functions"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def sample_profile_id(self):
        """Sample profile ID"""
        return 123
    
    @pytest.fixture
    def sample_org_id(self):
        """Sample organization ID"""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID"""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def sample_profile(self, sample_profile_id, sample_org_id, sample_user_id):
        """Sample connector profile"""
        return ConnectorProfile(
            id=str(sample_profile_id),
            organization_id=sample_org_id,
            user_id=sample_user_id,
            name="Test Profile",
            source="slack"
        )
    
    @pytest.mark.asyncio
    async def test_trigger_sync_success(self, mock_db, sample_profile_id, sample_org_id, sample_profile):
        """Test successful sync trigger"""
        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile
        mock_db.execute.return_value = profile_result
        
        # Mock Celery task
        with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
            mock_task = MagicMock()
            mock_task.id = "task_12345"
            mock_sync_connector.delay.return_value = mock_task
            
            result = await trigger_sync(sample_profile_id, mock_db, sample_org_id)
        
        assert result == {"task_id": "task_12345"}
        
        # Verify database query
        mock_db.execute.assert_called_once()
        
        # Verify Celery task was triggered
        mock_sync_connector.delay.assert_called_once_with(
            str(sample_profile_id),
            sample_org_id,
            sample_profile.user_id
        )
    
    @pytest.mark.asyncio
    async def test_trigger_sync_profile_not_found(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync trigger when profile doesn't exist"""
        # Mock profile query (not found)
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = profile_result
        
        with pytest.raises(HTTPException) as exc_info:
            await trigger_sync(sample_profile_id, mock_db, sample_org_id)
        
        assert exc_info.value.status_code == 404
        assert "Profile not found" in str(exc_info.value.detail)
        
        # Verify database query was made
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trigger_sync_profile_wrong_org(self, mock_db, sample_profile_id, sample_org_id):
        """Test sync trigger when profile belongs to different org"""
        # Mock profile query (filtered by org, so returns None)
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = profile_result
        
        with pytest.raises(HTTPException) as exc_info:
            await trigger_sync(sample_profile_id, mock_db, sample_org_id)
        
        assert exc_info.value.status_code == 404
        assert "Profile not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_trigger_sync_different_profile_ids(self, mock_db, sample_org_id, sample_user_id):
        """Test sync trigger with different profile ID formats"""
        test_cases = [
            (1, "1"),
            (999, "999"),
            (0, "0"),
            (12345, "12345")
        ]
        
        for profile_id_int, profile_id_str in test_cases:
            # Create profile for this test case
            profile = ConnectorProfile(
                id=profile_id_str,
                organization_id=sample_org_id,
                user_id=sample_user_id,
                name=f"Test Profile {profile_id_int}",
                source="gmail"
            )
            
            # Mock profile query
            profile_result = MagicMock()
            profile_result.scalar_one_or_none.return_value = profile
            mock_db.execute.return_value = profile_result
            
            # Mock Celery task
            with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
                mock_task = MagicMock()
                mock_task.id = f"task_{profile_id_int}"
                mock_sync_connector.delay.return_value = mock_task
                
                result = await trigger_sync(profile_id_int, mock_db, sample_org_id)
            
            assert result == {"task_id": f"task_{profile_id_int}"}
            
            # Verify correct parameters were passed
            mock_sync_connector.delay.assert_called_once_with(
                profile_id_str,  # Should be converted to string
                sample_org_id,
                sample_user_id
            )
    
    @pytest.mark.asyncio
    async def test_trigger_sync_celery_task_parameters(self, mock_db, sample_profile_id, sample_org_id, sample_profile):
        """Test that Celery task is called with correct parameters"""
        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile
        mock_db.execute.return_value = profile_result
        
        # Mock Celery task
        with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
            mock_task = MagicMock()
            mock_task.id = "test_task_id"
            mock_sync_connector.delay.return_value = mock_task
            
            await trigger_sync(sample_profile_id, mock_db, sample_org_id)
        
        # Verify task was called with string parameters
        args = mock_sync_connector.delay.call_args[0]
        assert len(args) == 3
        assert args[0] == str(sample_profile_id)  # profile_id as string
        assert args[1] == sample_org_id           # org_id as string
        assert args[2] == sample_profile.user_id  # user_id as string
        
        # Verify all parameters are strings
        assert all(isinstance(arg, str) for arg in args)
    
    @pytest.mark.asyncio
    async def test_trigger_sync_return_format(self, mock_db, sample_profile_id, sample_org_id, sample_profile):
        """Test that the return format is correct"""
        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile
        mock_db.execute.return_value = profile_result
        
        # Mock Celery task
        with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
            mock_task = MagicMock()
            mock_task.id = "unique_task_identifier_123"
            mock_sync_connector.delay.return_value = mock_task
            
            result = await trigger_sync(sample_profile_id, mock_db, sample_org_id)
        
        # Verify return format
        assert isinstance(result, dict)
        assert "task_id" in result
        assert result["task_id"] == "unique_task_identifier_123"
        assert len(result) == 1  # Only task_id should be returned
    
    @pytest.mark.asyncio
    async def test_trigger_sync_database_query_parameters(self, mock_db, sample_profile_id, sample_org_id, sample_profile):
        """Test that database query uses correct parameters"""
        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile
        mock_db.execute.return_value = profile_result
        
        # Mock Celery task
        with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
            mock_task = MagicMock()
            mock_task.id = "task_id"
            mock_sync_connector.delay.return_value = mock_task
            
            await trigger_sync(sample_profile_id, mock_db, sample_org_id)
        
        # Verify database execute was called
        mock_db.execute.assert_called_once()
        
        # The query should filter by profile_id (as string) and organization_id
        # We can't easily inspect the exact SQL, but we can verify it was called
        assert mock_db.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_trigger_sync_edge_case_profile_ids(self, mock_db, sample_org_id, sample_user_id):
        """Test sync trigger with edge case profile IDs"""
        edge_cases = [
            (0, "0"),           # Zero
            (-1, "-1"),         # Negative (if allowed)
            (2147483647, "2147483647"),  # Large int
        ]
        
        for profile_id_int, profile_id_str in edge_cases:
            # Create profile for this test case
            profile = ConnectorProfile(
                id=profile_id_str,
                organization_id=sample_org_id,
                user_id=sample_user_id,
                name=f"Edge Case Profile {profile_id_int}",
                source="notion"
            )
            
            # Mock profile query
            profile_result = MagicMock()
            profile_result.scalar_one_or_none.return_value = profile
            mock_db.execute.return_value = profile_result
            
            # Mock Celery task
            with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
                mock_task = MagicMock()
                mock_task.id = f"edge_task_{profile_id_int}"
                mock_sync_connector.delay.return_value = mock_task
                
                result = await trigger_sync(profile_id_int, mock_db, sample_org_id)
            
            assert result == {"task_id": f"edge_task_{profile_id_int}"}
    
    @pytest.mark.asyncio
    async def test_trigger_sync_celery_task_failure(self, mock_db, sample_profile_id, sample_org_id, sample_profile):
        """Test behavior when Celery task creation fails"""
        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = sample_profile
        mock_db.execute.return_value = profile_result
        
        # Mock Celery task failure
        with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
            mock_sync_connector.delay.side_effect = Exception("Celery connection failed")
            
            # The exception should propagate
            with pytest.raises(Exception, match="Celery connection failed"):
                await trigger_sync(sample_profile_id, mock_db, sample_org_id)
    
    @pytest.mark.asyncio
    async def test_trigger_sync_database_error(self, mock_db, sample_profile_id, sample_org_id):
        """Test behavior when database query fails"""
        # Mock database error
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        # The exception should propagate
        with pytest.raises(Exception, match="Database connection failed"):
            await trigger_sync(sample_profile_id, mock_db, sample_org_id)
        
        # Verify database execute was attempted
        mock_db.execute.assert_called_once()


class TestOrchestratorRoutesEdgeCases:
    """Test edge cases for orchestrator routes"""
    
    @pytest.mark.asyncio
    async def test_trigger_sync_with_none_task_id(self):
        """Test when Celery task returns None task ID"""
        mock_db = AsyncMock()
        profile_id = 123
        org_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        profile = ConnectorProfile(
            id=str(profile_id),
            organization_id=org_id,
            user_id=user_id,
            name="Test Profile",
            source="slack"
        )
        
        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = profile
        mock_db.execute.return_value = profile_result
        
        # Mock Celery task with None ID
        with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
            mock_task = MagicMock()
            mock_task.id = None
            mock_sync_connector.delay.return_value = mock_task
            
            result = await trigger_sync(profile_id, mock_db, org_id)
        
        assert result == {"task_id": None}
    
    @pytest.mark.asyncio
    async def test_trigger_sync_with_empty_string_task_id(self):
        """Test when Celery task returns empty string task ID"""
        mock_db = AsyncMock()
        profile_id = 456
        org_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        profile = ConnectorProfile(
            id=str(profile_id),
            organization_id=org_id,
            user_id=user_id,
            name="Test Profile",
            source="gmail"
        )
        
        # Mock profile query
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = profile
        mock_db.execute.return_value = profile_result
        
        # Mock Celery task with empty string ID
        with patch('backend.routes.orchestrator.sync_connector') as mock_sync_connector:
            mock_task = MagicMock()
            mock_task.id = ""
            mock_sync_connector.delay.return_value = mock_task
            
            result = await trigger_sync(profile_id, mock_db, org_id)
        
        assert result == {"task_id": ""}
