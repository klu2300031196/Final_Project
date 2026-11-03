"""
End-to-End (E2E) Continuous Integration & Business Flow Validation
Simulates multi-actor journey: Admin -> Customer -> Order -> Payment -> Inventory -> Metrics
"""
import pytest
import json

def test_complete_enterprise_e2e_journey(client, admin_headers):
    # STEP 1: Admin provisions a new high-value product
    new_prod_res = client.post("/api/products", headers=admin_headers, json={
        "name": "Enterprise Continuous Testing Cloud Node",
        "category": "Cloud Infrastructure",
        "price": 350.00,
        "stock": 10,
        "description": "High throughput test execution runner"
    })
    assert new_prod_res.status_code == 201
    product_id = new_prod_res.get_json()["id"]

    # STEP 2: New customer registers
    customer_user = f"e2e_customer_{product_id}"
    reg_res = client.post("/api/auth/register", json={
        "username": customer_user,
        "password": "SecurePassword@123",
        "email": f"{customer_user}@testing.org",
        "role": "customer"
    })
    assert reg_res.status_code == 201
    customer_token = reg_res.get_json()["token"]
    cust_headers = {"Authorization": f"Bearer {customer_token}", "Content-Type": "application/json"}

    # STEP 3: Customer searches for the new product
    search_res = client.get("/api/products?search=Enterprise+Continuous", headers=cust_headers)
    assert search_res.status_code == 200
    matched = search_res.get_json()["products"]
    assert any(p["id"] == product_id for p in matched)

    # STEP 4: Customer checks out with 2 units using DEVOPS20 promo
    order_res = client.post("/api/orders", headers=cust_headers, json={
        "items": [{"product_id": product_id, "quantity": 2}],
        "promo_code": "DEVOPS20"
    })
    assert order_res.status_code == 201
    order_id = order_res.get_json()["order_id"]
    summary = order_res.get_json()["summary"]
    # Subtotal = 2 * 350 = 700. Tier discount (15% = 105) + DEVOPS20 (20% = 140) = 245
    assert summary["subtotal"] == 700.0
    assert summary["discount"] == 245.0

    # STEP 5: Inventory validation - stock must be exactly 8 now
    prod_check = client.get(f"/api/products/{product_id}").get_json()
    assert prod_check["stock"] == 8

    # STEP 6: Customer processes payment
    pay_res = client.post(f"/api/orders/{order_id}/pay", headers=cust_headers, json={
        "payment_method": "UPI"
    })
    assert pay_res.status_code == 200
    assert pay_res.get_json()["status"] == "PAID"

    # STEP 7: Admin advances order workflow: PAID -> PROCESSING -> SHIPPED
    status_res1 = client.patch(f"/api/orders/{order_id}/status", headers=admin_headers, json={"status": "PROCESSING"})
    assert status_res1.status_code == 200

    status_res2 = client.patch(f"/api/orders/{order_id}/status", headers=admin_headers, json={"status": "SHIPPED"})
    assert status_res2.status_code == 200

    # STEP 8: Customer views their order list and verifies the SHIPPED status
    list_orders_res = client.get("/api/orders", headers=cust_headers)
    assert list_orders_res.status_code == 200
    orders = list_orders_res.get_json()["orders"]
    my_order = next((o for o in orders if o["id"] == order_id), None)
    assert my_order is not None
    assert my_order["status"] == "SHIPPED"

    # STEP 9: Telemetry telemetry verification
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.get_json()
    assert metrics_data["total_requests"] > 0
    assert metrics_data["status_2xx"] > 0
