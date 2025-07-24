from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from tuition.models import Student, Payment, PaymentBreakdown, PaymentItem, User
import uuid


class Command(BaseCommand):
    help = 'Add payments for Kurt and Klara Schimmel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating payments',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find Kurt and Klara Schimmel
        try:
            kurt = Student.objects.get(first_name='Kurt', last_name='Schimmel')
            klara = Student.objects.get(first_name='Klara', last_name='Schimmel')
        except Student.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Kurt or Klara Schimmel not found. Please ensure they exist in the database.')
            )
            return

        # Find a payer user (or create one if needed)
        payer = User.objects.filter(user_type='payer').first()
        if not payer:
            self.stdout.write(
                self.style.ERROR('No payer users found. Please create a payer user first.')
            )
            return

        self.stdout.write(f'Using payer: {payer.get_full_name()} ({payer.email})')

        # Define payments to create
        payments_data = [
            # Kurt's payments
            {
                'student': kurt,
                'amount': Decimal('500.00'),
                'payment_date': date(2025, 1, 15),
                'description': 'January Tuition Payment',
                'payment_method': 'credit card'
            },
            {
                'student': kurt,
                'amount': Decimal('120.00'),
                'payment_date': date(2025, 2, 1),
                'description': 'February Lunch Program Payment',
                'payment_method': 'bank transfer'
            },
            {
                'student': kurt,
                'amount': Decimal('75.00'),
                'payment_date': date(2025, 3, 10),
                'description': 'March Tech Fee Payment',
                'payment_method': 'cash'
            },
            {
                'student': kurt,
                'amount': Decimal('650.00'),
                'payment_date': date(2025, 4, 20),
                'description': 'April Tuition and Activity Fee Payment',
                'payment_method': 'credit card'
            },
            
            # Klara's payments
            {
                'student': klara,
                'amount': Decimal('500.00'),
                'payment_date': date(2025, 1, 10),
                'description': 'January Tuition Payment',
                'payment_method': 'credit card'
            },
            {
                'student': klara,
                'amount': Decimal('80.00'),
                'payment_date': date(2025, 2, 15),
                'description': 'February Art Supplies Payment',
                'payment_method': 'check'
            },
            {
                'student': klara,
                'amount': Decimal('200.00'),
                'payment_date': date(2025, 3, 5),
                'description': 'March Music Program Payment',
                'payment_method': 'bank transfer'
            },
            {
                'student': klara,
                'amount': Decimal('780.00'),
                'payment_date': date(2025, 4, 25),
                'description': 'April Tuition and Art Program Payment',
                'payment_method': 'credit card'
            }
        ]

        created_payments = []
        
        for payment_data in payments_data:
            if dry_run:
                self.stdout.write(
                    f"Would create payment: {payment_data['student'].first_name} {payment_data['student'].last_name} - "
                    f"${payment_data['amount']} on {payment_data['payment_date']} "
                    f"({payment_data['payment_method']}) - {payment_data['description']}"
                )
                continue

            # Create the payment
            payment = Payment.objects.create(
                student=payment_data['student'],
                payer=payer,
                amount=payment_data['amount'],
                payment_date=datetime.combine(payment_data['payment_date'], datetime.min.time()),
                status='completed',
                payment_method=payment_data['payment_method'],
                receipt_number=f"PAY-{uuid.uuid4().hex[:8].upper()}",
                notes=payment_data['description']
            )
            
            created_payments.append(payment)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created payment: {payment_data['student'].first_name} {payment_data['student'].last_name} - "
                    f"${payment_data['amount']} on {payment_data['payment_date']} "
                    f"({payment_data['payment_method']}) - Receipt: {payment.receipt_number}"
                )
            )

        if not dry_run and created_payments:
            # Create PaymentItem records to link payments to breakdown items
            self.stdout.write("\nCreating PaymentItem records...")
            
            for payment in created_payments:
                # Find unpaid breakdown items for this student around the payment date
                payment_month = payment.payment_date.month
                payment_year = payment.payment_date.year
                
                breakdown_items = PaymentBreakdown.objects.filter(
                    student=payment.student,
                    due_date__year=payment_year,
                    due_date__month=payment_month,
                    is_paid=False
                ).order_by('due_date')[:3]  # Limit to 3 items per payment
                
                if breakdown_items.exists():
                    # Calculate how much each item should be paid
                    total_items_amount = sum(item.amount for item in breakdown_items)
                    payment_amount = float(payment.amount)
                    
                    for item in breakdown_items:
                        if total_items_amount > 0:
                            # Calculate proportional amount for this item
                            item_amount = (item.amount / total_items_amount) * payment_amount
                            item_amount = round(item_amount, 2)
                        else:
                            item_amount = 0
                        
                        # Create PaymentItem record
                        PaymentItem.objects.create(
                            payment=payment,
                            breakdown_item=item,
                            amount_paid=item_amount
                        )
                        
                        # Mark the breakdown item as paid
                        item.is_paid = True
                        item.save()
                    
                    self.stdout.write(
                        f"  Created {breakdown_items.count()} PaymentItem records for payment {payment.receipt_number}"
                    )
                else:
                    # Create a generic breakdown item if none exist
                    generic_item = PaymentBreakdown.objects.create(
                        student=payment.student,
                        description=f"Tuition Payment - {payment.payment_date.strftime('%B %Y')}",
                        amount=payment.amount,
                        due_date=payment.payment_date.date(),
                        date_incurred=payment.payment_date.date(),
                        is_paid=True,
                        show_in_payment_history=True
                    )
                    
                    PaymentItem.objects.create(
                        payment=payment,
                        breakdown_item=generic_item,
                        amount_paid=payment.amount
                    )
                    
                    self.stdout.write(
                        f"  Created generic PaymentItem for payment {payment.receipt_number}"
                    )

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\nDRY RUN: Would create {len(payments_data)} payments for Kurt and Klara Schimmel")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nSuccessfully created {len(created_payments)} payments for Kurt and Klara Schimmel")
            )
            
            # Show summary by student
            self.stdout.write("\n" + "="*60)
            self.stdout.write("PAYMENT SUMMARY")
            self.stdout.write("="*60)
            
            for student in [kurt, klara]:
                student_payments = Payment.objects.filter(student=student).order_by('payment_date')
                total_amount = sum(p.amount for p in student_payments)
                
                self.stdout.write(f"\n{student.first_name} {student.last_name}:")
                self.stdout.write(f"  Total payments: {student_payments.count()}")
                self.stdout.write(f"  Total amount: ${total_amount:.2f}")
                
                for payment in student_payments:
                    self.stdout.write(f"    - ${payment.amount:.2f} on {payment.payment_date.date()} ({payment.payment_method})") 