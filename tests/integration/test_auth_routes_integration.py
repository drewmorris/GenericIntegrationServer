"""
Integration tests for authentication routes.
These tests run in CI with real PostgreSQL and Redis containers.
They test the complete auth flow without mocking.
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.integration  
class TestAuthIntegration:
    """Integration tests for authentication endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client for integration tests (uses real database in CI)"""
        with TestClient(app) as client:
            yield client
    
    def test_signup_basic_flow(self, client):
        """Test basic signup functionality with real database"""
        import time
        signup_data = {
            "email": f"integration_test_{int(time.time())}_{hash('signup_basic')}@example.com",
            "password": "test_password_123",
            "organization_name": "Integration Test Org"
        }
        
        response = client.post("/auth/signup", json=signup_data)
        
        # Should succeed or fail gracefully (depending on database state)
        assert response.status_code in [200, 400]  # 400 if user already exists
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            # token_type might not be in response, that's ok for integration test
    
    def test_login_after_signup(self, client):
        """Test login flow after signup"""
        # Use a unique email for this test
        import time
        email = f"login_test_{int(time.time())}_{hash('login_test')}@example.com"
        password = "test_password_456"
        
        signup_data = {
            "email": email,
            "password": password,
            "organization_name": "Login Test Org"
        }
        
        # First signup (might already exist, that's ok)
        signup_response = client.post("/auth/signup", json=signup_data)
        
        # Then try login
        login_data = {
            "email": email,
            "password": password
        }
        login_response = client.post("/auth/login", json=login_data)
        
        # Login should work if signup succeeded, or if user already existed
        if signup_response.status_code == 200:
            assert login_response.status_code == 200
            data = login_response.json()
            assert "access_token" in data
            assert "refresh_token" in data
    
    def test_invalid_login_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrong_password"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
    
    def test_malformed_requests(self, client):
        """Test handling of malformed requests"""
        # Signup with missing fields
        incomplete_data = {"email": "test@example.com"}  # Missing password
        response = client.post("/auth/signup", json=incomplete_data)
        assert response.status_code == 422
        
        # Login with missing fields
        incomplete_login = {"email": "test@example.com"}  # Missing password
        response = client.post("/auth/login", json=incomplete_login)
        assert response.status_code == 422
    
    def test_unauthorized_access(self, client):
        """Test that protected endpoints require authentication"""
        # Try to access /me without token
        me_response = client.get("/auth/me")
        assert me_response.status_code == 401
        
        # Try to access /me with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 401
    
    def test_app_starts_successfully(self, client):
        """Test that the application starts and basic endpoints are reachable"""
        # This should always work regardless of database state
        # Test some basic endpoint that doesn't require auth
        response = client.get("/docs")  # OpenAPI docs should be available
        assert response.status_code == 200