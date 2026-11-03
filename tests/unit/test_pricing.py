"""
Unit Tests for PricingService (Subtotals, Discounts, Taxes, Promo Codes)
"""
import pytest
from app.services import PricingService

def test_calculate_subtotal_valid():
    items = [
        {"price": 100.0, "quantity": 2},
        {"price": 50.0, "quantity": 1}
    ]
    subtotal = PricingService.calculate_subtotal(items)
    assert subtotal == 250.0

def test_calculate_subtotal_empty_items_raises_error():
    with pytest.raises(ValueError, match="at least one item"):
        PricingService.calculate_subtotal([])

def test_calculate_subtotal_negative_price():
    with pytest.raises(ValueError, match="cannot be negative"):
        PricingService.calculate_subtotal([{"price": -10.0, "quantity": 1}])

def test_calculate_subtotal_invalid_quantity():
    with pytest.raises(ValueError, match="greater than zero"):
        PricingService.calculate_subtotal([{"price": 10.0, "quantity": 0}])

def test_calculate_discount_below_threshold():
    # Subtotal < 200 has 0 volume discount
    discount = PricingService.calculate_discount(150.0)
    assert discount == 0.0

def test_calculate_discount_tier_1():
    # Subtotal >= 200 gets 5% discount
    discount = PricingService.calculate_discount(200.0)
    assert discount == 10.0  # 5% of 200

def test_calculate_discount_tier_2():
    # Subtotal >= 500 gets 15% discount
    discount = PricingService.calculate_discount(600.0)
    assert discount == 90.0  # 15% of 600

def test_calculate_discount_with_promo_devops20():
    # Promo DEVOPS20 gives 20%
    discount = PricingService.calculate_discount(100.0, promo_code="DEVOPS20")
    assert discount == 20.0

def test_calculate_discount_with_promo_and_tier():
    # Subtotal 500: Tier 15% + Promo 20% = 35% discount
    discount = PricingService.calculate_discount(500.0, promo_code="DEVOPS20")
    assert discount == 175.0  # 35% of 500

def test_calculate_discount_invalid_promo_raises_error():
    with pytest.raises(ValueError, match="Invalid promo code"):
        PricingService.calculate_discount(100.0, promo_code="BOGUS_CODE")

def test_calculate_order_summary_end_to_end():
    items = [{"price": 100.0, "quantity": 2}]  # Subtotal = 200
    summary = PricingService.calculate_order_summary(items, promo_code="DEVOPS20")
    # Subtotal = 200.0
    # Tier 5% (10) + DEVOPS20 20% (40) = 50.0
    # Discounted subtotal = 150.0
    # Tax 8% of 150.0 = 12.0
    # Total = 162.0
    assert summary["subtotal"] == 200.0
    assert summary["discount"] == 50.0
    assert summary["tax"] == 12.0
    assert summary["total_amount"] == 162.0
