"""
Tests for CC-Pair Pydantic schemas
"""
import pytest
import uuid
from datetime import datetime
from pydantic import ValidationError

from backend.schemas.cc_pairs import (
    ConnectorBase, ConnectorCreate, ConnectorUpdate, ConnectorOut,
    ConnectorCredentialPairBase, ConnectorCredentialPairCreate, 
    ConnectorCredentialPairUpdate, ConnectorCredentialPairOut,
    ConnectorCredentialPairWithDetails,
    IndexAttemptBase, IndexAttemptCreate, IndexAttemptUpdate, IndexAttemptOut,
    ConnectorWithCCPairs
)
from backend.db.models import (
    ConnectorCredentialPairStatus, IndexingStatus, AccessType
)


class TestConnectorSchemas:
    """Test Connector Pydantic schemas"""
    
    def test_connector_base_valid(self):
        """Test valid ConnectorBase schema"""
        data = {
            "name": "Test Slack Connector",
            "source": "slack",
            "input_type": "POLL",
            "connector_specific_config": {"workspace": "test-workspace"},
            "refresh_freq": 3600,
            "prune_freq": 86400
        }
        
        connector = ConnectorBase(**data)
        
        assert connector.name == "Test Slack Connector"
        assert connector.source == "slack"
        assert connector.input_type == "POLL"
        assert connector.connector_specific_config == {"workspace": "test-workspace"}
        assert connector.refresh_freq == 3600
        assert connector.prune_freq == 86400
    
    def test_connector_base_minimal(self):
        """Test ConnectorBase with minimal required fields"""
        data = {
            "name": "Minimal Connector",
            "source": "gmail",
            "input_type": "LOAD_STATE"
        }
        
        connector = ConnectorBase(**data)
        
        assert connector.name == "Minimal Connector"
        assert connector.source == "gmail"
        assert connector.input_type == "LOAD_STATE"
        assert connector.connector_specific_config == {}
        assert connector.refresh_freq is None
        assert connector.prune_freq is None
    
    def test_connector_create_schema(self):
        """Test ConnectorCreate schema"""
        data = {
            "name": "New Connector",
            "source": "jira",
            "input_type": "POLL",
            "connector_specific_config": {"project": "TEST"}
        }
        
        connector = ConnectorCreate(**data)
        
        assert connector.name == "New Connector"
        assert connector.source == "jira"
        assert connector.input_type == "POLL"
        assert connector.connector_specific_config == {"project": "TEST"}
    
    def test_connector_update_schema(self):
        """Test ConnectorUpdate schema"""
        data = {
            "name": "Updated Connector",
            "refresh_freq": 7200
        }
        
        connector = ConnectorUpdate(**data)
        
        assert connector.name == "Updated Connector"
        assert connector.refresh_freq == 7200


class TestConnectorCredentialPairSchemas:
    """Test ConnectorCredentialPair Pydantic schemas"""
    
    def test_cc_pair_base_valid(self):
        """Test valid ConnectorCredentialPairBase schema"""
        org_id = uuid.uuid4()
        cred_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        data = {
            "name": "Test CC-Pair",
            "connector_id": 1,
            "credential_id": cred_id,
            "organization_id": org_id,
            "creator_id": user_id,
            "status": ConnectorCredentialPairStatus.ACTIVE,
            "access_type": AccessType.PRIVATE,
            "auto_sync_options": {"frequency": "hourly"}
        }
        
        cc_pair = ConnectorCredentialPairBase(**data)
        
        assert cc_pair.name == "Test CC-Pair"
        assert cc_pair.connector_id == 1
        assert cc_pair.credential_id == cred_id
        assert cc_pair.organization_id == org_id
        assert cc_pair.creator_id == user_id
        assert cc_pair.status == ConnectorCredentialPairStatus.ACTIVE
        assert cc_pair.access_type == AccessType.PRIVATE
        assert cc_pair.auto_sync_options == {"frequency": "hourly"}
    
    def test_cc_pair_create_schema(self):
        """Test ConnectorCredentialPairCreate schema"""
        org_id = uuid.uuid4()
        cred_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        data = {
            "name": "New CC-Pair",
            "connector_id": 2,
            "credential_id": cred_id,
            "organization_id": org_id,
            "creator_id": user_id,
            "status": ConnectorCredentialPairStatus.ACTIVE
        }
        
        cc_pair = ConnectorCredentialPairCreate(**data)
        
        assert cc_pair.name == "New CC-Pair"
        assert cc_pair.connector_id == 2
        assert cc_pair.status == ConnectorCredentialPairStatus.ACTIVE


class TestIndexAttemptSchemas:
    """Test IndexAttempt Pydantic schemas"""
    
    def test_index_attempt_base_valid(self):
        """Test valid IndexAttemptBase schema"""
        data = {
            "connector_credential_pair_id": 1,
            "status": IndexingStatus.IN_PROGRESS,
            "from_beginning": True
        }
        
        attempt = IndexAttemptBase(**data)
        
        assert attempt.connector_credential_pair_id == 1
        assert attempt.status == IndexingStatus.IN_PROGRESS
        assert attempt.from_beginning is True
    
    def test_index_attempt_create_schema(self):
        """Test IndexAttemptCreate schema"""
        data = {
            "connector_credential_pair_id": 2,
            "from_beginning": False
        }
        
        attempt = IndexAttemptCreate(**data)
        
        assert attempt.connector_credential_pair_id == 2
        assert attempt.from_beginning is False
    
    def test_index_attempt_update_schema(self):
        """Test IndexAttemptUpdate schema"""
        data = {
            "status": IndexingStatus.SUCCESS,
            "new_docs_indexed": 50,
            "completed_batches": 10
        }
        
        attempt = IndexAttemptUpdate(**data)
        
        assert attempt.status == IndexingStatus.SUCCESS
        assert attempt.new_docs_indexed == 50
        assert attempt.completed_batches == 10


class TestSchemaValidation:
    """Test schema validation and error handling"""
    
    def test_connector_invalid_types(self):
        """Test connector schema with invalid types"""
        data = {
            "name": 123,  # Should be string
            "source": "slack",
            "input_type": "POLL"
        }
        
        with pytest.raises(ValidationError):
            ConnectorBase(**data)
    
    def test_cc_pair_invalid_uuid(self):
        """Test CC-Pair schema with invalid UUID"""
        data = {
            "name": "Test CC-Pair",
            "connector_id": 1,
            "credential_id": "not-a-uuid",  # Invalid UUID
            "organization_id": uuid.uuid4()
        }
        
        with pytest.raises(ValidationError):
            ConnectorCredentialPairBase(**data)
    
    def test_cc_pair_missing_required_fields(self):
        """Test CC-Pair schema with missing required fields"""
        data = {
            "name": "Test CC-Pair"
            # Missing connector_id, credential_id, organization_id
        }
        
        with pytest.raises(ValidationError):
            ConnectorCredentialPairBase(**data)


class TestSchemaDefaults:
    """Test schema default values"""
    
    def test_connector_base_defaults(self):
        """Test ConnectorBase default values"""
        data = {
            "name": "Test Connector",
            "source": "slack",
            "input_type": "POLL"
        }
        
        connector = ConnectorBase(**data)
        
        assert connector.connector_specific_config == {}
        assert connector.refresh_freq is None
        assert connector.prune_freq is None
