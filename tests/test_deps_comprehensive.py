"""
Comprehensive tests for FastAPI dependencies
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from jose import jwt

from backend.deps import (
    get_current_user,
    get_current_user_id,
    get_current_org_id,
    get_current_user_or_api_key
)
from backend.db.models import User
from backend.settings import get_settings


class TestGetCurrentUser:
    """Test get_current_user dependency"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token"""
        settings = get_settings()
        payload = {
            "sub": "test@example.com",
            "exp": 9999999999  # Far future
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4()
        )
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_db, valid_token, mock_user):
        """Test successful user authentication"""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        authorization = f"Bearer {valid_token}"
        result = await get_current_user(authorization, mock_db)
        
        assert result["user_id"] == str(mock_user.id)
        assert result["organization_id"] == str(mock_user.organization_id)
        assert result["email"] == mock_user.email
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_authorization(self, mock_db):
        """Test missing authorization header"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_bearer_format(self, mock_db):
        """Test invalid bearer token format"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("InvalidFormat", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_db):
        """Test invalid JWT token"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("Bearer invalid_token", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    
    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, mock_db):
        """Test expired JWT token"""
        settings = get_settings()
        payload = {
            "sub": "test@example.com",
            "exp": 1  # Expired timestamp
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(f"Bearer {expired_token}", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_token_missing_subject(self, mock_db):
        """Test JWT token without subject"""
        settings = get_settings()
        payload = {
            "exp": 9999999999  # Missing 'sub'
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(f"Bearer {token}", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token missing subject" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, mock_db, valid_token):
        """Test when user doesn't exist in database"""
        # Mock database query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(f"Bearer {valid_token}", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_case_insensitive_bearer(self, mock_db, valid_token, mock_user):
        """Test case insensitive bearer token detection"""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test with different cases
        for bearer_prefix in ["bearer", "Bearer", "BEARER", "BeArEr"]:
            authorization = f"{bearer_prefix} {valid_token}"
            result = await get_current_user(authorization, mock_db)
            assert result["email"] == mock_user.email


class TestGetCurrentUserId:
    """Test get_current_user_id dependency"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_id(self):
        """Test extracting user ID from current user"""
        user_id = str(uuid.uuid4())
        current_user = {
            "user_id": user_id,
            "organization_id": str(uuid.uuid4()),
            "email": "test@example.com"
        }
        
        result = await get_current_user_id(current_user)
        assert result == user_id


class TestGetCurrentOrgId:
    """Test get_current_org_id dependency"""
    
    @pytest.mark.asyncio
    async def test_get_current_org_id(self):
        """Test extracting organization ID from current user"""
        org_id = str(uuid.uuid4())
        current_user = {
            "user_id": str(uuid.uuid4()),
            "organization_id": org_id,
            "email": "test@example.com"
        }
        
        result = await get_current_org_id(current_user)
        assert result == org_id


class TestGetCurrentUserOrApiKey:
    """Test get_current_user_or_api_key dependency"""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request"""
        return MagicMock()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_api_user(self):
        """Create mock API user"""
        return User(
            id=uuid.uuid4(),
            email="api-key@example.com",
            organization_id=uuid.uuid4()
        )
    
    @pytest.fixture
    def mock_jwt_user(self):
        """Create mock JWT user"""
        return User(
            id=uuid.uuid4(),
            email="jwt-user@example.com",
            organization_id=uuid.uuid4()
        )
    
    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token"""
        settings = get_settings()
        payload = {
            "sub": "jwt-user@example.com",
            "exp": 9999999999
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    
    @pytest.mark.asyncio
    async def test_get_current_user_or_api_key_api_key_success(self, mock_request, mock_db, mock_api_user):
        """Test successful API key authentication"""
        with patch('backend.deps.get_hashed_api_key_from_request', return_value="hashed_api_key"):
            with patch('backend.deps.fetch_user_for_api_key', return_value=mock_api_user):
                result = await get_current_user_or_api_key(mock_request, None, mock_db)
        
        assert result["user_id"] == str(mock_api_user.id)
        assert result["organization_id"] == str(mock_api_user.organization_id)
        assert result["email"] == mock_api_user.email
    
    @pytest.mark.asyncio
    async def test_get_current_user_or_api_key_api_key_not_found(self, mock_request, mock_db, mock_jwt_user, valid_token):
        """Test API key not found, falls back to JWT"""
        # Mock database query for JWT user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_jwt_user
        mock_db.execute.return_value = mock_result
        
        with patch('backend.deps.get_hashed_api_key_from_request', return_value="hashed_api_key"):
            with patch('backend.deps.fetch_user_for_api_key', return_value=None):
                authorization = f"Bearer {valid_token}"
                result = await get_current_user_or_api_key(mock_request, authorization, mock_db)
        
        assert result["user_id"] == str(mock_jwt_user.id)
        assert result["email"] == mock_jwt_user.email
    
    @pytest.mark.asyncio
    async def test_get_current_user_or_api_key_no_api_key(self, mock_request, mock_db, mock_jwt_user, valid_token):
        """Test no API key present, uses JWT"""
        # Mock database query for JWT user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_jwt_user
        mock_db.execute.return_value = mock_result
        
        with patch('backend.deps.get_hashed_api_key_from_request', return_value=None):
            authorization = f"Bearer {valid_token}"
            result = await get_current_user_or_api_key(mock_request, authorization, mock_db)
        
        assert result["user_id"] == str(mock_jwt_user.id)
        assert result["email"] == mock_jwt_user.email
    
    @pytest.mark.asyncio
    async def test_get_current_user_or_api_key_both_fail(self, mock_request, mock_db):
        """Test when both API key and JWT authentication fail"""
        with patch('backend.deps.get_hashed_api_key_from_request', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_or_api_key(mock_request, None, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_or_api_key_api_key_invalid_jwt_fallback(self, mock_request, mock_db):
        """Test API key present but invalid, JWT also invalid"""
        with patch('backend.deps.get_hashed_api_key_from_request', return_value="invalid_hash"):
            with patch('backend.deps.fetch_user_for_api_key', return_value=None):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user_or_api_key(mock_request, "Bearer invalid_token", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in exc_info.value.detail


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_empty_authorization(self):
        """Test empty authorization string"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_bearer_only(self):
        """Test authorization with just 'Bearer' and no token"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("Bearer", mock_db)
        
        # This should raise a missing bearer token error since there's no space after Bearer
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_malformed_jwt(self):
        """Test malformed JWT token"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("Bearer not.a.jwt", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_wrong_algorithm(self):
        """Test JWT token signed with wrong algorithm"""
        mock_db = AsyncMock()
        settings = get_settings()
        
        # Create token with different algorithm
        payload = {"sub": "test@example.com", "exp": 9999999999}
        wrong_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS512")  # Wrong algorithm
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(f"Bearer {wrong_token}", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in exc_info.value.detail
