"""
Integration tests for User Session (/api/auth/me) and Test Records (/api/test-records)
"""
import pytest

def test_auth_me_authenticated(client, customer_headers):
    res = client.get("/api/auth/me", headers=customer_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert "user" in data
    assert data["user"]["username"] == "john_doe"

def test_auth_me_unauthenticated(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401

def test_get_and_post_test_records(client):
    payload = {
        "pipeline_id": "CT-AZURE-TEST-RUN-101",
        "total_tests": 55,
        "passed_tests": 55,
        "failed_tests": 0,
        "duration_seconds": 5.4,
        "code_coverage_pct": 78.5,
        "p95_latency_ms": 12.1,
        "security_vulnerabilities": 0,
        "verdict": "PASSED"
    }
    post_res = client.post("/api/test-records", json=payload)
    assert post_res.status_code == 201
    assert post_res.get_json()["pipeline_id"] == "CT-AZURE-TEST-RUN-101"

    get_res = client.get("/api/test-records?limit=5")
    assert get_res.status_code == 200
    records = get_res.get_json()["records"]
    assert any(r["pipeline_id"] == "CT-AZURE-TEST-RUN-101" for r in records)
