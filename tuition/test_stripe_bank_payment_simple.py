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
from tuition.models import Student, StudentPayer, PaymentBreakdown, Payment, BankAccount
import stripe
from django.conf import settings

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY

def test_bank_account_payment_without_verification():
    """Test bank account payment without requiring verification"""
    print("=== Testing Bank Account Payment (No Verification Required) ===\n")
    
    try:
        # Create test user (payer) with unique username
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        username = f'testpayer_{timestamp}'
        
        payer = User.objects.create_user(
            username=username,
            email=f'testpayer_{timestamp}@example.com',
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
            student_id=f'TEST{timestamp}',
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
            description='Test Bank Payment - $0.50',
            amount=0.50,
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
        
        # Create a PaymentIntent for bank account payment
        payment_intent = stripe.PaymentIntent.create(
            amount=int(payment_item.amount * 100),  # Convert to cents
            currency='usd',
            customer=customer.id,
            payment_method_types=['us_bank_account'],
            metadata={
                'student_id': student.id,
                'user_id': payer.id,
                'test_type': 'bank_account'
            }
        )
        print("✅ Created PaymentIntent")
        
        # Use Stripe's test bank account numbers
        test_bank_account = {
            'routing_number': '110000000',  # Stripe test routing number
            'account_number': '000123456789',  # Stripe test account number
            'account_holder_name': f"{payer.first_name} {payer.last_name}",
            'account_type': 'checking'
        }
        
        # Create a PaymentMethod with the test bank account
        payment_method = stripe.PaymentMethod.create(
            type='us_bank_account',
            us_bank_account={
                'routing_number': test_bank_account['routing_number'],
                'account_number': test_bank_account['account_number'],
                'account_holder_type': 'individual',
                'account_type': test_bank_account['account_type']
            },
            billing_details={
                'name': test_bank_account['account_holder_name'],
                'email': payer.email
            }
        )
        print("✅ Created PaymentMethod with test bank account")
        
        # Instead of attaching to customer (which requires verification),
        # we'll use the payment method directly with the PaymentIntent
        print("✅ Using PaymentMethod directly with PaymentIntent (no customer attachment)")
        
        # Confirm the PaymentIntent with the bank account
        confirmed_payment = stripe.PaymentIntent.confirm(
            payment_intent.id,
            payment_method=payment_method.id
        )
        print("✅ Confirmed PaymentIntent")
        
        # Check if payment succeeded
        if confirmed_payment.status == 'succeeded':
            print("✅ Payment succeeded!")
            
            # Create bank account record in our database
            bank_account = BankAccount.objects.create(
                user=payer,
                nickname='Test Bank Account',
                account_type=test_bank_account['account_type'],
                last4=test_bank_account['account_number'][-4:],
                provider_token=f"{test_bank_account['routing_number']}_{test_bank_account['account_number']}",
                stripe_payment_method_id=payment_method.id
            )
            print("✅ Created bank account record")
            
            # Create payment record
            payment = Payment.objects.create(
                student=student,
                amount=payment_item.amount,
                status='completed',
                bank_account=bank_account,
                routing_number=test_bank_account['routing_number'],
                account_number=test_bank_account['account_number'],
                account_type=test_bank_account['account_type'],
                receipt_number=payment_intent.id
            )
            print("✅ Created payment record")
            
            # Mark payment item as paid
            payment_item.is_paid = True
            payment_item.save()
            print("✅ Marked payment item as paid")
            
            print(f"\n🎉 Bank account payment test completed successfully!")
            print(f"Payment ID: {payment_intent.id}")
            print(f"Amount: ${payment_item.amount}")
            print(f"Status: {confirmed_payment.status}")
            print(f"Bank Account: ****{test_bank_account['account_number'][-4:]}")
            
        elif confirmed_payment.status == 'requires_action':
            print("⚠️ Payment requires additional action")
            if confirmed_payment.next_action and confirmed_payment.next_action.type == 'verify_with_microdeposits':
                print("⚠️ Microdeposits verification required")
                print(f"Verification URL: {confirmed_payment.next_action.verify_with_microdeposits.hosted_verification_url}")
                print("\n💡 To complete this test, you would need to:")
                print("   1. Click the verification URL")
                print("   2. Enter the microdeposit amounts (32 and 45 cents)")
                print("   3. Complete the verification")
            else:
                print(f"Next action type: {confirmed_payment.next_action.type}")
        else:
            print(f"❌ Payment failed with status: {confirmed_payment.status}")
            if confirmed_payment.last_payment_error:
                print(f"Error: {confirmed_payment.last_payment_error.message}")
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_credit_card_payment():
    """Test credit card payment as an alternative"""
    print("\n=== Testing Credit Card Payment (Alternative) ===\n")
    
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
            description='Test Card Payment - $0.50',
            amount=0.50,
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
        
        # Use Stripe's test credit card
        payment_method = stripe.PaymentMethod.create(
            type='card',
            card={
                'number': '4242424242424242',  # Stripe test card
                'exp_month': 12,
                'exp_year': 2025,
                'cvc': '123'
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
            
        else:
            print(f"❌ Payment failed with status: {confirmed_payment.status}")
            if confirmed_payment.last_payment_error:
                print(f"Error: {confirmed_payment.last_payment_error.message}")
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    print("=== Stripe Payment Testing Suite ===\n")
    
    # Test bank account payment
    test_bank_account_payment_without_verification()
    
    # Test credit card payment as alternative
    test_credit_card_payment()
    
    print("\n" + "=" * 60)
    print("✅ Testing completed!")
    print("\n💡 Summary:")
    print("   • Bank account payments require verification in Stripe")
    print("   • Credit card payments work immediately for testing")
    print("   • For production, users will need to verify their bank accounts")
    print("   • The verification process involves microdeposits (32¢ and 45¢)") 