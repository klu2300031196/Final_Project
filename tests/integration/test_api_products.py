"""
API Integration Tests: Products Catalog CRUD & Search
"""
import pytest
import json

def test_get_all_products(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.get_json()
    assert "products" in data
    assert data["count"] >= 5
    assert any(p["name"] == "Cloud Microservice License" for p in data["products"])

def test_search_products_by_keyword(client):
    response = client.get("/api/products?search=Docker")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] >= 1
    assert "Docker" in data["products"][0]["name"]

def test_filter_products_by_category(client):
    response = client.get("/api/products?category=Security")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] >= 1
    for p in data["products"]:
        assert p["category"] == "Security"

def test_get_single_product_valid(client):
    response = client.get("/api/products/1")
    assert response.status_code == 200
    product = response.get_json()
    assert product["id"] == 1
    assert product["name"] == "Cloud Microservice License"

def test_get_single_product_not_found(client):
    response = client.get("/api/products/999999")
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"].lower()

def test_admin_create_product_success(client, admin_headers):
    payload = {
        "name": "DevOps Automated Load Generator",
        "category": "Testing",
        "price": 299.00,
        "stock": 25,
        "description": "Enterprise performance test engine"
    }
    response = client.post("/api/products", headers=admin_headers, json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "DevOps Automated Load Generator"
    assert data["id"] > 0

def test_admin_delete_product_success(client, admin_headers):
    # First create a temporary product
    temp = client.post("/api/products", headers=admin_headers, json={
        "name": "Temp Test Product",
        "category": "Temp",
        "price": 10.0,
        "stock": 1
    }).get_json()
    
    prod_id = temp["id"]
    del_res = client.delete(f"/api/products/{prod_id}", headers=admin_headers)
    assert del_res.status_code == 200
    
    # Verify it is deleted
    get_res = client.get(f"/api/products/{prod_id}")
    assert get_res.status_code == 404
