"""
API Integration Tests: Edge Cases, Validations, and Negative Scenarios
"""

def test_order_with_insufficient_stock(client, customer_headers):
    payload = {
        "items": [{"product_id": 1, "quantity": 99999}]
    }
    response = client.post(
        "/api/orders",
        headers=customer_headers,
        json=payload
    )
    assert response.status_code == 400
    assert "insufficient stock" in response.get_json()["error"].lower()


def test_order_with_nonexistent_product_id(client, customer_headers):
    payload = {
        "items": [{"product_id": 999999, "quantity": 1}]
    }
    response = client.post(
        "/api/orders",
        headers=customer_headers,
        json=payload
    )
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"].lower()


def test_order_with_empty_items(client, customer_headers):
    payload = {"items": []}
    response = client.post(
        "/api/orders",
        headers=customer_headers,
        json=payload
    )
    assert response.status_code == 400


def test_payment_for_already_paid_order(client, customer_headers):
    order_res = client.post(
        "/api/orders",
        headers=customer_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]}
    ).get_json()

    order_id = order_res["order_id"]

    client.post(
        f"/api/orders/{order_id}/pay",
        headers=customer_headers,
        json={"payment_method": "UPI"}
    )

    duplicate_pay = client.post(
        f"/api/orders/{order_id}/pay",
        headers=customer_headers,
        json={"payment_method": "UPI"}
    )

    assert duplicate_pay.status_code == 400
    assert "cannot pay" in duplicate_pay.get_json()["error"].lower()


def test_invalid_order_state_transition(client, customer_headers, admin_headers):
    order_res = client.post(
        "/api/orders",
        headers=customer_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]}
    ).get_json()

    order_id = order_res["order_id"]

    illegal_patch = client.patch(
        f"/api/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "DELIVERED"}
    )

    assert illegal_patch.status_code == 400
    assert "invalid state transition" in illegal_patch.get_json()["error"].lower()


def test_customer_cannot_pay_another_customers_order(client, customer_headers):
    from app.auth import generate_token

    # Customer 1 creates an order
    order_res = client.post(
        "/api/orders",
        headers=customer_headers,
        json={"items": [{"product_id": 1, "quantity": 1}]}
    )
    assert order_res.status_code == 201
    order_id = order_res.get_json()["order_id"]

    # Customer 2 attempts to pay Customer 1's order
    other_token = generate_token(
        user_id=4,
        username="other_customer",
        role="customer"
    )
    other_headers = {
        "Authorization": f"Bearer {other_token}",
        "Content-Type": "application/json"
    }

    response = client.post(
        f"/api/orders/{order_id}/pay",
        headers=other_headers,
        json={"payment_method": "UPI"}
    )

    assert response.status_code == 403
    assert "unauthorized" in response.get_json()["error"].lower()
