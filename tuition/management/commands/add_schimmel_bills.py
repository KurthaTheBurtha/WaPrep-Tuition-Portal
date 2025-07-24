from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timedelta
import calendar
from decimal import Decimal
from tuition.models import Student, PaymentBreakdown


class Command(BaseCommand):
    help = 'Add bills for Kurt and Klara Schimmel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating bills',
        )
        parser.add_argument(
            '--months',
            type=int,
            default=6,
            help='Number of months of bills to create (default: 6)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        months = options['months']
        
        # Find Kurt and Klara Schimmel
        try:
            kurt = Student.objects.get(first_name='Kurt', last_name='Schimmel')
            klara = Student.objects.get(first_name='Klara', last_name='Schimmel')
        except Student.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Kurt or Klara Schimmel not found. Please ensure they exist in the database.')
            )
            return

        # Get current date info
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        self.stdout.write(f"Current date: {current_date.date()}")
        self.stdout.write(f"Creating bills for {months} months starting from {current_month}/{current_year}")

        bills_created = 0
        
        for month_offset in range(months):
            # Calculate month and year for this iteration
            month = current_month + month_offset
            year = current_year
            if month > 12:
                month = month - 12
                year += 1
            
            # Get last day of the month
            last_day = calendar.monthrange(year, month)[1]
            due_date = date(year, month, last_day)
            late_date = due_date + timedelta(days=15)  # 15 days grace period
            
            # Create bills for Kurt
            kurt_bills = [
                {
                    'student': kurt,
                    'description': f'{datetime(year, month, 1).strftime("%B %Y")} Tuition',
                    'amount': Decimal('500.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                },
                {
                    'student': kurt,
                    'description': f'{datetime(year, month, 1).strftime("%B %Y")} Lunch Program',
                    'amount': Decimal('120.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                },
                {
                    'student': kurt,
                    'description': f'{datetime(year, month, 1).strftime("%B %Y")} Activity Fee',
                    'amount': Decimal('50.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                }
            ]
            
            # Create bills for Klara
            klara_bills = [
                {
                    'student': klara,
                    'description': f'{datetime(year, month, 1).strftime("%B %Y")} Tuition',
                    'amount': Decimal('500.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                },
                {
                    'student': klara,
                    'description': f'{datetime(year, month, 1).strftime("%B %Y")} Art Program',
                    'amount': Decimal('80.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                },
                {
                    'student': klara,
                    'description': f'{datetime(year, month, 1).strftime("%B %Y")} Music Program',
                    'amount': Decimal('200.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                }
            ]
            
            # Add some special bills for specific months
            if month_offset == 0:  # Current month
                # Add some overdue bills for demonstration
                kurt_bills.append({
                    'student': kurt,
                    'description': 'Previous Month Tech Fee - Overdue',
                    'amount': Decimal('75.00'),
                    'due_date': due_date - timedelta(days=30),
                    'date_incurred': date(year, month-1 if month > 1 else 12, 1),
                    'late_date': due_date - timedelta(days=15),
                    'is_paid': False,
                    'show_in_payment_history': True
                })
                
                klara_bills.append({
                    'student': klara,
                    'description': 'Previous Month Art Supplies - Overdue',
                    'amount': Decimal('60.00'),
                    'due_date': due_date - timedelta(days=30),
                    'date_incurred': date(year, month-1 if month > 1 else 12, 1),
                    'late_date': due_date - timedelta(days=15),
                    'is_paid': False,
                    'show_in_payment_history': True
                })
            
            elif month_offset == 2:  # Third month
                # Add special one-time fees
                kurt_bills.append({
                    'student': kurt,
                    'description': 'Science Fair Registration Fee',
                    'amount': Decimal('150.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                })
                
                klara_bills.append({
                    'student': klara,
                    'description': 'Art Exhibition Materials',
                    'amount': Decimal('120.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                })
            
            elif month_offset == 4:  # Fifth month
                # Add field trip fees
                kurt_bills.append({
                    'student': kurt,
                    'description': 'Field Trip to Science Museum',
                    'amount': Decimal('85.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                })
                
                klara_bills.append({
                    'student': klara,
                    'description': 'Music Festival Trip',
                    'amount': Decimal('200.00'),
                    'due_date': due_date,
                    'date_incurred': date(year, month, 1),
                    'late_date': late_date,
                    'is_paid': False,
                    'show_in_payment_history': True
                })
            
            # Create all bills for this month
            all_bills = kurt_bills + klara_bills
            
            for bill_data in all_bills:
                if dry_run:
                    self.stdout.write(
                        f"Would create bill: {bill_data['student'].first_name} {bill_data['student'].last_name} - "
                        f"{bill_data['description']} - ${bill_data['amount']} - Due: {bill_data['due_date']} "
                        f"- Late: {bill_data['late_date']}"
                    )
                else:
                    # Check if this bill already exists
                    existing_bill = PaymentBreakdown.objects.filter(
                        student=bill_data['student'],
                        description=bill_data['description'],
                        due_date=bill_data['due_date']
                    ).first()
                    
                    if existing_bill:
                        self.stdout.write(
                            f"Skipping {bill_data['description']} for {bill_data['student'].first_name} "
                            f"{bill_data['student'].last_name} - already exists"
                        )
                        continue
                    
                    bill = PaymentBreakdown.objects.create(**bill_data)
                    bills_created += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created bill: {bill_data['student'].first_name} {bill_data['student'].last_name} - "
                            f"{bill_data['description']} - ${bill_data['amount']} - Due: {bill_data['due_date']}"
                        )
                    )

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\nDRY RUN: Would create bills for {months} months for Kurt and Klara Schimmel")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nSuccessfully created {bills_created} bills for Kurt and Klara Schimmel")
            )
            
            # Show summary by student
            self.stdout.write("\n" + "="*60)
            self.stdout.write("BILLS SUMMARY")
            self.stdout.write("="*60)
            
            for student in [kurt, klara]:
                student_bills = PaymentBreakdown.objects.filter(student=student).order_by('-due_date')
                unpaid_bills = student_bills.filter(is_paid=False)
                paid_bills = student_bills.filter(is_paid=True)
                
                total_unpaid = sum(bill.amount for bill in unpaid_bills)
                total_paid = sum(bill.amount for bill in paid_bills)
                
                self.stdout.write(f"\n{student.first_name} {student.last_name}:")
                self.stdout.write(f"  Total bills: {student_bills.count()}")
                self.stdout.write(f"  Unpaid bills: {unpaid_bills.count()} (${total_unpaid:.2f})")
                self.stdout.write(f"  Paid bills: {paid_bills.count()} (${total_paid:.2f})")
                
                # Show recent unpaid bills
                recent_unpaid = list(unpaid_bills[:5])
                if recent_unpaid:
                    self.stdout.write("  Recent unpaid bills:")
                    for bill in recent_unpaid:
                        status = "OVERDUE" if bill.is_overdue else "DUE"
                        self.stdout.write(f"    - {bill.description} (${bill.amount:.2f}) - {status}") 