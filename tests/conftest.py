"""
Global pytest configuration and fixtures for the test suite.
This file provides shared fixtures and configuration for both unit and integration tests.
"""
import os
import pytest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient


# Test constants
TEST_ORG_ID = "12345678-1234-5678-9012-123456789012"
TEST_USER_ID = "87654321-4321-8765-2109-876543210987"


@pytest.fixture
def sample_org_id():
    """Consistent organization ID for tests."""
    return TEST_ORG_ID


@pytest.fixture
def sample_user_id():
    """Consistent user ID for tests."""
    return TEST_USER_ID


@pytest.fixture
def sample_profile_data(sample_org_id, sample_user_id):
    """Sample connector profile data for tests."""
    return {
        "organization_id": sample_org_id,
        "user_id": sample_user_id,
        "name": "Test Profile",
        "source": "mock_source",
        "connector_config": {"destination": "csv"},
        "interval_minutes": 60,
        "credential_id": None,
        "status": "active"
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for tests."""
    return {
        "email": "test@example.com",
        "password": "test_password_123",
        "organization_name": "Test Organization"
    }


@pytest.fixture
def unit_test_client():
    """Create a test client for unit tests (no database dependencies)."""
    # Import here to avoid circular imports during test discovery
    from backend.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def integration_client():
    """Create a test client for integration tests (uses real database in CI)."""
    # Import here to avoid circular imports during test discovery
    from backend.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_integration_client(integration_client):
    """Create an integration client with real authentication for end-to-end tests."""
    import time
    
    # Create a unique test user
    unique_email = f"integration_test_{int(time.time())}@example.com"
    signup_data = {
        "email": unique_email,
        "password": "test_password_123",
        "organization_name": "Integration Test Org"
    }
    
    # Sign up to get real auth tokens
    signup_response = integration_client.post("/auth/signup", json=signup_data)
    
    if signup_response.status_code == 200:
        token_data = signup_response.json()
        access_token = token_data["access_token"]
        
        # Set authorization header on the client
        integration_client.headers.update({"Authorization": f"Bearer {access_token}"})
        
        return integration_client
    else:
        # If signup fails, try login with a test user that might already exist
        login_data = {"email": unique_email, "password": "test_password_123"}
        login_response = integration_client.post("/auth/login", json=login_data)
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data["access_token"]
            integration_client.headers.update({"Authorization": f"Bearer {access_token}"})
            return integration_client
        else:
            raise Exception(f"Failed to authenticate test user: signup={signup_response.status_code}, login={login_response.status_code}")





# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires database)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        "TESTING": "1",
        "LOG_LEVEL": "WARNING",
    }
    
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


# Performance monitoring for tests
@pytest.fixture(autouse=True)
def monitor_test_performance(request):
    """Monitor test performance and warn about slow tests."""
    import time
    
    start_time = time.time()
    yield
    duration = time.time() - start_time
    
    # Warn about slow tests (>5 seconds for unit tests, >30 seconds for integration tests)
    if hasattr(request.node, 'get_closest_marker'):
        is_integration = request.node.get_closest_marker('integration') is not None
        threshold = 30.0 if is_integration else 5.0
        
        if duration > threshold:
            test_type = "integration" if is_integration else "unit"
            print(f"\n⚠️  Slow {test_type} test: {request.node.name} took {duration:.2f}s")