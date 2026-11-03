"""
Unit Tests for OrderStateMachine (Order Lifecycle & Transitions)
"""
import pytest
from app.services import OrderStateMachine

def test_valid_transitions_from_pending():
    assert OrderStateMachine.validate_transition("PENDING", "PAID") is True
    assert OrderStateMachine.validate_transition("PENDING", "CANCELLED") is True

def test_valid_transitions_from_paid():
    assert OrderStateMachine.validate_transition("PAID", "PROCESSING") is True
    assert OrderStateMachine.validate_transition("PAID", "REFUNDED") is True

def test_valid_transitions_from_processing():
    assert OrderStateMachine.validate_transition("PROCESSING", "SHIPPED") is True
    assert OrderStateMachine.validate_transition("PROCESSING", "CANCELLED") is True

def test_valid_transitions_from_shipped():
    assert OrderStateMachine.validate_transition("SHIPPED", "DELIVERED") is True

def test_terminal_states():
    assert OrderStateMachine.validate_transition("DELIVERED", "CANCELLED") is False
    assert OrderStateMachine.validate_transition("DELIVERED", "PAID") is False
    assert OrderStateMachine.validate_transition("CANCELLED", "PENDING") is False
    assert OrderStateMachine.validate_transition("REFUNDED", "PAID") is False

def test_invalid_transitions():
    # Direct jump from PENDING to DELIVERED is forbidden
    assert OrderStateMachine.validate_transition("PENDING", "DELIVERED") is False
    # Direct jump from PENDING to SHIPPED without PAID is forbidden
    assert OrderStateMachine.validate_transition("PENDING", "SHIPPED") is False

def test_case_insensitive_states():
    assert OrderStateMachine.validate_transition("pending", "paid") is True
    assert OrderStateMachine.validate_transition("Processing", "Shipped") is True
