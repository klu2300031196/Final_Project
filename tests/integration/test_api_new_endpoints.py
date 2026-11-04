"""
Integration tests for User Session (/api/auth/me) and Test Records Security (/api/test-records)
Enforces JWT authentication, signature validation, expiration checks, and error responses.
"""
import pytest
from app.auth import generate_token

def test_auth_me_authenticated(client, customer_headers):
    """Verify authenticated user can fetch their own identity."""
    res = client.get("/api/auth/me", headers=customer_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert "user" in data
    assert data["user"]["username"] == "john_doe"

def test_auth_me_unauthenticated(client):
    """Verify unauthenticated request to /api/auth/me is blocked with 401."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert "Authorization header" in res.get_json()["error"]

def test_get_test_records_missing_token(client):
    """Requirement: Requests without a JWT Bearer token must return HTTP 401 Unauthorized."""
    res = client.get("/api/test-records")
    assert res.status_code == 401
    data = res.get_json()
    assert "Missing or invalid Authorization header" in data["error"]

def test_get_test_records_invalid_token(client):
    """Requirement: Requests with an invalid/tampered token signature must return HTTP 401."""
    invalid_headers = {"Authorization": "Bearer fake.tampered.token123"}
    res = client.get("/api/test-records", headers=invalid_headers)
    assert res.status_code == 401
    data = res.get_json()
    assert "Unauthorized" in data["error"]

def test_get_test_records_expired_token(client):
    """Requirement: Requests with an expired JWT token must return HTTP 401."""
    expired_token = generate_token(user_id=1, username="admin", role="admin", expires_in=-60)
    expired_headers = {"Authorization": f"Bearer {expired_token}"}
    res = client.get("/api/test-records", headers=expired_headers)
    assert res.status_code == 401
    data = res.get_json()
    assert "expired" in data["error"].lower()

def test_get_test_records_valid_token(client, customer_headers):
    """Requirement: Requests with a valid JWT Bearer token must return HTTP 200 and records."""
    res = client.get("/api/test-records?limit=5", headers=customer_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert "records" in data
    assert "count" in data
    assert isinstance(data["records"], list)

def test_post_test_records_missing_token(client):
    """Requirement: Unauthenticated POST to /api/test-records must be blocked with HTTP 401."""
    payload = {
        "pipeline_id": "UNAUTH-RUN-999",
        "total_tests": 10,
        "passed_tests": 10
    }
    res = client.post("/api/test-records", json=payload)
    assert res.status_code == 401

def test_post_test_records_valid_token(client, admin_headers):
    """Requirement: Authenticated POST to /api/test-records must save record and return HTTP 201."""
    payload = {
        "pipeline_id": "CT-SECURITY-AUDIT-VERIFIED-1",
        "total_tests": 60,
        "passed_tests": 60,
        "failed_tests": 0,
        "duration_seconds": 4.5,
        "code_coverage_pct": 91.2,
        "p95_latency_ms": 10.5,
        "security_vulnerabilities": 0,
        "verdict": "PASSED"
    }
    res = client.post("/api/test-records", headers=admin_headers, json=payload)
    assert res.status_code == 201
    assert res.get_json()["pipeline_id"] == "CT-SECURITY-AUDIT-VERIFIED-1"
def test_post_test_records_missing_pipeline_id(client, admin_headers):
    payload = {
        "total_tests": 10,
        "passed_tests": 10,
        "failed_tests": 0
    }

    response = client.post(
        "/api/test-records",
        headers=admin_headers,
        json=payload
    )

    assert response.status_code == 400
    assert "pipeline_id is required" in response.get_json()["error"]
def test_post_test_records_missing_pipeline_id(client, admin_headers):
    """POST without pipeline_id must return HTTP 400."""
    payload = {
        "total_tests": 10,
        "passed_tests": 10,
        "failed_tests": 0
    }

    response = client.post(
        "/api/test-records",
        headers=admin_headers,
        json=payload
    )

    assert response.status_code == 400
    assert "pipeline_id is required" in response.get_json()["error"]
