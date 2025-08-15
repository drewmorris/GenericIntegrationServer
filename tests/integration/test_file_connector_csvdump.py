import tempfile
import uuid
from pathlib import Path


def test_file_connector_to_csvdump(client):
	"""Test file connector to CSV dump integration via API."""
	with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dump_dir:
		# Create a test file to read
		test_file = Path(src_dir) / "test.txt"
		test_file.write_text("This is a test document for file connector.")
		
		# Create profile with file source and CSV dump destination
		# Use fixed test IDs
		org_id = "12345678-1234-5678-9012-123456789012"
		user_id = "87654321-4321-8765-2109-876543210987"
		
		profile_data = {
			"organization_id": org_id,
			"user_id": user_id,
			"name": "File→CSV Profile",
			"source": "file",
			"connector_config": {
				"destination": "csvdump",
				"csvdump": {"dump_dir": dump_dir},
				"file": {"path": src_dir},
			},
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
		
		# Verify profile was created with correct configuration
		get_response = client.get(f"/profiles/{profile_id}")
		assert get_response.status_code == 200
		updated_profile = get_response.json()
		assert updated_profile["source"] == "file"
		assert updated_profile["connector_config"]["destination"] == "csvdump"
		assert updated_profile["connector_config"]["file"]["path"] == src_dir
		assert updated_profile["connector_config"]["csvdump"]["dump_dir"] == dump_dir
		
		# Check that sync run was created
		runs_response = client.get(f"/profiles/{profile_id}/runs")
		assert runs_response.status_code == 200
		runs = runs_response.json()
		assert len(runs) >= 1