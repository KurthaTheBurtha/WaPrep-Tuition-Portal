import os
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Student, StudentPayer, PaymentBreakdown, Payment, BankAccount
from .bill_api import (
    get_session_id,
    create_vendor,
    create_bank_account,
    create_bill,
    pay_bill,
    get_payment_status,
    BillAPIError
)

User = get_user_model()

class BillAPITest(TestCase):
    def setUp(self):
        # Create test user (payer)
        self.payer = User.objects.create_user(
            username='testpayer',
            email='testpayer@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Payer',
            user_type='payer'
        )
        
        # Create test student
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            date_of_birth='2010-01-01',
            student_id='TEST001',
            grade='9'
        )
        
        # Link student to payer
        StudentPayer.objects.create(
            student=self.student,
            payer=self.payer,
            relationship='guardian'
        )
        
        # Create test bank account
        self.bank_account = BankAccount.objects.create(
            user=self.payer,
            nickname='Test Account',
            account_type='checking',
            last4='1234',
            provider_token='123456789_987654321'
        )
        
        # Create test payment breakdown items
        self.payment_items = []
        for i in range(2):
            item = PaymentBreakdown.objects.create(
                student=self.student,
                description=f'Test Payment Item {i+1}',
                amount=100.00,
                due_date=timezone.now().date(),
                is_paid=False
            )
            self.payment_items.append(item)

    def test_payment_process(self):
        """Test the complete payment process"""
        try:
            # Get BILL session
            session_id = get_session_id()
            self.assertIsNotNone(session_id, "Failed to get session ID")
            
            # Create vendor
            vendor_data = {
                "name": f"{self.payer.first_name} {self.payer.last_name}",
                "email": self.payer.email,
                "accountType": "PERSON",
                "phone": None,
                "address": {
                    "line1": None,
                    "city": "Seattle",
                    "zipOrPostalCode": "98101",
                    "country": "US"
                }
            }
            vendor_response = create_vendor(session_id, vendor_data)
            self.assertIn('id', vendor_response, "Failed to create vendor")
            vendor_id = vendor_response['id']
            
            # Create bank account
            bank_data = {
                "bankAccountNumber": "987654321",
                "routingNumber": "123456789",
                "accountType": "CHECKING",
                "bankAccountName": f"{self.payer.first_name} {self.payer.last_name}"
            }
            bank_response = create_bank_account(session_id, vendor_id, bank_data)
            self.assertIn('id', bank_response, "Failed to create bank account")
            
            # Create line items
            line_items = []
            for item in self.payment_items:
                line_items.append({
                    "amount": str(item.amount),
                    "description": item.description
                })
            
            # Create bill
            bill_data = {
                "amount": "200.00",
                "description": f"Test payment for {self.student.first_name} {self.student.last_name}",
                "invoiceNumber": f"TEST-{self.student.id}-{timezone.now().strftime('%Y%m%d')}",
                "dueDate": timezone.now().strftime('%Y-%m-%d'),
                "lineItems": line_items
            }
            bill_response = create_bill(session_id, vendor_id, bill_data)
            self.assertIn('id', bill_response, "Failed to create bill")
            bill_id = bill_response['id']
            
            # Process payment
            payment_response = pay_bill(session_id, bill_id)
            self.assertIn('id', payment_response, "Failed to process payment")
            payment_id = payment_response['id']
            
            # Check payment status
            status_response = get_payment_status(session_id, payment_id)
            self.assertIn('status', status_response, "Failed to get payment status")
            
            # Create payment record
            payment = Payment.objects.create(
                student=self.student,
                amount=200.00,
                status='pending',
                bank_account=self.bank_account,
                routing_number='123456789',
                account_number='987654321',
                account_type='checking',
                receipt_number=payment_id
            )
            
            # Mark payment items as paid
            for item in self.payment_items:
                item.is_paid = True
                item.save()
            
            # Verify payment items are marked as paid
            for item in self.payment_items:
                item.refresh_from_db()
                self.assertTrue(item.is_paid, f"Payment item {item.id} not marked as paid")
            
            print("✅ Payment process test completed successfully!")
            
        except BillAPIError as e:
            self.fail(f"BILL API Error: {str(e)}")
        except Exception as e:
            self.fail(f"Unexpected error: {str(e)}")

if __name__ == '__main__':
    import django
    django.setup()
    test = BillAPITest()
    test.setUp()
    test.test_payment_process()
