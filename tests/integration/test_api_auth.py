"""
API Integration Tests: Authentication & Authorization Flow
"""
import pytest
import json

def test_user_registration_success(client):
    payload = {
        "username": "developer_alice",
        "password": "Password@123",
        "email": "alice@devops.org",
        "role": "customer"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["username"] == "developer_alice"
    assert "token" in data
    assert data["role"] == "customer"

def test_user_registration_duplicate_username(client):
    payload = {
        "username": "developer_alice",
        "password": "Password@123",
        "email": "alice2@devops.org"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    data = response.get_json()
    assert "already exists" in data["error"].lower()

def test_user_registration_short_password(client):
    payload = {
        "username": "short_user",
        "password": "123",
        "email": "short@devops.org"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "at least 6 characters" in response.get_json()["error"]

def test_login_success(client):
    payload = {
        "username": "developer_alice",
        "password": "Password@123"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "token" in data
    assert data["user"]["username"] == "developer_alice"

def test_login_invalid_password(client):
    payload = {
        "username": "developer_alice",
        "password": "WrongPassword!"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid username or password" in response.get_json()["error"]

def test_unauthorized_access_to_orders_endpoint(client):
    # Calling /api/orders without Bearer token must be rejected
    response = client.get("/api/orders")
    assert response.status_code == 401
    data = response.get_json()
    assert "Authorization header" in data["error"]

def test_forbidden_role_access(client, customer_headers):
    # Standard customer attempting to create a product (Admin only)
    new_product = {
        "name": "Unauthorized Product",
        "price": 50.0,
        "stock": 10
    }
    response = client.post("/api/products", headers=customer_headers, json=new_product)
    assert response.status_code == 403
    assert "insufficient permissions" in response.get_json()["error"].lower()
