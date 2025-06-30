import os
import django
import sys
from pathlib import Path
from datetime import datetime

# Add the project root directory to Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from tuition.models import Student, StudentPayer, PaymentBreakdown, Payment, Card
import stripe
from django.conf import settings

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

def test_credit_card_payment():
    """Test credit card payment - this works without verification"""
    print("=== Testing Credit Card Payment ===\n")
    
    try:
        # Create test user (payer) with unique username
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        username = f'testpayer_card_{timestamp}'
        
        payer = User.objects.create_user(
            username=username,
            email=f'testpayer_card_{timestamp}@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Payer',
            user_type='payer'
        )
        print(f"✅ Created test payer: {username}")
        
        # Create test student with unique ID
        student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            date_of_birth='2010-01-01',
            student_id=f'TEST_CARD{timestamp}',
            grade='9'
        )
        print(f"✅ Created test student: {student.student_id}")
        
        # Link student to payer
        StudentPayer.objects.create(
            student=student,
            payer=payer,
            relationship='guardian'
        )
        print("✅ Linked student to payer")
        
        # Create test payment breakdown item
        payment_item = PaymentBreakdown.objects.create(
            student=student,
            description='Test Credit Card Payment - $1.00',
            amount=1.00,
            due_date=timezone.now().date(),
            is_paid=False
        )
        print("✅ Created test payment item")
        
        # Get or create Stripe customer
        if not payer.stripe_customer_id:
            customer = stripe.Customer.create(
                email=payer.email,
                name=f"{payer.first_name} {payer.last_name}",
                metadata={'user_id': payer.id}
            )
            payer.stripe_customer_id = customer.id
            payer.save()
            print("✅ Created Stripe customer")
        else:
            customer = stripe.Customer.retrieve(payer.stripe_customer_id)
            print("✅ Retrieved existing Stripe customer")
        
        # Create a PaymentIntent for credit card payment
        payment_intent = stripe.PaymentIntent.create(
            amount=int(payment_item.amount * 100),  # Convert to cents
            currency='usd',
            customer=customer.id,
            payment_method_types=['card'],
            metadata={
                'student_id': student.id,
                'user_id': payer.id,
                'test_type': 'credit_card'
            }
        )
        print("✅ Created PaymentIntent")
        
        # Use Stripe's test credit card token (safer than raw card data)
        # Create a PaymentMethod with test card token
        payment_method = stripe.PaymentMethod.create(
            type='card',
            card={
                'token': 'tok_visa'  # Stripe test token for Visa card
            },
            billing_details={
                'name': f"{payer.first_name} {payer.last_name}",
                'email': payer.email
            }
        )
        print("✅ Created PaymentMethod with test credit card")
        
        # Attach the payment method to the customer
        payment_method.attach(customer=customer.id)
        print("✅ Attached PaymentMethod to customer")
        
        # Confirm the PaymentIntent with the credit card
        confirmed_payment = stripe.PaymentIntent.confirm(
            payment_intent.id,
            payment_method=payment_method.id
        )
        print("✅ Confirmed PaymentIntent")
        
        # Check if payment succeeded
        if confirmed_payment.status == 'succeeded':
            print("✅ Credit card payment succeeded!")
            
            # Create card record in our database
            card = Card.objects.create(
                user=payer,
                nickname='Test Visa Card',
                last4='4242',  # Last 4 digits of test card
                brand='Visa',
                exp_month=12,
                exp_year=2025,
                stripe_payment_method_id=payment_method.id
            )
            print("✅ Created card record")
            
            # Create payment record
            payment = Payment.objects.create(
                student=student,
                amount=payment_item.amount,
                status='completed',
                bank_account=None,  # No bank account for credit card
                receipt_number=payment_intent.id
            )
            print("✅ Created payment record")
            
            # Mark payment item as paid
            payment_item.is_paid = True
            payment_item.save()
            print("✅ Marked payment item as paid")
            
            print(f"\n🎉 Credit card payment test completed successfully!")
            print(f"Payment ID: {payment_intent.id}")
            print(f"Amount: ${payment_item.amount}")
            print(f"Status: {confirmed_payment.status}")
            print(f"Card: {card.brand} ****{card.last4}")
            
            # Verify database records
            print(f"\n📊 Database Verification:")
            print(f"   Payment record exists: {Payment.objects.filter(id=payment.id).exists()}")
            print(f"   Card record exists: {Card.objects.filter(id=card.id).exists()}")
            print(f"   Payment item marked as paid: {payment_item.is_paid}")
            print(f"   Student has {student.payments.count()} payment(s)")
            
        else:
            print(f"❌ Payment failed with status: {confirmed_payment.status}")
            if confirmed_payment.last_payment_error:
                print(f"Error: {confirmed_payment.last_payment_error.message}")
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_payment_failure():
    """Test payment failure scenario"""
    print("\n=== Testing Payment Failure ===\n")
    
    try:
        # Create test user (payer) with unique username
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        username = f'testpayer_fail_{timestamp}'
        
        payer = User.objects.create_user(
            username=username,
            email=f'testpayer_fail_{timestamp}@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Payer',
            user_type='payer'
        )
        print(f"✅ Created test payer: {username}")
        
        # Get or create Stripe customer
        if not payer.stripe_customer_id:
            customer = stripe.Customer.create(
                email=payer.email,
                name=f"{payer.first_name} {payer.last_name}",
                metadata={'user_id': payer.id}
            )
            payer.stripe_customer_id = customer.id
            payer.save()
            print("✅ Created Stripe customer")
        
        # Create a PaymentIntent for a small amount
        payment_intent = stripe.PaymentIntent.create(
            amount=100,  # $1.00 in cents
            currency='usd',
            customer=customer.id,
            payment_method_types=['card'],
            metadata={'test_type': 'payment_failure'}
        )
        print("✅ Created PaymentIntent")
        
        # Use Stripe's test card that will be declined
        payment_method = stripe.PaymentMethod.create(
            type='card',
            card={
                'token': 'tok_chargeDeclined'  # Stripe test token for declined card
            },
            billing_details={
                'name': f"{payer.first_name} {payer.last_name}",
                'email': payer.email
            }
        )
        print("✅ Created PaymentMethod with declined test card")
        
        # Attach the payment method to the customer
        payment_method.attach(customer=customer.id)
        print("✅ Attached PaymentMethod to customer")
        
        # Try to confirm the PaymentIntent (should fail)
        try:
            confirmed_payment = stripe.PaymentIntent.confirm(
                payment_intent.id,
                payment_method=payment_method.id
            )
            print("❌ Payment should have failed but didn't")
        except stripe.error.CardError as e:
            print("✅ Payment correctly failed as expected")
            print(f"   Error: {e.error.message}")
            print(f"   Error code: {e.error.code}")
        except Exception as e:
            print(f"❌ Unexpected error during payment failure test: {str(e)}")
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    print("=== Credit Card Payment Testing Suite ===\n")
    
    # Test successful payment
    test_credit_card_payment()
    
    # Test payment failure
    test_payment_failure()
    
    print("\n" + "=" * 60)
    print("✅ Credit card testing completed!")
    print("\n💡 Next Steps:")
    print("   1. Start your Django server: python manage.py runserver")
    print("   2. Test the web interface with these test cards:")
    print("      - Success: 4242424242424242")
    print("      - Decline: 4000000000000002")
    print("   3. For bank account testing, use the web interface")
    print("   4. Complete microdeposits verification manually") 