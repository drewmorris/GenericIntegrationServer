import uuid
import tempfile


def test_cleverbrag_and_csv_destinations(client):
    """Test end-to-end integration with CleverBrag and CSV destinations via API."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create profile with CleverBrag destination
        # Use fixed test IDs
        org_id = "12345678-1234-5678-9012-123456789012"
        user_id = "87654321-4321-8765-2109-876543210987"
        
        cb_profile_data = {
            "organization_id": org_id,
            "user_id": user_id,
            "name": "CB Profile",
            "source": "mock",
            "connector_config": {
                "destination": "cleverbrag",
                "cleverbrag": {"api_key": "dummy"}
            },
            "interval_minutes": 1,
            "credential_id": None,
            "status": "active"
        }
        
        # Create CleverBrag profile
        cb_response = client.post("/profiles/", json=cb_profile_data)
        assert cb_response.status_code == 201
        cb_profile = cb_response.json()
        cb_profile_id = cb_profile["id"]
        
        # Create CSV profile
        csv_profile_data = {
            "organization_id": org_id,
            "user_id": user_id,
            "name": "CSV Profile",
            "source": "mock",
            "connector_config": {
                "destination": "csvdump",
                "csvdump": {"dump_dir": tmp_dir}
            },
            "interval_minutes": 1,
            "credential_id": None,
            "status": "active"
        }
        
        csv_response = client.post("/profiles/", json=csv_profile_data)
        assert csv_response.status_code == 201
        csv_profile = csv_response.json()
        csv_profile_id = csv_profile["id"]
        
        # Trigger syncs via API
        cb_sync_response = client.post(f"/profiles/{cb_profile_id}/run")
        assert cb_sync_response.status_code == 200
        
        csv_sync_response = client.post(f"/profiles/{csv_profile_id}/run")
        assert csv_sync_response.status_code == 200
        
        # Verify profiles were created and syncs were triggered
        cb_get_response = client.get(f"/profiles/{cb_profile_id}")
        assert cb_get_response.status_code == 200
        cb_updated = cb_get_response.json()
        assert cb_updated["connector_config"]["destination"] == "cleverbrag"
        
        csv_get_response = client.get(f"/profiles/{csv_profile_id}")
        assert csv_get_response.status_code == 200
        csv_updated = csv_get_response.json()
        assert csv_updated["connector_config"]["destination"] == "csvdump"
        
        # Check sync runs were created
        cb_runs_response = client.get(f"/profiles/{cb_profile_id}/runs")
        assert cb_runs_response.status_code == 200
        cb_runs = cb_runs_response.json()
        assert len(cb_runs) >= 1
        
        csv_runs_response = client.get(f"/profiles/{csv_profile_id}/runs")
        assert csv_runs_response.status_code == 200
        csv_runs = csv_runs_response.json()
        assert len(csv_runs) >= 1