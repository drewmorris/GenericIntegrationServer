"""
Tests for API key database operations
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch

from backend.db.api_key import (
    get_api_key_email_pattern,
    is_api_key_email_address,
    fetch_api_keys,
    fetch_user_for_api_key,
    get_api_key_fake_email,
    insert_api_key,
    update_api_key,
    regenerate_api_key,
    remove_api_key,
    BACKEND_API_KEY_DUMMY_EMAIL_DOMAIN,
    BACKEND_API_KEY_PREFIX,
    UNNAMED_KEY_PLACEHOLDER
)
from backend.auth.api_key import ApiKeyDescriptor
from backend.auth.schemas import UserRole
from backend.db.models import ApiKey, User


class TestApiKeyUtilities:
    """Test utility functions for API keys"""
    
    def test_get_api_key_email_pattern(self):
        """Test getting API key email pattern"""
        pattern = get_api_key_email_pattern()
        assert pattern == BACKEND_API_KEY_DUMMY_EMAIL_DOMAIN
    
    def test_is_api_key_email_address_true(self):
        """Test identifying API key email addresses - positive case"""
        email = f"test{BACKEND_API_KEY_DUMMY_EMAIL_DOMAIN}"
        assert is_api_key_email_address(email) is True
    
    def test_is_api_key_email_address_false(self):
        """Test identifying API key email addresses - negative case"""
        email = "user@example.com"
        assert is_api_key_email_address(email) is False
    
    def test_get_api_key_fake_email(self):
        """Test generating fake email for API key"""
        name = "test-key"
        unique_id = "12345"
        expected = f"{BACKEND_API_KEY_PREFIX}{name}@{unique_id}{BACKEND_API_KEY_DUMMY_EMAIL_DOMAIN}"
        
        result = get_api_key_fake_email(name, unique_id)
        assert result == expected


class TestFetchApiKeys:
    """Test fetching API keys from database"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        return MagicMock()
    
    def test_fetch_api_keys_success(self, mock_db_session):
        """Test successful API key fetching"""
        # Create mock API keys with users
        user1 = User(id=uuid.uuid4(), role=UserRole.ADMIN.value)
        user2 = User(id=uuid.uuid4(), role=UserRole.BASIC.value)
        
        api_key1 = ApiKey(
            id=1,
            name="Admin Key",
            api_key_display="ak_****1234",
            user_id=user1.id,
            user=user1
        )
        api_key2 = ApiKey(
            id=2,
            name="Basic Key",
            api_key_display="ak_****5678",
            user_id=user2.id,
            user=user2
        )
        
        # Mock database query
        mock_scalars = MagicMock()
        mock_unique = MagicMock()
        mock_unique.all.return_value = [api_key1, api_key2]
        mock_scalars.unique.return_value = mock_unique
        mock_db_session.scalars.return_value = mock_scalars
        
        result = fetch_api_keys(mock_db_session)
        
        assert len(result) == 2
        assert all(isinstance(key, ApiKeyDescriptor) for key in result)
        
        # Check first key
        assert result[0].api_key_id == 1
        assert result[0].api_key_name == "Admin Key"
        assert result[0].api_key_display == "ak_****1234"
        assert result[0].api_key_role == UserRole.ADMIN
        assert result[0].user_id == user1.id
        
        # Check second key
        assert result[1].api_key_id == 2
        assert result[1].api_key_name == "Basic Key"
        assert result[1].api_key_display == "ak_****5678"
        assert result[1].api_key_role == UserRole.BASIC
        assert result[1].user_id == user2.id
    
    def test_fetch_api_keys_empty(self, mock_db_session):
        """Test fetching API keys when none exist"""
        # Mock empty result
        mock_scalars = MagicMock()
        mock_unique = MagicMock()
        mock_unique.all.return_value = []
        mock_scalars.unique.return_value = mock_unique
        mock_db_session.scalars.return_value = mock_scalars
        
        result = fetch_api_keys(mock_db_session)
        
        assert result == []


class TestFetchUserForApiKey:
    """Test fetching user for API key (async)"""
    
    @pytest.fixture
    def mock_async_db_session(self):
        """Create mock async database session"""
        return MagicMock()
    
    @pytest.mark.asyncio
    async def test_fetch_user_for_api_key_found(self, mock_async_db_session):
        """Test successful user lookup by API key hash"""
        from unittest.mock import AsyncMock
        
        mock_user = User(id=uuid.uuid4(), email="test@example.com")
        mock_async_db_session.scalar = AsyncMock(return_value=mock_user)
        
        result = await fetch_user_for_api_key("hashed_key", mock_async_db_session)
        
        assert result == mock_user
        mock_async_db_session.scalar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_user_for_api_key_not_found(self, mock_async_db_session):
        """Test user lookup when API key doesn't exist"""
        from unittest.mock import AsyncMock
        
        mock_async_db_session.scalar = AsyncMock(return_value=None)
        
        result = await fetch_user_for_api_key("invalid_hash", mock_async_db_session)
        
        assert result is None


class TestInsertApiKey:
    """Test API key insertion"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        return MagicMock()
    
    def test_insert_api_key_with_name(self, mock_db_session):
        """Test inserting API key with name"""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        api_key_args = {
            "name": "Test Key",
            "role": UserRole.ADMIN.value,
            "organization_id": org_id
        }
        
        # Mock the add method to set IDs on objects
        def mock_add(obj):
            if isinstance(obj, ApiKey):
                obj.id = 123  # Set a mock ID
            elif isinstance(obj, User):
                obj.id = user_id
        
        mock_db_session.add.side_effect = mock_add
        
        with patch('backend.db.api_key.generate_api_key', return_value="test_api_key_123"):
            with patch('backend.db.api_key.hash_api_key', return_value="hashed_key"):
                with patch('backend.db.api_key.build_displayable_api_key', return_value="ak_****123"):
                    result = insert_api_key(mock_db_session, api_key_args, user_id)
        
        assert isinstance(result, ApiKeyDescriptor)
        assert result.api_key_name == "Test Key"
        assert result.api_key_role == UserRole.ADMIN
        assert result.api_key == "test_api_key_123"
        assert result.api_key_display == "ak_****123"
        assert result.api_key_id == 123
        
        # Verify database operations
        assert mock_db_session.add.call_count == 2  # User and ApiKey
        mock_db_session.commit.assert_called_once()
    
    def test_insert_api_key_without_name(self, mock_db_session):
        """Test inserting API key without name (uses placeholder)"""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        api_key_args = {
            "role": UserRole.BASIC.value,
            "organization_id": org_id
        }
        
        # Mock the add method to set IDs on objects
        def mock_add(obj):
            if isinstance(obj, ApiKey):
                obj.id = 456  # Set a mock ID
            elif isinstance(obj, User):
                obj.id = user_id
        
        mock_db_session.add.side_effect = mock_add
        
        with patch('backend.db.api_key.generate_api_key', return_value="test_api_key_456"):
            with patch('backend.db.api_key.hash_api_key', return_value="hashed_key"):
                with patch('backend.db.api_key.build_displayable_api_key', return_value="ak_****456"):
                    result = insert_api_key(mock_db_session, api_key_args, user_id)
        
        assert isinstance(result, ApiKeyDescriptor)
        assert result.api_key_name is None
        assert result.api_key_role == UserRole.BASIC
        assert result.api_key_id == 456
        
        # Verify that unnamed placeholder was used in email generation
        mock_db_session.add.assert_called()
    
    def test_insert_api_key_default_role(self, mock_db_session):
        """Test inserting API key with default role"""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        api_key_args = {
            "name": "Default Role Key",
            "organization_id": org_id
        }
        
        # Mock the add method to set IDs on objects
        def mock_add(obj):
            if isinstance(obj, ApiKey):
                obj.id = 789  # Set a mock ID
            elif isinstance(obj, User):
                obj.id = user_id
        
        mock_db_session.add.side_effect = mock_add
        
        with patch('backend.db.api_key.generate_api_key', return_value="test_api_key_789"):
            with patch('backend.db.api_key.hash_api_key', return_value="hashed_key"):
                with patch('backend.db.api_key.build_displayable_api_key', return_value="ak_****789"):
                    result = insert_api_key(mock_db_session, api_key_args, user_id)
        
        assert result.api_key_role == UserRole.BASIC  # Default role
        assert result.api_key_id == 789


class TestUpdateApiKey:
    """Test API key updates"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        return MagicMock()
    
    def test_update_api_key_success(self, mock_db_session):
        """Test successful API key update"""
        api_key_id = 1
        user_id = uuid.uuid4()
        
        # Mock existing API key
        existing_api_key = ApiKey(
            id=api_key_id,
            name="Old Name",
            api_key_display="ak_****old",
            user_id=user_id
        )
        
        # Mock associated user
        api_key_user = User(
            id=user_id,
            email="old@example.com",
            role=UserRole.BASIC.value
        )
        
        # Mock database queries
        mock_db_session.scalar.side_effect = [existing_api_key, api_key_user]
        
        api_key_args = {
            "name": "Updated Name",
            "role": UserRole.ADMIN.value
        }
        
        result = update_api_key(mock_db_session, api_key_id, api_key_args)
        
        assert isinstance(result, ApiKeyDescriptor)
        assert result.api_key_name == "Updated Name"
        assert result.api_key_role == UserRole.ADMIN
        assert result.api_key_id == api_key_id
        assert result.user_id == user_id
        
        # Verify updates were made
        assert existing_api_key.name == "Updated Name"
        assert api_key_user.role == UserRole.ADMIN.value
        mock_db_session.commit.assert_called_once()
    
    def test_update_api_key_not_found(self, mock_db_session):
        """Test updating non-existent API key"""
        mock_db_session.scalar.return_value = None
        
        api_key_args = {"name": "New Name"}
        
        with pytest.raises(ValueError, match="API key with id 999 does not exist"):
            update_api_key(mock_db_session, 999, api_key_args)
    
    def test_update_api_key_user_not_found(self, mock_db_session):
        """Test updating API key when associated user doesn't exist"""
        api_key_id = 1
        existing_api_key = ApiKey(id=api_key_id, name="Test Key")
        
        # First call returns API key, second returns None for user
        mock_db_session.scalar.side_effect = [existing_api_key, None]
        
        api_key_args = {"name": "New Name"}
        
        with pytest.raises(RuntimeError, match="API Key does not have associated user"):
            update_api_key(mock_db_session, api_key_id, api_key_args)
    
    def test_update_api_key_without_name(self, mock_db_session):
        """Test updating API key without providing name (uses placeholder)"""
        api_key_id = 1
        user_id = uuid.uuid4()
        
        existing_api_key = ApiKey(
            id=api_key_id,
            name="Old Name",
            api_key_display="ak_****old",
            user_id=user_id
        )
        
        api_key_user = User(
            id=user_id,
            email="old@example.com",
            role=UserRole.BASIC.value
        )
        
        mock_db_session.scalar.side_effect = [existing_api_key, api_key_user]
        
        api_key_args = {"role": UserRole.ADMIN.value}  # No name provided
        
        result = update_api_key(mock_db_session, api_key_id, api_key_args)
        
        assert result.api_key_name is None
        # Email should use unnamed placeholder
        expected_email = get_api_key_fake_email(UNNAMED_KEY_PLACEHOLDER, str(user_id))
        assert api_key_user.email == expected_email


class TestRegenerateApiKey:
    """Test API key regeneration"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        return MagicMock()
    
    def test_regenerate_api_key_success(self, mock_db_session):
        """Test successful API key regeneration"""
        api_key_id = 1
        user_id = uuid.uuid4()
        
        existing_api_key = ApiKey(
            id=api_key_id,
            name="Test Key",
            hashed_api_key="old_hash",
            api_key_display="ak_****old",
            user_id=user_id
        )
        
        api_key_user = User(
            id=user_id,
            role=UserRole.ADMIN.value
        )
        
        mock_db_session.scalar.side_effect = [existing_api_key, api_key_user]
        
        with patch('backend.db.api_key.generate_api_key', return_value="new_api_key_123"):
            with patch('backend.db.api_key.hash_api_key', return_value="new_hash"):
                with patch('backend.db.api_key.build_displayable_api_key', return_value="ak_****new"):
                    result = regenerate_api_key(mock_db_session, api_key_id)
        
        assert isinstance(result, ApiKeyDescriptor)
        assert result.api_key == "new_api_key_123"
        assert result.api_key_display == "ak_****new"
        assert result.api_key_name == "Test Key"
        assert result.api_key_role == UserRole.ADMIN
        
        # Verify updates
        assert existing_api_key.hashed_api_key == "new_hash"
        assert existing_api_key.api_key_display == "ak_****new"
        mock_db_session.commit.assert_called_once()
    
    def test_regenerate_api_key_not_found(self, mock_db_session):
        """Test regenerating non-existent API key"""
        mock_db_session.scalar.return_value = None
        
        with pytest.raises(ValueError, match="API key with id 999 does not exist"):
            regenerate_api_key(mock_db_session, 999)
    
    def test_regenerate_api_key_user_not_found(self, mock_db_session):
        """Test regenerating API key when associated user doesn't exist"""
        api_key_id = 1
        existing_api_key = ApiKey(id=api_key_id, name="Test Key")
        
        # First call returns API key, second returns None for user
        mock_db_session.scalar.side_effect = [existing_api_key, None]
        
        with pytest.raises(RuntimeError, match="API Key does not have associated user"):
            regenerate_api_key(mock_db_session, api_key_id)


class TestRemoveApiKey:
    """Test API key removal"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        return MagicMock()
    
    def test_remove_api_key_success(self, mock_db_session):
        """Test successful API key removal"""
        api_key_id = 1
        user_id = uuid.uuid4()
        
        existing_api_key = ApiKey(
            id=api_key_id,
            name="Test Key",
            user_id=user_id
        )
        
        associated_user = User(
            id=user_id,
            email="api-test@example.com"
        )
        
        mock_db_session.scalar.side_effect = [existing_api_key, associated_user]
        
        # Should not raise any exception
        remove_api_key(mock_db_session, api_key_id)
        
        # Verify deletions
        mock_db_session.delete.assert_any_call(existing_api_key)
        mock_db_session.delete.assert_any_call(associated_user)
        assert mock_db_session.delete.call_count == 2
        mock_db_session.commit.assert_called_once()
    
    def test_remove_api_key_not_found(self, mock_db_session):
        """Test removing non-existent API key"""
        mock_db_session.scalar.return_value = None
        
        with pytest.raises(ValueError, match="API key with id 999 does not exist"):
            remove_api_key(mock_db_session, 999)
    
    def test_remove_api_key_user_not_found(self, mock_db_session):
        """Test removing API key when associated user doesn't exist"""
        api_key_id = 1
        existing_api_key = ApiKey(id=api_key_id, name="Test Key")
        
        # First call returns API key, second returns None for user
        mock_db_session.scalar.side_effect = [existing_api_key, None]
        
        with pytest.raises(ValueError, match="User associated with API key with id 1 does not exist"):
            remove_api_key(mock_db_session, api_key_id)
