"""
Unit Tests for PaymentSimulator (Transaction Processing & Validation)
"""
import pytest
from app.services import PaymentSimulator

def test_successful_payment():
    success, msg, details = PaymentSimulator.process_payment(amount=150.0, method="CREDIT_CARD")
    assert success is True
    assert msg == "Payment processed successfully"
    assert details["status"] == "SUCCESS"
    assert details["amount"] == 150.0
    assert details["method"] == "CREDIT_CARD"
    assert details["transaction_id"].startswith("TXN-")

def test_payment_with_all_supported_methods():
    for method in ["CREDIT_CARD", "DEBIT_CARD", "UPI", "PAYPAL"]:
        success, _, _ = PaymentSimulator.process_payment(50.0, method)
        assert success is True

def test_payment_with_unsupported_method():
    success, msg, _ = PaymentSimulator.process_payment(100.0, "BITCOIN")
    assert success is False
    assert "Unsupported payment method" in msg

def test_payment_negative_or_zero_amount():
    success, msg, _ = PaymentSimulator.process_payment(0.0, "UPI")
    assert success is False
    assert "greater than zero" in msg

    success_neg, _, _ = PaymentSimulator.process_payment(-25.0, "UPI")
    assert success_neg is False

def test_simulated_card_decline_scenario():
    # Token ending with 0000 simulates bank decline
    success, msg, details = PaymentSimulator.process_payment(200.0, "CREDIT_CARD", card_token="CARD_FAIL_0000")
    assert success is False
    assert "declined" in msg.lower()
