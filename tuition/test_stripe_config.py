import os
import django
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')
django.setup()

import stripe
from django.conf import settings

def test_stripe_configuration():
    """Test basic Stripe configuration and connectivity"""
    print("=== Testing Stripe Configuration ===\n")
    
    # Check if Stripe keys are configured
    if not settings.STRIPE_SECRET_KEY:
        print("❌ STRIPE_SECRET_KEY not configured in settings")
        return False
    
    if not settings.STRIPE_PUBLISHABLE_KEY:
        print("❌ STRIPE_PUBLISHABLE_KEY not configured in settings")
        return False
    
    print(f"✅ Stripe keys configured")
    print(f"   Secret Key: {settings.STRIPE_SECRET_KEY[:12]}...")
    print(f"   Publishable Key: {settings.STRIPE_PUBLISHABLE_KEY[:12]}...")
    
    # Set the API key
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        # Test API connectivity by retrieving account information
        account = stripe.Account.retrieve()
        print(f"✅ Stripe API connection successful")
        print(f"   Account ID: {account.id}")
        print(f"   Account Type: {account.type}")
        print(f"   Country: {account.country}")
        
        # Check if bank accounts are enabled
        if hasattr(account, 'capabilities') and 'us_bank_account_ach_payment' in account.capabilities:
            if account.capabilities['us_bank_account_ach_payment'] == 'active':
                print("✅ Bank account payments are enabled")
            else:
                print(f"⚠️ Bank account payments status: {account.capabilities['us_bank_account_ach_payment']}")
        else:
            print("⚠️ Bank account payment capability not found")
        
        return True
        
    except stripe.error.AuthenticationError:
        print("❌ Stripe authentication failed - check your secret key")
        return False
    except stripe.error.APIError as e:
        print(f"❌ Stripe API error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def test_bank_account_creation():
    """Test creating a bank account PaymentMethod"""
    print("\n=== Testing Bank Account Creation ===\n")
    
    try:
        # Use Stripe's test bank account numbers
        payment_method = stripe.PaymentMethod.create(
            type='us_bank_account',
            us_bank_account={
                'routing_number': '110000000',  # Stripe test routing number
                'account_number': '000123456789',  # Stripe test account number
                'account_holder_type': 'individual',
                'account_type': 'checking'
            },
            billing_details={
                'name': 'Test User',
                'email': 'test@example.com'
            }
        )
        
        print("✅ Successfully created bank account PaymentMethod")
        print(f"   PaymentMethod ID: {payment_method.id}")
        print(f"   Account: ****{payment_method.us_bank_account.last4}")
        print(f"   Type: {payment_method.us_bank_account.account_type}")
        # Status field might not be available for all bank accounts
        if hasattr(payment_method.us_bank_account, 'status'):
            print(f"   Status: {payment_method.us_bank_account.status}")
        else:
            print(f"   Status: Not available")
        
        # Clean up
        payment_method.detach()
        print("✅ Cleaned up PaymentMethod")
        
        return True
        
    except stripe.error.StripeError as e:
        print(f"❌ Failed to create bank account: {str(e)}")
        return False

def test_payment_intent_creation():
    """Test creating a PaymentIntent for bank account payment"""
    print("\n=== Testing PaymentIntent Creation ===\n")
    
    try:
        # Create a PaymentIntent for $0.50
        payment_intent = stripe.PaymentIntent.create(
            amount=50,  # $0.50 in cents
            currency='usd',
            payment_method_types=['us_bank_account'],
            metadata={'test': 'bank_account_payment'}
        )
        
        print("✅ Successfully created PaymentIntent")
        print(f"   PaymentIntent ID: {payment_intent.id}")
        print(f"   Amount: ${payment_intent.amount / 100}")
        print(f"   Currency: {payment_intent.currency}")
        print(f"   Status: {payment_intent.status}")
        
        # Clean up
        payment_intent.cancel()
        print("✅ Cancelled PaymentIntent")
        
        return True
        
    except stripe.error.StripeError as e:
        print(f"❌ Failed to create PaymentIntent: {str(e)}")
        return False

if __name__ == "__main__":
    print("Stripe Bank Account Testing Suite\n")
    print("=" * 50)
    
    # Test configuration
    config_ok = test_stripe_configuration()
    
    if config_ok:
        # Test bank account creation
        test_bank_account_creation()
        
        # Test PaymentIntent creation
        test_payment_intent_creation()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("\nTo test a full payment flow, run:")
        print("python tuition/test_stripe_bank_payment.py")
    else:
        print("\n❌ Configuration test failed. Please fix Stripe configuration first.") 