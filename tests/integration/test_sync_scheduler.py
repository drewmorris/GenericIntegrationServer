import uuid
from datetime import datetime, timedelta


import pytest


def test_scheduler_enqueues_and_creates_sync_run(client):
    """Test that scheduler can enqueue sync runs via API."""
    # Create a profile that should be due for sync
    # Use fixed test IDs
    org_id = "12345678-1234-5678-9012-123456789012"
    user_id = "87654321-4321-8765-2109-876543210987"
    
    profile_data = {
        "organization_id": org_id,
        "user_id": user_id,
        "name": "Test GDrive",
        "source": "google_drive",
        "connector_config": {"destination": "csv"},
        "interval_minutes": 1,
        "credential_id": None,
        "status": "active"
    }
    
    response = client.post("/profiles/", json=profile_data)
    assert response.status_code == 201
    profile = response.json()
    profile_id = profile["id"]
    
    # Trigger sync via API (simulating scheduler behavior)
    sync_response = client.post(f"/profiles/{profile_id}/run")
    assert sync_response.status_code == 200
    
    # Verify profile exists and sync was attempted
    get_response = client.get(f"/profiles/{profile_id}")
    assert get_response.status_code == 200
    updated_profile = get_response.json()
    assert updated_profile["source"] == "google_drive"
    assert updated_profile["status"] == "active"
    
    # Check that sync run was created
    runs_response = client.get(f"/profiles/{profile_id}/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert len(runs) >= 1
    
    # Verify the sync run has expected properties
    sync_run = runs[0]
    assert sync_run["profile_id"] == profile_id
    assert "status" in sync_run
    assert "created_at" in sync_run