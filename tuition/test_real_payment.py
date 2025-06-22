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
from tuition.bill_api import (
    get_session_id,
    create_vendor,
    create_bank_account,
    create_bill,
    pay_bill,
    get_payment_status,
    BillAPIError
)

User = get_user_model()

def test_real_payment():
    """Test a real payment of $0.01"""
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
        
        # Create test bank account
        bank_account = BankAccount.objects.create(
            user=payer,
            nickname='Test Account',
            account_type='checking',
            last4='1234',
            provider_token='123456789_987654321'
        )
        print("✅ Created test bank account")
        
        # Create test payment breakdown item
        payment_item = PaymentBreakdown.objects.create(
            student=student,
            description='Test Payment - $0.01',
            amount=0.01,
            due_date=timezone.now().date(),
            is_paid=False
        )
        print("✅ Created test payment item")
        
        # Get BILL session
        session_id = get_session_id()
        print("✅ Got BILL session ID")
        
        # Create vendor with required fields
        vendor_data = {
            "name": f"{payer.first_name} {payer.last_name}",
            "email": payer.email,
            "accountType": "PERSON",
            "phone": "2065551234",  # Required field
            "address": {
                "line1": "123 Test St",
                "city": "Seattle",
                "state": "WA",
                "zipOrPostalCode": "98101",
                "country": "US"
            },
            "isActive": True,
            "vendorType": "PERSON"
        }
        vendor_response = create_vendor(session_id, vendor_data)
        vendor_id = vendor_response['id']
        print("✅ Created vendor in BILL")
        
        # Create bank account
        bank_data = {
            "bankAccountNumber": "987654321",
            "routingNumber": "123456789",
            "accountType": "CHECKING",
            "bankAccountName": f"{payer.first_name} {payer.last_name}"
        }
        bank_response = create_bank_account(session_id, vendor_id, bank_data)
        print("✅ Created bank account in BILL")
        
        # Create bill
        bill_data = {
            "amount": "0.01",
            "description": f"Test payment for {student.first_name} {student.last_name}",
            "invoiceNumber": f"TEST-{student.id}-{timezone.now().strftime('%Y%m%d')}",
            "dueDate": timezone.now().strftime('%Y-%m-%d'),
            "lineItems": [{
                "amount": "0.01",
                "description": "Test Payment - $0.01"
            }]
        }
        bill_response = create_bill(session_id, vendor_id, bill_data)
        bill_id = bill_response['id']
        print("✅ Created bill in BILL")
        
        # Process payment
        payment_response = pay_bill(session_id, bill_id)
        payment_id = payment_response['id']
        print("✅ Processed payment in BILL")
        
        # Check payment status
        status_response = get_payment_status(session_id, payment_id)
        print(f"✅ Payment status: {status_response.get('status')}")
        
        # Create payment record
        payment = Payment.objects.create(
            student=student,
            amount=0.01,
            status='pending',
            bank_account=bank_account,
            routing_number='123456789',
            account_number='987654321',
            account_type='checking',
            receipt_number=payment_id
        )
        print("✅ Created payment record in database")
        
        # Mark payment item as paid
        payment_item.is_paid = True
        payment_item.save()
        print("✅ Marked payment item as paid")
        
        print("\n✅ Payment process completed successfully!")
        print(f"Payment ID: {payment_id}")
        print(f"Amount: $0.01")
        print(f"Status: {status_response.get('status')}")
        
    except BillAPIError as e:
        print(f"❌ BILL API Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == '__main__':
    test_real_payment() 