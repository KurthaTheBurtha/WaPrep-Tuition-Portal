from django.core.management.base import BaseCommand
from tuition.models import Payment, PaymentItem, PaymentBreakdown
from django.db import transaction
from decimal import Decimal

class Command(BaseCommand):
    help = 'Populate PaymentItem records for existing payments that don\'t have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all payments that don't have PaymentItem records
        payments_without_items = Payment.objects.filter(payment_items__isnull=True)
        
        if not payments_without_items.exists():
            self.stdout.write(
                self.style.SUCCESS('All payments already have PaymentItem records.')
            )
            return
        
        self.stdout.write(f"Found {payments_without_items.count()} payments without PaymentItem records.")
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made.")
        
        created_count = 0
        
        for payment in payments_without_items:
            # Get unpaid breakdown items for this student around the payment date
            # We'll look for items due in the same month as the payment
            payment_month = payment.payment_date.month
            payment_year = payment.payment_date.year
            
            breakdown_items = PaymentBreakdown.objects.filter(
                student=payment.student,
                due_date__year=payment_year,
                due_date__month=payment_month,
                is_paid=True  # These should be marked as paid
            )
            
            if not breakdown_items.exists():
                # If no specific breakdown items found, create a generic one
                if not dry_run:
                    with transaction.atomic():
                        PaymentItem.objects.create(
                            payment=payment,
                            breakdown_item=PaymentBreakdown.objects.create(
                                student=payment.student,
                                description=f"Tuition Payment - {payment.payment_date.strftime('%B %Y')}",
                                amount=payment.amount,
                                is_paid=True
                            ),
                            amount_paid=payment.amount
                        )
                created_count += 1
                self.stdout.write(f"Created generic PaymentItem for payment {payment.id}")
            else:
                # Create PaymentItem records for existing breakdown items
                total_items_amount = sum(item.amount for item in breakdown_items)
                
                if not dry_run:
                    with transaction.atomic():
                        for item in breakdown_items:
                            if total_items_amount > 0:
                                # Calculate proportional amount
                                item_amount = (item.amount / total_items_amount) * float(payment.amount)
                                item_amount = round(item_amount, 2)
                            else:
                                item_amount = 0
                            
                            PaymentItem.objects.create(
                                payment=payment,
                                breakdown_item=item,
                                amount_paid=item_amount
                            )
                            created_count += 1
                
                self.stdout.write(f"Created {breakdown_items.count()} PaymentItem records for payment {payment.id}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would create {created_count} PaymentItem records.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created {created_count} PaymentItem records.")
            ) 