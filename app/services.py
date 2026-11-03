"""
Business Logic & Domain Services for AUT.
Includes Pricing Engine, Order Workflow, and Payment Gateway Simulation.
"""
from typing import List, Dict, Tuple
import uuid
from datetime import datetime

class PricingService:
    """Calculates order totals, progressive discounts, promo codes, and taxes."""
    
    TAX_RATE = 0.08  # 8% standard sales tax
    PROMO_CODES = {
        "DEVOPS20": 0.20,     # 20% off
        "AUTOMATION10": 0.10, # 10% off
        "FREESHIP": 0.05      # 5% off
    }

    @classmethod
    def calculate_subtotal(cls, items: List[Dict]) -> float:
        if not items:
            raise ValueError("Order must contain at least one item")
        
        subtotal = 0.0
        for item in items:
            price = float(item.get("price", 0))
            quantity = int(item.get("quantity", 0))
            if price < 0:
                raise ValueError("Item price cannot be negative")
            if quantity <= 0:
                raise ValueError("Item quantity must be greater than zero")
            subtotal += price * quantity
        return round(subtotal, 2)

    @classmethod
    def calculate_discount(cls, subtotal: float, promo_code: str = None) -> float:
        if subtotal < 0:
            raise ValueError("Subtotal cannot be negative")

        discount = 0.0
        # Volume tiered discount
        if subtotal >= 500:
            discount += subtotal * 0.15  # 15% tier
        elif subtotal >= 200:
            discount += subtotal * 0.05  # 5% tier

        # Promo code discount
        if promo_code:
            code_upper = promo_code.strip().upper()
            if code_upper in cls.PROMO_CODES:
                discount += subtotal * cls.PROMO_CODES[code_upper]
            else:
                raise ValueError(f"Invalid promo code: {promo_code}")

        # Discount cannot exceed subtotal
        return round(min(discount, subtotal), 2)

    @classmethod
    def calculate_order_summary(cls, items: List[Dict], promo_code: str = None) -> Dict:
        subtotal = cls.calculate_subtotal(items)
        discount = cls.calculate_discount(subtotal, promo_code)
        discounted_amount = subtotal - discount
        tax = round(discounted_amount * cls.TAX_RATE, 2)
        total = round(discounted_amount + tax, 2)

        return {
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "total_amount": total
        }


class OrderStateMachine:
    """Manages order lifecycle state transitions."""
    
    ALLOWED_TRANSITIONS = {
        "PENDING": ["PAID", "CANCELLED"],
        "PAID": ["PROCESSING", "REFUNDED"],
        "PROCESSING": ["SHIPPED", "CANCELLED"],
        "SHIPPED": ["DELIVERED"],
        "DELIVERED": [],
        "CANCELLED": [],
        "REFUNDED": []
    }

    @classmethod
    def validate_transition(cls, current_state: str, new_state: str) -> bool:
        curr = current_state.upper()
        nxt = new_state.upper()
        valid_next_states = cls.ALLOWED_TRANSITIONS.get(curr, [])
        return nxt in valid_next_states


class PaymentSimulator:
    """Simulates payment gateway transaction processing."""

    SUPPORTED_METHODS = ["CREDIT_CARD", "DEBIT_CARD", "UPI", "PAYPAL"]

    @classmethod
    def process_payment(cls, amount: float, method: str, card_token: str = None) -> Tuple[bool, str, Dict]:
        if amount <= 0:
            return False, "Payment amount must be greater than zero", {}

        method_upper = method.upper()
        if method_upper not in cls.SUPPORTED_METHODS:
            return False, f"Unsupported payment method: {method}", {}

        # Simulate test card failure scenario (for failure testing)
        if card_token and card_token.endswith("0000"):
            return False, "Card declined by issuing bank (Simulated Failure)", {}

        tx_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        return True, "Payment processed successfully", {
            "transaction_id": tx_id,
            "amount": round(amount, 2),
            "method": method_upper,
            "status": "SUCCESS",
            "timestamp": datetime.utcnow().isoformat()
        }
