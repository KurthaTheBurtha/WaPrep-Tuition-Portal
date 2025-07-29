from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date
from tuition.models import PaymentBreakdown


class Command(BaseCommand):
    help = 'Remove all bills after November 2025'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        
        # Define the cutoff date: December 1, 2025
        cutoff_date = date(2025, 12, 1)
        
        # Find all bills with due_date after November 2025
        bills_to_delete = PaymentBreakdown.objects.filter(
            due_date__gte=cutoff_date
        ).order_by('due_date')
        
        # Also find bills with date_incurred after November 2025
        bills_by_incurred = PaymentBreakdown.objects.filter(
            date_incurred__gte=cutoff_date
        ).exclude(
            due_date__gte=cutoff_date
        ).order_by('date_incurred')
        
        # Combine both querysets
        all_bills_to_delete = list(bills_to_delete) + list(bills_by_incurred)
        
        if not all_bills_to_delete:
            self.stdout.write(
                self.style.SUCCESS('No bills found after November 2025.')
            )
            return
        
        # Show summary
        self.stdout.write("=" * 60)
        self.stdout.write("BILLS TO BE REMOVED (After November 2025)")
        self.stdout.write("=" * 60)
        
        total_amount = 0
        for bill in all_bills_to_delete:
            status = "PAID" if bill.is_fully_paid else "UNPAID"
            self.stdout.write(
                f"{bill.student.first_name} {bill.student.last_name} - "
                f"{bill.description} - ${bill.amount} - {status} - "
                f"Due: {bill.due_date} - Incurred: {bill.date_incurred}"
            )
            total_amount += bill.amount
        
        self.stdout.write("-" * 60)
        self.stdout.write(f"Total bills to remove: {len(all_bills_to_delete)}")
        self.stdout.write(f"Total amount: ${total_amount:,.2f}")
        self.stdout.write("=" * 60)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No bills were actually deleted.')
            )
            return
        
        # Confirm deletion
        if not confirm:
            self.stdout.write(
                self.style.WARNING('WARNING: This will permanently delete the bills listed above!')
            )
            response = input('Are you sure you want to proceed? (yes/no): ')
            if response.lower() not in ['yes', 'y']:
                self.stdout.write('Operation cancelled.')
                return
        
        # Delete the bills
        deleted_count = 0
        for bill in all_bills_to_delete:
            try:
                bill.delete()
                deleted_count += 1
                self.stdout.write(
                    f"Deleted: {bill.student.first_name} {bill.student.last_name} - "
                    f"{bill.description} - ${bill.amount}"
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error deleting bill {bill.id}: {str(e)}")
                )
        
        self.stdout.write("-" * 60)
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} bills after November 2025.')
        )
        
        # Show remaining bills
        remaining_bills = PaymentBreakdown.objects.count()
        self.stdout.write(f"Total bills remaining in system: {remaining_bills}") 