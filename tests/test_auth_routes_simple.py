"""
Simple unit tests for authentication routes
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from backend.routes.auth import signup, login, me, refresh, logout, _provider
from backend.auth.interfaces import TokenPair
from backend.auth.schemas import SignupRequest, LoginRequest, RefreshRequest, LogoutRequest
from backend.db.models import User
from backend.settings import get_settings


class TestAuthRouteFunctions:
    """Test auth route functions directly"""
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock auth provider"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4()
        )
    
    @pytest.fixture
    def valid_token_pair(self):
        """Create valid token pair"""
        return TokenPair(
            access_token="access_token_123",
            refresh_token="refresh_token_456"
        )


class TestSignupFunction:
    """Test signup route function"""
    
    @pytest.mark.asyncio
    async def test_signup_success(self):
        """Test successful signup"""
        mock_provider = AsyncMock()
        mock_provider.signup.return_value = None
        mock_provider.login.return_value = TokenPair(
            access_token="access_123",
            refresh_token="refresh_456"
        )
        
        request = SignupRequest(
            email="test@example.com",
            password="password123",
            organization="TestOrg"
        )
        
        result = await signup(request, mock_provider)
        
        assert result.access_token == "access_123"
        assert result.refresh_token == "refresh_456"
        
        mock_provider.signup.assert_called_once_with("test@example.com", "password123", "TestOrg")
        mock_provider.login.assert_called_once_with("test@example.com", "password123")
    
    @pytest.mark.asyncio
    async def test_signup_user_already_exists(self):
        """Test signup when user already exists"""
        mock_provider = AsyncMock()
        mock_provider.signup.side_effect = ValueError("User already exists")
        
        request = SignupRequest(
            email="existing@example.com",
            password="password123",
            organization="TestOrg"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await signup(request, mock_provider)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "User already exists" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_signup_login_fails_after_signup(self):
        """Test when signup succeeds but login fails"""
        mock_provider = AsyncMock()
        mock_provider.signup.return_value = None
        mock_provider.login.side_effect = ValueError("Login failed")
        
        request = SignupRequest(
            email="test@example.com",
            password="password123",
            organization="TestOrg"
        )
        
        with pytest.raises(ValueError):
            await signup(request, mock_provider)


class TestLoginFunction:
    """Test login route function"""
    
    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login"""
        mock_provider = AsyncMock()
        mock_provider.login.return_value = TokenPair(
            access_token="access_789",
            refresh_token="refresh_012"
        )
        
        request = LoginRequest(
            email="test@example.com",
            password="password123"
        )
        
        result = await login(request, mock_provider)
        
        assert result.access_token == "access_789"
        assert result.refresh_token == "refresh_012"
        
        mock_provider.login.assert_called_once_with("test@example.com", "password123")
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        mock_provider = AsyncMock()
        mock_provider.login.side_effect = ValueError("Invalid credentials")
        
        request = LoginRequest(
            email="test@example.com",
            password="wrongpassword"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await login(request, mock_provider)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in str(exc_info.value.detail)


class TestMeFunction:
    """Test me route function"""
    
    @pytest.fixture
    def mock_user(self):
        return User(
            id=uuid.uuid4(),
            email="test@example.com",
            organization_id=uuid.uuid4()
        )
    
    @pytest.mark.asyncio
    async def test_me_success(self, mock_user):
        """Test successful /me request"""
        settings = get_settings()
        from jose import jwt
        
        # Create valid token
        payload = {
            "sub": "test@example.com",
            "exp": 9999999999
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        authorization = f"Bearer {token}"
        
        # Mock database
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        result = await me(authorization, mock_db)
        
        assert result.user_id == str(mock_user.id)
        assert result.organization_id == str(mock_user.organization_id)
        assert result.email == "test@example.com"
        assert result.access_token == token
        assert result.refresh_token == ""
    
    @pytest.mark.asyncio
    async def test_me_missing_authorization(self):
        """Test /me without authorization header"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me(None, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_me_invalid_bearer_format(self):
        """Test /me with invalid bearer format"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me("InvalidFormat", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_me_invalid_token(self):
        """Test /me with invalid JWT token"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me("Bearer invalid_token", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_me_token_missing_subject(self):
        """Test /me with token missing subject"""
        settings = get_settings()
        from jose import jwt
        
        # Create token without subject
        payload = {
            "exp": 9999999999
            # Missing 'sub'
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        authorization = f"Bearer {token}"
        
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me(authorization, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token missing subject" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_me_user_not_found(self):
        """Test /me when user doesn't exist in database"""
        settings = get_settings()
        from jose import jwt
        
        # Create valid token
        payload = {
            "sub": "nonexistent@example.com",
            "exp": 9999999999
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        authorization = f"Bearer {token}"
        
        # Mock database query returning None
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await me(authorization, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_me_expired_token(self):
        """Test /me with expired token"""
        settings = get_settings()
        from jose import jwt
        
        # Create expired token
        payload = {
            "sub": "test@example.com",
            "exp": 1  # Expired
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        authorization = f"Bearer {token}"
        
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me(authorization, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_me_case_insensitive_bearer(self, mock_user):
        """Test that bearer token detection is case insensitive"""
        settings = get_settings()
        from jose import jwt
        
        payload = {
            "sub": "test@example.com",
            "exp": 9999999999
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        # Mock database
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test different cases
        for bearer_prefix in ["bearer", "Bearer", "BEARER", "BeArEr"]:
            authorization = f"{bearer_prefix} {token}"
            result = await me(authorization, mock_db)
            assert result.email == "test@example.com"


class TestRefreshFunction:
    """Test refresh route function"""
    
    @pytest.mark.asyncio
    async def test_refresh_success(self):
        """Test successful token refresh"""
        mock_provider = AsyncMock()
        mock_provider.refresh.return_value = TokenPair(
            access_token="new_access_123",
            refresh_token="new_refresh_456"
        )
        
        request = RefreshRequest(refresh_token="old_refresh_token")
        
        result = await refresh(request, mock_provider)
        
        assert result.access_token == "new_access_123"
        assert result.refresh_token == "new_refresh_456"
        
        mock_provider.refresh.assert_called_once_with("old_refresh_token")
    
    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self):
        """Test refresh with invalid token"""
        mock_provider = AsyncMock()
        mock_provider.refresh.side_effect = ValueError("Invalid refresh token")
        
        request = RefreshRequest(refresh_token="invalid_token")
        
        with pytest.raises(HTTPException) as exc_info:
            await refresh(request, mock_provider)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid refresh token" in str(exc_info.value.detail)


class TestLogoutFunction:
    """Test logout route function"""
    
    @pytest.mark.asyncio
    async def test_logout_success(self):
        """Test successful logout"""
        mock_provider = AsyncMock()
        mock_provider.revoke.return_value = None
        
        request = LogoutRequest(refresh_token="token_to_revoke")
        
        result = await logout(request, mock_provider)
        
        # Logout returns None (empty response body for 204)
        assert result is None
        
        mock_provider.revoke.assert_called_once_with("token_to_revoke")
    
    @pytest.mark.asyncio
    async def test_logout_provider_error(self):
        """Test logout when provider raises error"""
        mock_provider = AsyncMock()
        mock_provider.revoke.side_effect = Exception("Revoke failed")
        
        request = LogoutRequest(refresh_token="token_to_revoke")
        
        # If provider raises exception, it should propagate
        with pytest.raises(Exception, match="Revoke failed"):
            await logout(request, mock_provider)


class TestProviderDependency:
    """Test the _provider dependency function"""
    
    @pytest.mark.asyncio
    async def test_provider_dependency(self):
        """Test that _provider returns auth provider"""
        mock_db = AsyncMock()
        
        with patch('backend.routes.auth.get_auth_provider') as mock_get_provider:
            mock_provider = AsyncMock()
            mock_get_provider.return_value = mock_provider
            
            result = await _provider(mock_db)
            
            assert result == mock_provider
            mock_get_provider.assert_called_once_with(mock_db)


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_authorization_header(self):
        """Test with empty authorization header"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me("", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_bearer_only_authorization(self):
        """Test with just 'Bearer' and no token"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me("Bearer", mock_db)
        
        # This should raise missing bearer token since there's no space
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing bearer token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_malformed_jwt_token(self):
        """Test with malformed JWT token"""
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me("Bearer not.a.jwt", mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_wrong_algorithm_token(self):
        """Test JWT token signed with wrong algorithm"""
        settings = get_settings()
        from jose import jwt
        
        # Create token with different algorithm
        payload = {"sub": "test@example.com", "exp": 9999999999}
        wrong_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS512")  # Wrong algorithm
        authorization = f"Bearer {wrong_token}"
        
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await me(authorization, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token" in str(exc_info.value.detail)
