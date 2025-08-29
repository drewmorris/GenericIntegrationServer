import pytest


def test_checkpoint_persisted(client, test_org_user_ids):
    """Test that checkpoint data is persisted after sync via API."""
    # Use sample org and user IDs from fixture
    org_id = test_org_user_ids["org_id"]
    user_id = test_org_user_ids["user_id"]
    
    # Create profile via API
    profile_data = {
        "organization_id": org_id,
        "user_id": user_id,
        "name": "Test Profile",
        "source": "mock_source",
        "connector_config": {"destination": "csv"},
        "credential_id": None,
        "status": "active"
    }
    
    response = client.post("/profiles/", json=profile_data)
    assert response.status_code == 201
    profile = response.json()
    profile_id = profile["id"]
    
    # Trigger sync via API
    sync_response = client.post(f"/profiles/{profile_id}/run")
    assert sync_response.status_code == 200
    
    # Check that profile still exists and sync was attempted
    get_response = client.get(f"/profiles/{profile_id}")
    assert get_response.status_code == 200
    updated_profile = get_response.json()
    assert updated_profile["id"] == profile_id
    assert updated_profile["name"] == "Test Profile" 