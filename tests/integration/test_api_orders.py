"""
API Integration Tests: Orders, Inventory Sync, Payment Processing & State Flow
"""
import pytest
import json

def test_full_order_checkout_and_payment_lifecycle(client, customer_headers, admin_headers):
    # 1. Fetch initial stock of Product 2 ("DevOps CI/CD Pipeline Kit")
    prod_before = client.get("/api/products/2").get_json()
    initial_stock = prod_before["stock"]

    # 2. Place an order for 2 units with DEVOPS20 promo
    order_payload = {
        "items": [
            {"product_id": 2, "quantity": 2}
        ],
        "promo_code": "DEVOPS20"
    }
    create_res = client.post("/api/orders", headers=customer_headers, json=order_payload)
    assert create_res.status_code == 201
    order_data = create_res.get_json()
    order_id = order_data["order_id"]
    assert order_data["status"] == "PENDING"
    assert order_data["summary"]["discount"] > 0

    # 3. Verify product stock was decremented by 2
    prod_after = client.get("/api/products/2").get_json()
    assert prod_after["stock"] == initial_stock - 2

    # 4. Fetch order details
    get_order_res = client.get(f"/api/orders/{order_id}", headers=customer_headers)
    assert get_order_res.status_code == 200
    assert get_order_res.get_json()["status"] == "PENDING"

    # 5. Process Payment
    pay_payload = {
        "payment_method": "CREDIT_CARD",
        "card_token": "VALID_VISA_4242"
    }
    pay_res = client.post(f"/api/orders/{order_id}/pay", headers=customer_headers, json=pay_payload)
    assert pay_res.status_code == 200
    pay_data = pay_res.get_json()
    assert pay_data["status"] == "PAID"
    assert pay_data["payment"]["status"] == "SUCCESS"

    # 6. Admin transitions order from PAID -> PROCESSING -> SHIPPED
    patch_proc = client.patch(f"/api/orders/{order_id}/status", headers=admin_headers, json={"status": "PROCESSING"})
    assert patch_proc.status_code == 200
    assert patch_proc.get_json()["new_status"] == "PROCESSING"

    patch_ship = client.patch(f"/api/orders/{order_id}/status", headers=admin_headers, json={"status": "SHIPPED"})
    assert patch_ship.status_code == 200
    assert patch_ship.get_json()["new_status"] == "SHIPPED"
