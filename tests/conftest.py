"""
PyTest Configuration & Shared DevOps Fixtures.
Provides isolated test databases, test clients, and authentication tokens.
"""
import pytest
import os
import tempfile
from app.app import create_app
from app.auth import generate_token

@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

@pytest.fixture(scope="session")
def app(test_db_path):
    """Instantiate application configured with the test database."""
    app_instance = create_app(db_path=test_db_path)
    app_instance.config["TESTING"] = True
    return app_instance

@pytest.fixture
def client(app):
    """Provide Flask test client for API integration tests."""
    with app.test_client() as c:
        yield c

@pytest.fixture
def admin_headers():
    """Authorization headers for Admin role."""
    token = generate_token(user_id=1, username="admin", role="admin")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@pytest.fixture
def customer_headers():
    """Authorization headers for standard Customer role."""
    token = generate_token(user_id=3, username="john_doe", role="customer")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@pytest.fixture
def tester_headers():
    """Authorization headers for QA Tester role."""
    token = generate_token(user_id=2, username="qa_tester", role="tester")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
