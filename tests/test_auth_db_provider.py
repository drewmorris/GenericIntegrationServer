"""
Tests for database-backed authentication provider
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from backend.auth.db_provider import DbAuthProvider, SimpleUser
from backend.auth.interfaces import TokenPair
from backend.db.models import User, Organization, UserToken


class TestSimpleUser:
    """Test SimpleUser class"""
    
    def test_simple_user_creation(self):
        """Test SimpleUser initialization"""
        user = SimpleUser("test@example.com", "hashed_password")
        
        assert user.email == "test@example.com"
        assert user.hashed_pw == "hashed_password"
        assert isinstance(user.id, uuid.UUID)


class TestDbAuthProviderInMemory:
    """Test DbAuthProvider in-memory fallback mode"""
    
    @pytest.fixture
    def provider(self):
        """Create provider without database session (in-memory mode)"""
        return DbAuthProvider(db=None)
    
    @pytest.mark.asyncio
    async def test_signup_in_memory(self, provider):
        """Test in-memory signup"""
        user = await provider.signup("test@example.com", "password123")
        
        assert isinstance(user, SimpleUser)
        assert user.email == "test@example.com"
        assert user.hashed_pw != "password123"  # Should be hashed
        assert "test@example.com" in provider._users
    
    @pytest.mark.asyncio
    async def test_signup_duplicate_user_in_memory(self, provider):
        """Test signup with duplicate email in memory"""
        await provider.signup("test@example.com", "password123")
        
        with pytest.raises(ValueError, match="User already exists"):
            await provider.signup("test@example.com", "password456")
    
    @pytest.mark.asyncio
    async def test_login_in_memory(self, provider):
        """Test in-memory login"""
        await provider.signup("test@example.com", "password123")
        
        token_pair = await provider.login("test@example.com", "password123")
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token
        assert token_pair.refresh_token
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials_in_memory(self, provider):
        """Test login with invalid credentials in memory"""
        await provider.signup("test@example.com", "password123")
        
        with pytest.raises(ValueError, match="Invalid credentials"):
            await provider.login("test@example.com", "wrongpassword")
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user_in_memory(self, provider):
        """Test login with nonexistent user in memory"""
        with pytest.raises(ValueError, match="Invalid credentials"):
            await provider.login("nonexistent@example.com", "password123")
    
    @pytest.mark.asyncio
    async def test_refresh_in_memory(self, provider):
        """Test token refresh in memory"""
        await provider.signup("test@example.com", "password123")
        token_pair = await provider.login("test@example.com", "password123")
        
        new_token_pair = await provider.refresh(token_pair.refresh_token)
        
        assert isinstance(new_token_pair, TokenPair)
        assert new_token_pair.access_token
        assert new_token_pair.refresh_token
    
    @pytest.mark.asyncio
    async def test_refresh_invalid_token_in_memory(self, provider):
        """Test refresh with invalid token in memory"""
        with pytest.raises(ValueError, match="Invalid refresh token"):
            await provider.refresh("invalid_token")
    
    @pytest.mark.asyncio
    async def test_refresh_user_not_found_in_memory(self, provider):
        """Test refresh when user no longer exists in memory"""
        await provider.signup("test@example.com", "password123")
        token_pair = await provider.login("test@example.com", "password123")
        
        # Remove user from memory
        del provider._users["test@example.com"]
        
        with pytest.raises(ValueError, match="User not found"):
            await provider.refresh(token_pair.refresh_token)
    
    @pytest.mark.asyncio
    async def test_revoke_in_memory(self, provider):
        """Test token revocation in memory (should be noop)"""
        await provider.signup("test@example.com", "password123")
        token_pair = await provider.login("test@example.com", "password123")
        
        # Should not raise any exception
        await provider.revoke(token_pair.refresh_token)


class TestDbAuthProviderDatabase:
    """Test DbAuthProvider with database session"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def provider(self, mock_db):
        """Create provider with mock database session"""
        return DbAuthProvider(db=mock_db)
    
    @pytest.mark.asyncio
    async def test_signup_db_new_org(self, provider, mock_db):
        """Test database signup with new organization"""
        # Mock organization query (not found)
        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = org_result
        
        # Mock user query (not found)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [org_result, user_result]
        
        user = await provider.signup("test@example.com", "password123", "TestOrg")
        
        assert isinstance(user, User)
        assert user.email == "test@example.com"
        assert user.hashed_pw != "password123"  # Should be hashed
        mock_db.add.assert_called()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_signup_db_existing_org(self, provider, mock_db):
        """Test database signup with existing organization"""
        org_id = uuid.uuid4()
        mock_org = Organization(id=org_id, name="TestOrg")
        
        # Mock organization query (found)
        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = mock_org
        
        # Mock user query (not found)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [org_result, user_result]
        
        user = await provider.signup("test@example.com", "password123", "TestOrg")
        
        assert isinstance(user, User)
        assert user.organization_id == org_id
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_signup_db_no_org_name_with_existing_org(self, provider, mock_db):
        """Test database signup without org name when org exists"""
        mock_org = Organization(id=uuid.uuid4(), name="DefaultOrg")
        
        # Mock organization query (found first org)
        org_result = MagicMock()
        org_scalars = MagicMock()
        org_scalars.first.return_value = mock_org
        org_result.scalars.return_value = org_scalars
        
        # Mock user query (not found)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [org_result, user_result]
        
        user = await provider.signup("test@example.com", "password123")
        
        assert isinstance(user, User)
        assert user.organization_id == mock_org.id
    
    @pytest.mark.asyncio
    async def test_signup_db_no_org_name_no_existing_org(self, provider, mock_db):
        """Test database signup without org name when no org exists"""
        # Mock organization query (no orgs found)
        org_result = MagicMock()
        org_scalars = MagicMock()
        org_scalars.first.return_value = None
        org_result.scalars.return_value = org_scalars
        
        mock_db.execute.return_value = org_result
        
        with pytest.raises(ValueError, match="No organization exists, provide org_name"):
            await provider.signup("test@example.com", "password123")
    
    @pytest.mark.asyncio
    async def test_signup_db_duplicate_user(self, provider, mock_db):
        """Test database signup with duplicate user"""
        mock_org = Organization(id=uuid.uuid4(), name="TestOrg")
        mock_user = User(id=uuid.uuid4(), email="test@example.com")
        
        # Mock organization query (found)
        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = mock_org
        
        # Mock user query (found existing user)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        
        mock_db.execute.side_effect = [org_result, user_result]
        
        with pytest.raises(ValueError, match="User already exists"):
            await provider.signup("test@example.com", "password123", "TestOrg")
    
    @pytest.mark.asyncio
    async def test_login_db_success(self, provider, mock_db):
        """Test successful database login"""
        mock_user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_pw="$2b$12$test_hashed_password"
        )
        
        # Mock user query (found)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = user_result
        
        with patch('backend.auth.db_provider.verify_password', return_value=True):
            token_pair = await provider.login("test@example.com", "password123")
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token
        assert token_pair.refresh_token
    
    @pytest.mark.asyncio
    async def test_login_db_user_not_found(self, provider, mock_db):
        """Test database login with nonexistent user"""
        # Mock user query (not found)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = user_result
        
        with pytest.raises(ValueError, match="Invalid credentials"):
            await provider.login("nonexistent@example.com", "password123")
    
    @pytest.mark.asyncio
    async def test_login_db_wrong_password(self, provider, mock_db):
        """Test database login with wrong password"""
        mock_user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_pw="$2b$12$test_hashed_password"
        )
        
        # Mock user query (found)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = user_result
        
        with patch('backend.auth.db_provider.verify_password', return_value=False):
            with pytest.raises(ValueError, match="Invalid credentials"):
                await provider.login("test@example.com", "wrongpassword")
    
    @pytest.mark.asyncio
    async def test_refresh_db_success(self, provider, mock_db):
        """Test successful token refresh with database"""
        # Create a valid refresh token
        with patch('backend.auth.db_provider.jwt.decode') as mock_decode:
            mock_decode.return_value = {"sub": "test@example.com", "jti": "test-jti"}
            
            # Mock the login call that refresh makes
            with patch.object(provider, 'login') as mock_login:
                mock_login.return_value = TokenPair(
                    access_token="new_access_token",
                    refresh_token="new_refresh_token"
                )
                
                token_pair = await provider.refresh("valid_refresh_token")
                
                assert isinstance(token_pair, TokenPair)
                mock_login.assert_called_once_with("test@example.com", "_dummy_")
    
    @pytest.mark.asyncio
    async def test_refresh_invalid_token_db(self, provider, mock_db):
        """Test refresh with invalid token in database mode"""
        with patch('backend.auth.db_provider.jwt.decode', side_effect=Exception("Invalid token")):
            with pytest.raises(ValueError, match="Invalid refresh token"):
                await provider.refresh("invalid_token")
    
    @pytest.mark.asyncio
    async def test_refresh_no_subject_db(self, provider, mock_db):
        """Test refresh with token missing subject in database mode"""
        with patch('backend.auth.db_provider.jwt.decode') as mock_decode:
            mock_decode.return_value = {"jti": "test-jti"}  # Missing 'sub'
            
            with pytest.raises(ValueError, match="Invalid refresh token payload"):
                await provider.refresh("token_without_subject")
    
    @pytest.mark.asyncio
    async def test_revoke_db_success(self, provider, mock_db):
        """Test successful token revocation with database"""
        with patch('backend.auth.db_provider.jwt.decode') as mock_decode:
            mock_decode.return_value = {"jti": "test-jti"}
            
            await provider.revoke("valid_refresh_token")
            
            mock_db.execute.assert_called_once()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_db_invalid_token(self, provider, mock_db):
        """Test token revocation with invalid token"""
        with patch('backend.auth.db_provider.jwt.decode', side_effect=Exception("Invalid token")):
            # Should not raise exception, just return silently
            await provider.revoke("invalid_token")
            
            mock_db.execute.assert_not_called()
            mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_revoke_db_no_jti(self, provider, mock_db):
        """Test token revocation with token missing jti"""
        with patch('backend.auth.db_provider.jwt.decode') as mock_decode:
            mock_decode.return_value = {"sub": "test@example.com"}  # Missing 'jti'
            
            # Should not raise exception, just return silently
            await provider.revoke("token_without_jti")
            
            mock_db.execute.assert_not_called()
            mock_db.commit.assert_not_called()


class TestTokenIssuing:
    """Test token issuing functionality"""
    
    @pytest.fixture
    def provider(self):
        """Create provider for token testing"""
        return DbAuthProvider(db=None)
    
    def test_issue_tokens_structure(self, provider):
        """Test token structure and content"""
        token_pair = provider._issue_tokens("test@example.com")
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token
        assert token_pair.refresh_token
        
        # Decode tokens to verify structure
        from jose import jwt
        from backend.settings import get_settings
        settings = get_settings()
        
        access_payload = jwt.decode(
            token_pair.access_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        refresh_payload = jwt.decode(
            token_pair.refresh_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        assert access_payload["sub"] == "test@example.com"
        assert refresh_payload["sub"] == "test@example.com"
        assert "jti" in refresh_payload
        assert "exp" in access_payload
        assert "exp" in refresh_payload
        assert "iat" in access_payload
        assert "iat" in refresh_payload
    
    @pytest.mark.asyncio
    async def test_issue_tokens_with_db_storage(self):
        """Test token issuing with database storage"""
        mock_db = AsyncMock()
        provider = DbAuthProvider(db=mock_db)
        
        # Mock the async session and user lookup
        with patch('backend.db.session.AsyncSessionLocal') as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            
            mock_user = User(id=uuid.uuid4(), email="test@example.com")
            user_result = MagicMock()
            user_result.scalar_one.return_value = mock_user
            mock_session.execute.return_value = user_result
            
            # Mock asyncio to avoid actual async execution
            with patch('asyncio.create_task') as mock_create_task:
                token_pair = provider._issue_tokens("test@example.com")
                
                assert isinstance(token_pair, TokenPair)
                # Verify that token storage task was created
                mock_create_task.assert_called_once()
