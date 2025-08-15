"""
Pytest configuration and fixtures for integration tests.
"""
import pytest
import os
import sys
import logging
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def app():
    """
    Create FastAPI application instance for testing.
    This triggers the normal startup process including database initialization.
    """
    from backend.main import app
    return app


@pytest.fixture(scope="session")
def client(app):
    """
    Create test client that uses the full application stack.
    This ensures database initialization happens through normal startup.
    """
    logger.info("🔧 Starting FastAPI test client (includes database initialization)...")
    
    with TestClient(app) as test_client:
        logger.info("✅ Integration test client ready")
        
        # Set up test data using the API instead of direct database access
        _setup_test_data_via_api(test_client)
        
        yield test_client
        logger.info("🧹 Integration test session complete")


@pytest.fixture(autouse=True)
def skip_if_no_database():
    """
    Automatically skip integration tests if database is not available.
    This runs before each test.
    """
    if not _database_available():
        pytest.skip("Database not available - skipping integration tests")


def _database_available() -> bool:
    """Check if database is available for testing."""
    try:
        import psycopg2
        
        # Get database connection parameters
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "55432"))  # CI uses 55432
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "integration_server")
        
        # Try to connect
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, database=db
        )
        conn.close()
        return True
        
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        return False


@pytest.fixture
def db_session():
    """
    Provide a clean database session for each test.
    This could be enhanced to use transactions that rollback after each test.
    """
    from backend.db.session import AsyncSessionLocal
    return AsyncSessionLocal


@pytest.fixture(scope="session")
async def sample_org_and_user():
    """
    Create sample organization and user for tests that need them.
    This runs once per test session and provides consistent IDs.
    """
    import uuid
    from backend.db import models as m
    from backend.db.session import AsyncSessionLocal
    
    # Use fixed UUIDs for predictable testing
    org_id = uuid.UUID("12345678-1234-5678-9012-123456789012")
    user_id = uuid.UUID("87654321-4321-8765-2109-876543210987")
    
    async with AsyncSessionLocal() as session:
        # Create organization
        org = m.Organization(
            id=org_id, 
            name="Test Organization",
            billing_plan="test",
            settings={}
        )
        
        # Create user  
        user = m.User(
            id=user_id,
            organization_id=org_id,
            email="test@example.com",
            hashed_pw="test_password_hash",
            role="admin"
        )
        
        session.add(org)
        session.add(user)
        await session.commit()
        await session.refresh(org)
        await session.refresh(user)
        
        return org, user


def _setup_test_data_via_api(client):
    """
    Set up test organization and user data using direct database insertion.
    This avoids async event loop conflicts with TestClient.
    """
    import uuid
    import psycopg2
    import os
    
    try:
        # Get database connection parameters
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "55432"))  # CI uses 55432
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "integration_server")
        
        # Use fixed UUIDs for predictable testing
        org_id = "12345678-1234-5678-9012-123456789012"
        user_id = "87654321-4321-8765-2109-876543210987"
        
        # Connect to database directly
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, database=db
        )
        cursor = conn.cursor()
        
        # Check if org already exists
        cursor.execute("SELECT id FROM organization WHERE id = %s", (org_id,))
        if cursor.fetchone():
            logger.info("Test organization already exists")
            cursor.close()
            conn.close()
            return
            
        # Insert organization
        cursor.execute("""
            INSERT INTO organization (id, name, billing_plan, settings, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (org_id, "Test Organization", "test", "{}"))
        
        # Insert user
        cursor.execute("""
            INSERT INTO "user" (id, organization_id, email, hashed_pw, role, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, org_id, "test@example.com", "test_password_hash", "admin"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ Test organization and user created via direct SQL")
        
    except Exception as e:
        logger.warning(f"Failed to set up test data: {e}")


@pytest.fixture
def test_org_user_ids():
    """
    Provide the standard test organization and user IDs.
    This is a synchronous fixture that can be used in non-async tests.
    """
    return {
        "org_id": "12345678-1234-5678-9012-123456789012",
        "user_id": "87654321-4321-8765-2109-876543210987"
    }
