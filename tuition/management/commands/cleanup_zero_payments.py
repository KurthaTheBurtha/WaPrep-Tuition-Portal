from django.core.management.base import BaseCommand
from django.db import transaction
from tuition.models import Payment, PaymentItem


class Command(BaseCommand):
    help = 'Identify and delete payments with $0 amount'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Actually delete the $0 payments',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete = options['delete']

        # Find all payments with $0 amount
        zero_payments = Payment.objects.filter(amount=0)
        count = zero_payments.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No $0 payments found in the database.')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {count} payment(s) with $0 amount:')
        )

        for payment in zero_payments:
            self.stdout.write(
                f'  - Payment ID: {payment.id}, Student: {payment.student}, '
                f'Date: {payment.payment_date}, Status: {payment.status}, '
                f'Receipt: {payment.receipt_number}'
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} payment(s) with $0 amount.'
                )
            )
            return

        if not delete:
            self.stdout.write(
                self.style.ERROR(
                    'Use --delete flag to actually delete these payments, '
                    'or --dry-run to see what would be deleted.'
                )
            )
            return

        # Check for associated PaymentItem records
        payments_with_items = []
        for payment in zero_payments:
            payment_items = PaymentItem.objects.filter(payment=payment)
            if payment_items.exists():
                payments_with_items.append(payment)
                self.stdout.write(
                    f'  - Payment {payment.id} has {payment_items.count()} PaymentItem records'
                )

        if payments_with_items:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {len(payments_with_items)} payment(s) with associated PaymentItem records. '
                    'These will also be deleted.'
                )
            )

        # Confirm deletion
        confirm = input(f'Are you sure you want to delete {count} payment(s)? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR('Deletion cancelled.'))
            return

        # Delete the payments
        with transaction.atomic():
            deleted_count = zero_payments.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} payment(s) with $0 amount.'
                )
            ) 