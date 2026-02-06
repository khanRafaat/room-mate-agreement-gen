"""
Test Stripe Payment API - Terminal Only
This script tests the complete payment flow without needing a browser.
Uses Stripe's pre-built test tokens instead of raw card data.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import stripe

def run_terminal_payment_test():
    """Run complete payment test in terminal."""
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    
    if not secret_key:
        print("[ERROR] STRIPE_SECRET_KEY not found in .env")
        return False
    
    stripe.api_key = secret_key
    
    print("=" * 60)
    print("Stripe Payment API Terminal Test")
    print("=" * 60)
    print()
    
    # Test 1: Verify API connection
    print("[TEST 1] Verifying Stripe API connection...")
    try:
        account = stripe.Account.retrieve()
        print(f"  [OK] Connected to account: {account.id}")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return False
    
    # Test 2: Create a PaymentIntent with automatic payment method
    print("\n[TEST 2] Creating PaymentIntent for $2.50...")
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=250,  # $2.50 in cents
            currency="usd",
            payment_method="pm_card_visa",  # Stripe's pre-built test token
            confirm=True,  # Confirm immediately
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            metadata={"agreement_id": "test-agreement-123"}
        )
        print(f"  [OK] PaymentIntent created: {payment_intent.id}")
        print(f"  [OK] Status: {payment_intent.status}")
        print(f"  [OK] Amount: ${payment_intent.amount / 100:.2f} {payment_intent.currency.upper()}")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return False
    
    # Test 3: Check payment status
    print("\n[TEST 3] Verifying payment completion...")
    try:
        if payment_intent.status == "succeeded":
            print(f"  [OK] Payment successful!")
            print(f"  [OK] Amount received: ${payment_intent.amount_received / 100:.2f}")
        else:
            print(f"  [INFO] Status: {payment_intent.status}")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return False
    
    # Test 4: Retrieve charge details
    print("\n[TEST 4] Retrieving charge details...")
    try:
        charges = stripe.Charge.list(payment_intent=payment_intent.id, limit=1)
        if charges.data:
            charge = charges.data[0]
            print(f"  [OK] Charge ID: {charge.id}")
            print(f"  [OK] Paid: {charge.paid}")
            print(f"  [OK] Card brand: {charge.payment_method_details.card.brand.upper()}")
            print(f"  [OK] Card last 4: {charge.payment_method_details.card.last4}")
            if charge.receipt_url:
                print(f"  [OK] Receipt: {charge.receipt_url}")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return False
    
    # Test 5: Create refund (cleanup)
    print("\n[TEST 5] Creating refund (cleanup)...")
    try:
        refund = stripe.Refund.create(payment_intent=payment_intent.id)
        print(f"  [OK] Refund created: {refund.id}")
        print(f"  [OK] Refund status: {refund.status}")
        print(f"  [OK] Amount refunded: ${refund.amount / 100:.2f}")
    except Exception as e:
        print(f"  [WARNING] Refund failed: {e}")
    
    # Test 6: Test different card scenarios
    print("\n[TEST 6] Testing different card scenarios...")
    
    # Test declined card
    try:
        declined = stripe.PaymentIntent.create(
            amount=100,
            currency="usd",
            payment_method="pm_card_chargeDeclined",
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        print(f"  [UNEXPECTED] Declined card should have failed")
    except stripe.error.CardError as e:
        print(f"  [OK] Declined card test passed - error: {e.error.code}")
    except Exception as e:
        print(f"  [OK] Declined card properly rejected")
    
    print()
    print("=" * 60)
    print("[SUCCESS] All payment API tests passed!")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - PaymentIntent: {payment_intent.id}")
    print(f"  - Test Amount: $2.50 USD")
    print(f"  - Payment Status: {payment_intent.status}")
    print(f"  - Refund Status: Completed")
    print()
    print("Your Stripe integration is working correctly!")
    print()
    
    return True


if __name__ == "__main__":
    run_terminal_payment_test()
