from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import datetime, timedelta
from decimal import Decimal
from tuition.models import PaymentBreakdown, Student, Payment, PaymentItem
import csv
import os


class Command(BaseCommand):
    help = 'Manage bills with various operations like bulk creation, updates, and exports'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['create_monthly', 'mark_overdue', 'export_overdue', 'bulk_update', 'summary', 'test_remaining_amount', 'reset_and_create'],
            help='Action to perform'
        )
        parser.add_argument(
            '--month',
            type=str,
            help='Month for monthly bill creation (YYYY-MM format)'
        )
        parser.add_argument(
            '--amount',
            type=Decimal,
            help='Amount for bill creation'
        )
        parser.add_argument(
            '--description',
            type=str,
            help='Description for bill creation'
        )
        parser.add_argument(
            '--due-day',
            type=int,
            default=15,
            help='Day of month for due date (default: 15)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file for exports'
        )
        parser.add_argument(
            '--student-id',
            type=str,
            help='Specific student ID to process'
        )
        parser.add_argument(
            '--grade',
            type=str,
            help='Filter by student grade'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'create_monthly':
            self.create_monthly_bills(options)
        elif action == 'mark_overdue':
            self.mark_overdue_bills()
        elif action == 'export_overdue':
            self.export_overdue_bills(options)
        elif action == 'bulk_update':
            self.bulk_update_bills(options)
        elif action == 'summary':
            self.show_bill_summary()
        elif action == 'test_remaining_amount':
            self.test_remaining_amount()
        elif action == 'reset_and_create':
            self.reset_and_create_bills()

    def create_monthly_bills(self, options):
        """Create monthly bills for all active students"""
        month_str = options['month']
        amount = options['amount']
        description = options['description']
        due_day = options['due_day']
        
        if not month_str or not amount or not description:
            raise CommandError('Month, amount, and description are required for monthly bill creation')
        
        try:
            month_date = datetime.strptime(month_str, '%Y-%m').date()
        except ValueError:
            raise CommandError('Month must be in YYYY-MM format')
        
        # Get active students
        students = Student.objects.filter(status='active')
        if options['grade']:
            students = students.filter(grade=options['grade'])
        if options['student_id']:
            students = students.filter(student_id=options['student_id'])
        
        # Calculate due date
        due_date = month_date.replace(day=due_day)
        
        bills_created = 0
        for student in students:
            # Check if bill already exists for this month
            existing_bill = PaymentBreakdown.objects.filter(
                student=student,
                description__icontains=month_str,
                date_incurred__year=month_date.year,
                date_incurred__month=month_date.month
            ).first()
            
            if not existing_bill:
                bill = PaymentBreakdown.objects.create(
                    student=student,
                    description=f"{description} - {month_str}",
                    amount=amount,
                    due_date=due_date,
                    date_incurred=month_date,
                    is_paid=False,
                    show_in_payment_history=False
                )
                bills_created += 1
                self.stdout.write(f"Created bill for {student.first_name} {student.last_name}: ${amount}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {bills_created} monthly bills for {month_str}')
        )

    def mark_overdue_bills(self):
        """Mark bills as overdue based on late_date"""
        today = timezone.now().date()
        overdue_bills = PaymentBreakdown.objects.filter(
            is_paid=False,
            late_date__lt=today
        )
        
        count = overdue_bills.count()
        self.stdout.write(f"Found {count} overdue bills")
        
        for bill in overdue_bills:
            self.stdout.write(f"Overdue: {bill.student.first_name} {bill.student.last_name} - {bill.description} (${bill.amount}) - {bill.days_overdue} days overdue")

    def export_overdue_bills(self, options):
        """Export overdue bills to CSV"""
        today = timezone.now().date()
        overdue_bills = PaymentBreakdown.objects.filter(
            is_paid=False,
            late_date__lt=today
        ).select_related('student')
        
        output_file = options['output'] or f'overdue_bills_{today}.csv'
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Student ID', 'Student Name', 'Grade', 'Description', 'Amount', 'Remaining Amount',
                'Due Date', 'Late Date', 'Days Overdue', 'Date Incurred', 'Payment Status'
            ])
            
            for bill in overdue_bills:
                writer.writerow([
                    bill.student.student_id,
                    f"{bill.student.first_name} {bill.student.last_name}",
                    bill.student.grade,
                    bill.description,
                    bill.amount,
                    bill.remaining_amount,
                    bill.due_date,
                    bill.late_date,
                    bill.days_overdue,
                    bill.date_incurred,
                    bill.payment_status
                ])
        
        self.stdout.write(
            self.style.SUCCESS(f'Exported {overdue_bills.count()} overdue bills to {output_file}')
        )

    def bulk_update_bills(self, options):
        """Bulk update bill properties"""
        # This is a placeholder for bulk update functionality
        self.stdout.write("Bulk update functionality not yet implemented")

    def show_bill_summary(self):
        """Show summary of all bills"""
        total_bills = PaymentBreakdown.objects.count()
        paid_bills = PaymentBreakdown.objects.filter(is_paid=True).count()
        unpaid_bills = PaymentBreakdown.objects.filter(is_paid=False).count()
        
        today = timezone.now().date()
        overdue_bills = PaymentBreakdown.objects.filter(
            is_paid=False,
            late_date__lt=today
        ).count()
        
        total_amount = PaymentBreakdown.objects.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        paid_amount = PaymentBreakdown.objects.filter(is_paid=True).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        unpaid_amount = PaymentBreakdown.objects.filter(is_paid=False).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Calculate total remaining amount
        total_remaining = sum(bill.remaining_amount for bill in PaymentBreakdown.objects.all())
        
        self.stdout.write("=" * 50)
        self.stdout.write("BILL SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total Bills: {total_bills}")
        self.stdout.write(f"Paid Bills: {paid_bills}")
        self.stdout.write(f"Unpaid Bills: {unpaid_bills}")
        self.stdout.write(f"Overdue Bills: {overdue_bills}")
        self.stdout.write("-" * 30)
        self.stdout.write(f"Total Amount: ${total_amount:,.2f}")
        self.stdout.write(f"Paid Amount: ${paid_amount:,.2f}")
        self.stdout.write(f"Unpaid Amount: ${unpaid_amount:,.2f}")
        self.stdout.write(f"Total Remaining: ${total_remaining:,.2f}")
        self.stdout.write("=" * 50)

    def test_remaining_amount(self):
        """Test the remaining amount calculation for bills"""
        self.stdout.write("Testing remaining amount calculations...")
        self.stdout.write("=" * 50)
        
        bills = PaymentBreakdown.objects.select_related('student').prefetch_related('payment_items')
        
        for bill in bills:
            self.stdout.write(f"Bill: {bill.description}")
            self.stdout.write(f"  Student: {bill.student.first_name} {bill.student.last_name}")
            self.stdout.write(f"  Amount: ${bill.amount}")
            self.stdout.write(f"  Remaining Amount: ${bill.remaining_amount}")
            self.stdout.write(f"  Payment Status: {bill.payment_status}")
            self.stdout.write(f"  Is Fully Paid: {bill.is_fully_paid}")
            
            # Show payment items
            payment_items = bill.payment_items.all()
            if payment_items:
                self.stdout.write(f"  Payment Items:")
                for item in payment_items:
                    self.stdout.write(f"    - ${item.amount_paid} (Payment: {item.payment.receipt_number})")
            else:
                self.stdout.write(f"  No payment items")
            
            self.stdout.write("-" * 30) 

    def reset_and_create_bills(self):
        """Remove all current bills and create new ones"""
        self.stdout.write("=" * 50)
        self.stdout.write("RESETTING AND CREATING NEW BILLS")
        self.stdout.write("=" * 50)
        
        # First, show current bill count
        current_bills = PaymentBreakdown.objects.count()
        self.stdout.write(f"Current bills in system: {current_bills}")
        
        if current_bills > 0:
            # Confirm deletion
            self.stdout.write(self.style.WARNING("WARNING: This will delete ALL existing bills!"))
            self.stdout.write("Deleting all current bills...")
            
            # Delete all PaymentBreakdown objects (this will cascade to PaymentItems)
            deleted_count = PaymentBreakdown.objects.all().delete()[0]
            self.stdout.write(f"Deleted {deleted_count} bills and related records")
        
        # Get all active students
        students = Student.objects.filter(status='active')
        self.stdout.write(f"Found {students.count()} active students")
        
        # Create new bills for the 2025-2026 school year
        # Monthly tuition bills from September 2025 to May 2026
        monthly_tuition = Decimal('1200.00')
        months = [
            ('2025-09', 'September 2025 Tuition', 15),
            ('2025-10', 'October 2025 Tuition', 15),
            ('2025-11', 'November 2025 Tuition', 15),
            ('2025-12', 'December 2025 Tuition', 15),
            ('2026-01', 'January 2026 Tuition', 15),
            ('2026-02', 'February 2026 Tuition', 15),
            ('2026-03', 'March 2026 Tuition', 15),
            ('2026-04', 'April 2026 Tuition', 15),
            ('2026-05', 'May 2026 Tuition', 15),
        ]
        
        bills_created = 0
        
        for student in students:
            self.stdout.write(f"Creating bills for {student.first_name} {student.last_name} ({student.grade})")
            
            for month_str, description, due_day in months:
                try:
                    month_date = datetime.strptime(month_str, '%Y-%m').date()
                    due_date = month_date.replace(day=due_day)
                    
                    # Create the bill
                    bill = PaymentBreakdown.objects.create(
                        student=student,
                        description=description,
                        amount=monthly_tuition,
                        due_date=due_date,
                        date_incurred=month_date,
                        is_paid=False,
                        show_in_payment_history=False
                    )
                    bills_created += 1
                    self.stdout.write(f"  Created: {description} - ${monthly_tuition} (Due: {due_date})")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error creating bill for {month_str}: {str(e)}"))
            
            # Add some additional fees for variety
            additional_fees = [
                ('2025-09-01', 'Registration Fee', Decimal('150.00'), 15),
                ('2025-10-01', 'Technology Fee', Decimal('75.00'), 15),
                ('2025-11-01', 'Activity Fee', Decimal('50.00'), 15),
                ('2026-01-01', 'Materials Fee', Decimal('100.00'), 15),
                ('2026-03-01', 'Spring Activity Fee', Decimal('75.00'), 15),
            ]
            
            for fee_date_str, fee_description, fee_amount, fee_due_day in additional_fees:
                try:
                    fee_date = datetime.strptime(fee_date_str, '%Y-%m-%d').date()
                    fee_due_date = fee_date.replace(day=fee_due_day)
                    
                    bill = PaymentBreakdown.objects.create(
                        student=student,
                        description=fee_description,
                        amount=fee_amount,
                        due_date=fee_due_date,
                        date_incurred=fee_date,
                        is_paid=False,
                        show_in_payment_history=False
                    )
                    bills_created += 1
                    self.stdout.write(f"  Created: {fee_description} - ${fee_amount} (Due: {fee_due_date})")
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error creating fee {fee_description}: {str(e)}"))
        
        self.stdout.write("=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Successfully created {bills_created} new bills"))
        self.stdout.write("=" * 50)
        
        # Show summary of new bills
        self.show_bill_summary() 