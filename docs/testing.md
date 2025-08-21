# Testing Guide

This document outlines the testing strategy and best practices for the Generic Integration Server project.

## Testing Architecture

Our testing strategy follows industry best practices with a clear separation between unit and integration tests:

### Unit Tests
- **Location**: `tests/` (excluding `tests/integration/`)
- **Purpose**: Test individual functions, classes, and modules in isolation
- **Dependencies**: Use mocks and stubs, no external services required
- **Speed**: Fast execution (< 5 seconds per test)
- **Coverage**: Aim for 80%+ code coverage

### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test complete workflows with real database and services
- **Dependencies**: Require PostgreSQL, Redis, and other external services
- **Speed**: Slower execution (< 30 seconds per test)
- **Environment**: Run in CI with Docker containers

## Running Tests

### Local Development (Unit Tests Only)

```bash
# Run all unit tests with coverage
PYTHONPATH=/workspaces/GenericIntegrationServer poetry run pytest -q -k 'not integration' --cov=backend --cov-report=term-missing

# Run specific test file
PYTHONPATH=/workspaces/GenericIntegrationServer poetry run pytest tests/test_auth_routes_simple.py -v

# Run tests with specific marker
PYTHONPATH=/workspaces/GenericIntegrationServer poetry run pytest -m unit -v
```

### Using the Check Script

The project includes a comprehensive check script that handles the testing pipeline:

```bash
# Run unit tests only (recommended for local development)
./bin/check_codebase.sh --gh --no-web-checks

# Run full CI emulation with integration tests
./bin/check_codebase.sh --ci-emulate

# Interactive mode (choose what to run)
./bin/check_codebase.sh
```

### CI Environment

In CI, the pipeline automatically:
1. **Unit Tests**: Run with `pytest -k 'not integration'` (fast feedback)
2. **Integration Tests**: Run in GitHub Actions with real PostgreSQL/Redis containers
3. **Coverage**: Generate coverage reports and enforce thresholds

## Test Organization

### Test Markers

Tests are automatically marked based on their location:
- `@pytest.mark.unit`: Tests in `tests/` (excluding integration)
- `@pytest.mark.integration`: Tests in `tests/integration/`
- `@pytest.mark.slow`: Tests that take longer than expected

### Test Structure

```
tests/
├── conftest.py                 # Global fixtures and configuration
├── integration/                # Integration tests (CI only)
│   ├── test_auth_integration.py
│   └── test_sync_scheduler.py
├── test_auth_routes_simple.py  # Unit tests for auth routes
├── test_destinations_routes.py # Unit tests for destination routes
└── test_*.py                   # Other unit tests
```

## Writing Tests

### Unit Test Example

```python
"""
Unit tests for authentication routes
"""
import pytest
from unittest.mock import AsyncMock, patch

from backend.routes.auth import signup, login


class TestAuthRoutes:
    """Test authentication route functions"""
    
    @pytest.mark.asyncio
    async def test_signup_success(self):
        """Test successful signup"""
        mock_provider = AsyncMock()
        mock_provider.signup.return_value = None
        mock_provider.login.return_value = TokenPair(
            access_token="access_123",
            refresh_token="refresh_456"
        )
        
        with patch('backend.routes.auth._provider', return_value=mock_provider):
            result = await signup(SignupRequest(
                email="test@example.com",
                password="password123",
                organization_name="TestOrg"
            ), mock_provider)
        
        assert result.access_token == "access_123"
        mock_provider.signup.assert_called_once()
```

### Integration Test Example

```python
"""
Integration tests for authentication
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.integration
class TestAuthIntegration:
    """Integration tests for auth endpoints"""
    
    @pytest.fixture
    def client(self):
        with TestClient(app) as client:
            yield client
    
    def test_signup_flow(self, client):
        """Test complete signup flow with real database"""
        response = client.post("/auth/signup", json={
            "email": "integration_test@example.com",
            "password": "test_password_123",
            "organization_name": "Integration Test Org"
        })
        
        # Should succeed or fail gracefully
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
```

## Best Practices

### Unit Tests
1. **Mock External Dependencies**: Use `AsyncMock` and `MagicMock` for database, HTTP clients, etc.
2. **Test One Thing**: Each test should verify a single behavior
3. **Clear Test Names**: Use descriptive names like `test_signup_success` or `test_login_invalid_credentials`
4. **Arrange-Act-Assert**: Structure tests clearly with setup, execution, and verification
5. **Use Fixtures**: Leverage pytest fixtures for common test data and setup

### Integration Tests
1. **Minimal Mocking**: Only mock external services (not internal components)
2. **Database State**: Assume clean database state, handle existing data gracefully
3. **Error Handling**: Test both success and failure scenarios
4. **Performance**: Keep tests under 30 seconds each
5. **CI Only**: Don't run integration tests locally unless necessary

### Coverage Guidelines
- **Target**: 80% overall coverage
- **Critical Paths**: 100% coverage for authentication, security, and data handling
- **New Code**: All new features must include comprehensive tests
- **Exclusions**: Generated code, migrations, and simple getters/setters can be excluded

## Fixtures and Utilities

### Common Fixtures (conftest.py)
- `sample_org_id`: Consistent organization ID for tests
- `sample_user_id`: Consistent user ID for tests  
- `sample_user_data`: Standard user signup data
- `sample_profile_data`: Standard connector profile data
- `unit_test_client`: FastAPI test client for unit tests

### Test Utilities
- Performance monitoring (warns about slow tests)
- Automatic test marking based on file location
- Environment variable management for test isolation

## Troubleshooting

### Common Issues

1. **Import Errors**: Set `PYTHONPATH=/workspaces/GenericIntegrationServer` before running pytest
2. **Database Connection Errors**: Integration tests require real database (CI environment)
3. **Async Test Issues**: Use `@pytest.mark.asyncio` for async test functions
4. **Mock Errors**: Use `AsyncMock` for async functions, `MagicMock` for sync functions

### Debugging Tests

```bash
# Run with verbose output
PYTHONPATH=/workspaces/GenericIntegrationServer poetry run pytest tests/test_auth.py -v -s

# Run single test with debugging
PYTHONPATH=/workspaces/GenericIntegrationServer poetry run pytest tests/test_auth.py::TestAuth::test_signup -v -s --pdb

# Show test coverage gaps
PYTHONPATH=/workspaces/GenericIntegrationServer poetry run pytest --cov=backend --cov-report=html
```

## CI Pipeline

The CI pipeline (`./github/workflows/ci.yml`) automatically:

1. **Setup**: Start PostgreSQL and Redis containers
2. **Dependencies**: Install Python dependencies via Poetry
3. **Linting**: Run Ruff and MyPy checks
4. **Unit Tests**: Execute fast unit tests for immediate feedback
5. **Integration Tests**: Run comprehensive integration tests with real services
6. **Coverage**: Generate and upload coverage reports
7. **Artifacts**: Store test results and logs

## Performance Monitoring

Tests are automatically monitored for performance:
- **Unit Tests**: Warn if > 5 seconds
- **Integration Tests**: Warn if > 30 seconds
- **Slow Tests**: Marked with `@pytest.mark.slow` for optional exclusion

## Future Improvements

1. **Parallel Execution**: Run tests in parallel for faster feedback
2. **Test Data Factories**: Create factory functions for complex test data
3. **Property-Based Testing**: Add Hypothesis for property-based tests
4. **Visual Testing**: Add screenshot testing for web components
5. **Load Testing**: Add performance tests for critical endpoints

