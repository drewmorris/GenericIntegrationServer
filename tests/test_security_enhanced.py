import pytest
import uuid
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from backend.security.crypto import (
    encrypt_dict, maybe_decrypt_dict, needs_key_rotation, rotate_encryption,
    generate_new_key, validate_encryption_setup, _get_current_key_version
)
from backend.security.audit import AuditLogger
from backend.db.models import Credential, CredentialAuditLog


class TestEnhancedCrypto:
    """Test enhanced encryption with key rotation."""
    
    def test_encrypt_with_version_tracking(self):
        """Test that encryption includes version and timestamp metadata."""
        test_data = {"api_key": "secret123", "user": "test"}
        
        encrypted = encrypt_dict(test_data)
        
        assert "_enc" in encrypted
        assert "_enc_version" in encrypted
        assert "_enc_timestamp" in encrypted
        assert encrypted["_enc_version"] == 1  # Default version
        
        # Verify timestamp is recent
        timestamp = datetime.fromisoformat(encrypted["_enc_timestamp"].replace("Z", "+00:00"))
        assert (datetime.utcnow() - timestamp.replace(tzinfo=None)).seconds < 5
    
    def test_decrypt_with_version_info(self):
        """Test decryption works with version metadata."""
        test_data = {"api_key": "secret123", "user": "test"}
        
        encrypted = encrypt_dict(test_data)
        decrypted = maybe_decrypt_dict(encrypted)
        
        assert decrypted == test_data
    
    def test_needs_key_rotation_by_age(self):
        """Test key rotation detection based on age."""
        # Create old encrypted data
        old_data = {
            "_enc": "fake_token",
            "_enc_version": 1,
            "_enc_timestamp": (datetime.utcnow() - timedelta(days=100)).isoformat() + "Z"
        }
        
        with patch("backend.security.crypto.KEY_ROTATION_DAYS", 90):
            assert needs_key_rotation(old_data) is True
        
        # Recent data should not need rotation
        recent_data = {
            "_enc": "fake_token",
            "_enc_version": 1,
            "_enc_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        assert needs_key_rotation(recent_data) is False
    
    def test_needs_key_rotation_by_version(self):
        """Test key rotation detection based on version."""
        old_version_data = {
            "_enc": "fake_token",
            "_enc_version": 1,
            "_enc_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        with patch("backend.security.crypto._get_current_key_version", return_value=2):
            assert needs_key_rotation(old_version_data) is True
    
    def test_generate_new_key(self):
        """Test new key generation."""
        key1 = generate_new_key()
        key2 = generate_new_key()
        
        assert len(key1) > 20  # Fernet keys are base64 encoded
        assert key1 != key2  # Should be unique
        assert isinstance(key1, str)
    
    def test_validate_encryption_setup(self):
        """Test encryption setup validation."""
        status = validate_encryption_setup()
        
        assert "valid" in status
        assert "key_count" in status
        assert "current_version" in status
        assert isinstance(status["valid"], bool)
        assert isinstance(status["key_count"], int)
    
    @patch.dict(os.environ, {
        "CREDENTIALS_SECRET_KEY": "test_key_1",
        "CREDENTIALS_SECRET_KEY_V2": "test_key_2",
        "CREDENTIALS_SECRET_KEY_V3": "test_key_3"
    })
    def test_multi_key_support(self):
        """Test support for multiple encryption keys."""
        from backend.security.crypto import _get_encryption_keys, _get_current_key_version
        
        keys = _get_encryption_keys()
        assert len(keys) == 3
        
        version = _get_current_key_version()
        assert version == 3


class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session with async methods."""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def audit_logger(self, mock_db):
        """Create audit logger with mock DB."""
        return AuditLogger(mock_db)
    
    @pytest.mark.asyncio
    async def test_log_credential_created(self, audit_logger, mock_db):
        """Test credential creation audit logging."""
        cred_id = uuid.uuid4()
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        await audit_logger.log_credential_created(
            credential_id=cred_id,
            organization_id=org_id,
            user_id=user_id,
            connector_name="google_drive",
            provider_key="oauth"
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify the audit log entry
        call_args = mock_db.add.call_args[0][0]
        assert isinstance(call_args, CredentialAuditLog)
        assert call_args.credential_id == cred_id
        assert call_args.organization_id == org_id
        assert call_args.user_id == user_id
        assert call_args.action == "created"
        assert call_args.result == "success"
        assert call_args.details["connector_name"] == "google_drive"
    
    @pytest.mark.asyncio
    async def test_log_credential_accessed(self, audit_logger, mock_db):
        """Test credential access audit logging."""
        cred_id = uuid.uuid4()
        org_id = uuid.uuid4()
        
        await audit_logger.log_credential_accessed(
            credential_id=cred_id,
            organization_id=org_id,
            result="success",
            context="connector_run"
        )
        
        call_args = mock_db.add.call_args[0][0]
        assert call_args.action == "accessed"
        assert call_args.result == "success"
        assert call_args.details["context"] == "connector_run"
    
    @pytest.mark.asyncio
    async def test_log_credential_test_failure(self, audit_logger, mock_db):
        """Test credential test failure audit logging."""
        cred_id = uuid.uuid4()
        org_id = uuid.uuid4()
        
        await audit_logger.log_credential_test(
            credential_id=cred_id,
            organization_id=org_id,
            result="failure",
            error_message="Invalid API key"
        )
        
        call_args = mock_db.add.call_args[0][0]
        assert call_args.action == "tested"
        assert call_args.result == "failure"
        assert call_args.details["error"] == "Invalid API key"
    
    @pytest.mark.asyncio
    async def test_audit_logging_resilience(self, mock_db):
        """Test that audit logging failures don't break main operations."""
        mock_db.commit.side_effect = Exception("DB error")
        
        audit_logger = AuditLogger(mock_db)
        
        # Should not raise exception
        await audit_logger.log_credential_created(
            credential_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            connector_name="test",
            provider_key="test"
        )
        
        mock_db.rollback.assert_called_once()


class TestCredentialsProvider:
    """Test enhanced credentials provider."""
    
    @pytest.fixture
    def mock_credential(self):
        """Mock credential object."""
        cred = MagicMock()
        cred.id = uuid.uuid4()
        cred.organization_id = uuid.uuid4()
        cred.user_id = uuid.uuid4()
        cred.connector_name = "google_drive"
        cred.status = "active"
        cred.refresh_attempts = 0
        cred.credential_json = encrypt_dict({"api_key": "test123"})
        return cred
    
    @pytest.fixture
    def mock_db(self, mock_credential):
        """Mock database session with async methods."""
        db = AsyncMock()
        result = AsyncMock()
        result.scalar_one.return_value = mock_credential
        db.execute.return_value = result
        return db
    
    def test_credentials_provider_initialization(self, mock_db, mock_credential):
        """Test that credentials provider initializes correctly."""
        from backend.connectors.credentials_provider import DBCredentialsProvider
        
        provider = DBCredentialsProvider(
            tenant_id="test_tenant",
            connector_name="google_drive",
            credential_id=str(mock_credential.id),
            db=mock_db
        )
        
        assert provider.get_tenant_id() == "test_tenant"
        assert provider.get_provider_key() == str(mock_credential.id)
        assert provider.is_dynamic() is True
    
    def test_static_credentials_provider(self):
        """Test static credentials provider."""
        from backend.connectors.credentials_provider import StaticCredentialsProvider
        
        test_creds = {"api_key": "static_key"}
        provider = StaticCredentialsProvider(
            tenant_id="test_tenant",
            connector_name="test_connector",
            credential_json=test_creds
        )
        
        assert provider.get_credentials() == test_creds
        assert provider.is_dynamic() is False
        
        # Test credential update
        new_creds = {"api_key": "new_key"}
        provider.set_credentials(new_creds)
        assert provider.get_credentials() == new_creds


class TestIntegration:
    """Integration tests for security features."""
    
    def test_end_to_end_encryption_flow(self):
        """Test complete encryption/decryption flow with rotation."""
        # Original data
        original = {"api_key": "secret123", "refresh_token": "refresh456"}
        
        # Encrypt
        encrypted = encrypt_dict(original)
        assert "_enc" in encrypted
        assert "_enc_version" in encrypted
        
        # Decrypt
        decrypted = maybe_decrypt_dict(encrypted)
        assert decrypted == original
        
        # Test rotation detection
        # Make it look old
        encrypted["_enc_timestamp"] = (datetime.utcnow() - timedelta(days=100)).isoformat() + "Z"
        
        with patch("backend.security.crypto.KEY_ROTATION_DAYS", 90):
            assert needs_key_rotation(encrypted) is True
        
        # Rotate
        with patch("backend.security.crypto.maybe_decrypt_dict", return_value=original):
            rotated = rotate_encryption(encrypted)
            assert rotated != encrypted  # Should be different
            assert rotated["_enc_version"] >= encrypted["_enc_version"]
    
    def test_credential_status_transitions(self):
        """Test credential status transitions during operations."""
        from backend.db.models import Credential
        
        # Create credential
        cred = Credential(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            connector_name="google_drive",
            provider_key="oauth",
            credential_json=encrypt_dict({"access_token": "token123"}),
            status="active",
            refresh_attempts=0
        )
        
        assert cred.status == "active"
        assert cred.refresh_attempts == 0
        
        # Simulate failed refresh
        cred.status = "expired"
        cred.refresh_attempts = 1
        
        assert cred.status == "expired"
        assert cred.refresh_attempts == 1
    
    def test_encryption_metadata_consistency(self):
        """Test that encryption metadata is consistent across operations."""
        test_data = {"secret": "value123"}
        
        # First encryption
        encrypted1 = encrypt_dict(test_data)
        
        # Second encryption should have different token but same version
        encrypted2 = encrypt_dict(test_data)
        
        assert encrypted1["_enc"] != encrypted2["_enc"]  # Different tokens
        assert encrypted1["_enc_version"] == encrypted2["_enc_version"]  # Same version
        
        # Both should decrypt to same data
        assert maybe_decrypt_dict(encrypted1) == test_data
        assert maybe_decrypt_dict(encrypted2) == test_data
    
    def test_non_encrypted_data_passthrough(self):
        """Test that non-encrypted data passes through unchanged."""
        plain_data = {"api_key": "plain_value"}
        
        # Should return unchanged
        result = maybe_decrypt_dict(plain_data)
        assert result == plain_data
        
        # Should not need rotation
        assert needs_key_rotation(plain_data) is False 