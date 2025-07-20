from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from tuition.models import Student, PaymentBreakdown


class Command(BaseCommand):
    help = 'Add special one-time bills for specific students'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Special bills for different students
        special_bills = [
            # Kurt Schimmel - Special programs
            {
                'student_id': 7,
                'description': 'Fall Sports Program Registration',
                'amount': 150.00,
                'due_date': today + timedelta(days=30),
                'date_incurred': today,
                'late_date': today + timedelta(days=60),
                'is_paid': False
            },
            {
                'student_id': 7,
                'description': 'Science Fair Materials',
                'amount': 75.00,
                'due_date': today + timedelta(days=45),
                'date_incurred': today,
                'late_date': today + timedelta(days=75),
                'is_paid': False
            },
            
            # Klara Schimmel - Art and music programs
            {
                'student_id': 8,
                'description': 'Art Supplies Kit',
                'amount': 120.00,
                'due_date': today + timedelta(days=20),
                'date_incurred': today,
                'late_date': today + timedelta(days=50),
                'is_paid': False
            },
            {
                'student_id': 8,
                'description': 'Music Program Fee',
                'amount': 200.00,
                'due_date': today + timedelta(days=35),
                'date_incurred': today,
                'late_date': today + timedelta(days=65),
                'is_paid': False
            },
            
            # Tyler Jones - Technology fee
            {
                'student_id': 9,
                'description': 'Technology Lab Fee',
                'amount': 85.00,
                'due_date': today + timedelta(days=25),
                'date_incurred': today,
                'late_date': today + timedelta(days=55),
                'is_paid': False
            },
            
            # Mindy Watson - Field trip
            {
                'student_id': 18,
                'description': 'Field Trip to Science Museum',
                'amount': 45.00,
                'due_date': today + timedelta(days=15),
                'date_incurred': today,
                'late_date': today + timedelta(days=45),
                'is_paid': False
            },
            
            # Test Students - Various fees
            {
                'student_id': 19,
                'description': 'Library Book Replacement',
                'amount': 25.00,
                'due_date': today + timedelta(days=10),
                'date_incurred': today,
                'late_date': today + timedelta(days=40),
                'is_paid': False
            },
            {
                'student_id': 20,
                'description': 'Yearbook Fee',
                'amount': 35.00,
                'due_date': today + timedelta(days=40),
                'date_incurred': today,
                'late_date': today + timedelta(days=70),
                'is_paid': False
            },
            {
                'student_id': 21,
                'description': 'Graduation Cap and Gown',
                'amount': 65.00,
                'due_date': today + timedelta(days=50),
                'date_incurred': today,
                'late_date': today + timedelta(days=80),
                'is_paid': False
            },
            {
                'student_id': 22,
                'description': 'Senior Class Trip Deposit',
                'amount': 100.00,
                'due_date': today + timedelta(days=30),
                'date_incurred': today,
                'late_date': today + timedelta(days=60),
                'is_paid': False
            }
        ]
        
        bills_created = 0
        
        for bill_data in special_bills:
            try:
                student = Student.objects.get(id=bill_data['student_id'])
                
                # Check if this bill already exists
                existing_bill = PaymentBreakdown.objects.filter(
                    student=student,
                    description=bill_data['description'],
                    due_date=bill_data['due_date']
                ).first()
                
                if existing_bill:
                    self.stdout.write(
                        f"Skipping {bill_data['description']} for {student.first_name} {student.last_name} - already exists"
                    )
                    continue
                
                PaymentBreakdown.objects.create(
                    student=student,
                    description=bill_data['description'],
                    amount=bill_data['amount'],
                    due_date=bill_data['due_date'],
                    date_incurred=bill_data['date_incurred'],
                    late_date=bill_data['late_date'],
                    is_paid=bill_data['is_paid'],
                    show_in_payment_history=True
                )
                
                bills_created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {bill_data['description']} (${bill_data['amount']:.2f}) for {student.first_name} {student.last_name}"
                    )
                )
                
            except Student.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Student ID {bill_data['student_id']} not found")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating bill for student {bill_data['student_id']}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {bills_created} special bills")
        ) 