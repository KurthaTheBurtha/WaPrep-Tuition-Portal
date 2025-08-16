#!/usr/bin/env python
"""
Test script to verify amount calculations are consistent between payer and admin views.
This script will help identify any discrepancies in how amounts are calculated.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')
django.setup()

from django.utils import timezone
from datetime import datetime, timedelta
import calendar
from tuition.models import Student, PaymentBreakdown, Payment, PaymentItem, User, StudentPayer

def test_amount_calculations():
    """Test amount calculations for consistency between payer and admin views"""
    
    print("=== Amount Calculation Consistency Test ===\n")
    
    # Get all students
    students = Student.objects.all()
    
    for student in students:
        print(f"Testing Student: {student.first_name} {student.last_name} (ID: {student.id})")
        print("-" * 60)
        
        # Get all bills for this student
        all_bills = PaymentBreakdown.objects.filter(student=student)
        
        if not all_bills.exists():
            print("No bills found for this student.\n")
            continue
        
        # Test 1: Verify remaining_amount calculations
        print("\n1. Testing remaining_amount calculations:")
        for bill in all_bills:
            # Calculate total paid manually
            total_paid_manual = PaymentItem.objects.filter(breakdown_item=bill).aggregate(
                total=models.Sum('amount_paid')
            )['total'] or Decimal('0.00')
            
            # Get the property value
            remaining_amount_property = bill.remaining_amount
            
            # Calculate expected remaining amount
            expected_remaining = max(bill.amount - total_paid_manual, Decimal('0.00'))
            
            if remaining_amount_property != expected_remaining:
                print(f"  ❌ BILL {bill.id} ({bill.description}):")
                print(f"     Amount: ${bill.amount}")
                print(f"     Total Paid: ${total_paid_manual}")
                print(f"     Expected Remaining: ${expected_remaining}")
                print(f"     Actual Remaining: ${remaining_amount_property}")
                print(f"     DIFFERENCE: ${expected_remaining - remaining_amount_property}")
            else:
                print(f"  ✅ BILL {bill.id} ({bill.description}): ${remaining_amount_property}")
        
        # Test 2: Verify payer view calculations (from payment view logic)
        print("\n2. Testing payer view calculations:")
        today = timezone.now().date()
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        # Calculate the last day of the current month
        last_day_of_month = calendar.monthrange(current_year, current_month)[1]
        end_of_month = datetime(current_year, current_month, last_day_of_month).date()
        
        # Get unpaid bills (payer view logic)
        unpaid_bills = PaymentBreakdown.objects.filter(
            student=student,
            is_paid=False
        ).order_by('due_date')
        
        # Categorize items (payer view logic)
        overdue_items = []
        current_month_items = []
        future_items = []
        
        for item in unpaid_bills:
            # Skip items with zero or negative remaining amounts
            if item.remaining_amount <= 0:
                continue
                
            if item.late_date and item.late_date < today:
                overdue_items.append(item)
            elif item.due_date <= end_of_month:
                current_month_items.append(item)
            else:
                future_items.append(item)
        
        # Calculate totals (payer view logic)
        overdue_total_payer = sum(item.remaining_amount for item in overdue_items)
        current_month_total_payer = sum(item.remaining_amount for item in current_month_items)
        future_total_payer = sum(item.remaining_amount for item in future_items)
        total_amount_due_payer = overdue_total_payer + current_month_total_payer + future_total_payer
        
        print(f"  Payer View Totals:")
        print(f"    Overdue: ${overdue_total_payer}")
        print(f"    Current Month: ${current_month_total_payer}")
        print(f"    Future: ${future_total_payer}")
        print(f"    Total Due: ${total_amount_due_payer}")
        
        # Test 3: Verify admin view calculations (from student_months view logic)
        print("\n3. Testing admin view calculations:")
        
        # Get all unpaid bills (admin view logic)
        unpaid_bills_admin = [bill for bill in all_bills if not bill.is_fully_paid]
        
        # Categorize bills by priority (admin view logic)
        overdue_items_admin = []
        current_month_items_admin = []
        future_items_admin = []
        
        for bill in unpaid_bills_admin:
            if bill.late_date and bill.late_date < today:
                overdue_items_admin.append(bill)
            elif bill.due_date <= end_of_month:
                current_month_items_admin.append(bill)
            else:
                future_items_admin.append(bill)
        
        # Calculate totals (admin view logic)
        overdue_total_admin = sum(bill.remaining_amount for bill in overdue_items_admin)
        current_month_total_admin = sum(bill.remaining_amount for bill in current_month_items_admin)
        future_total_admin = sum(bill.remaining_amount for bill in future_items_admin)
        total_amount_due_admin = overdue_total_admin + current_month_total_admin + future_total_admin
        
        print(f"  Admin View Totals:")
        print(f"    Overdue: ${overdue_total_admin}")
        print(f"    Current Month: ${current_month_total_admin}")
        print(f"    Future: ${future_total_admin}")
        print(f"    Total Due: ${total_amount_due_admin}")
        
        # Test 4: Compare payer vs admin calculations
        print("\n4. Comparing payer vs admin calculations:")
        
        if total_amount_due_payer != total_amount_due_admin:
            print(f"  ❌ DISCREPANCY FOUND!")
            print(f"     Payer Total Due: ${total_amount_due_payer}")
            print(f"     Admin Total Due: ${total_amount_due_admin}")
            print(f"     Difference: ${total_amount_due_payer - total_amount_due_admin}")
            
            # Analyze the difference
            print(f"  Analyzing differences:")
            print(f"    Payer overdue items: {len(overdue_items)}")
            print(f"    Admin overdue items: {len(overdue_items_admin)}")
            print(f"    Payer current month items: {len(current_month_items)}")
            print(f"    Admin current month items: {len(current_month_items_admin)}")
            print(f"    Payer future items: {len(future_items)}")
            print(f"    Admin future items: {len(future_items_admin)}")
            
            # Check for specific differences
            payer_bill_ids = {item.id for item in overdue_items + current_month_items + future_items}
            admin_bill_ids = {item.id for item in overdue_items_admin + current_month_items_admin + future_items_admin}
            
            if payer_bill_ids != admin_bill_ids:
                print(f"  Different bills included:")
                only_in_payer = payer_bill_ids - admin_bill_ids
                only_in_admin = admin_bill_ids - payer_bill_ids
                if only_in_payer:
                    print(f"    Only in payer view: {only_in_payer}")
                if only_in_admin:
                    print(f"    Only in admin view: {only_in_admin}")
        else:
            print(f"  ✅ Amounts match between payer and admin views")
        
        # Test 5: Verify payment status calculations
        print("\n5. Testing payment status calculations:")
        for bill in all_bills:
            is_fully_paid_property = bill.is_fully_paid
            payment_status_property = bill.payment_status
            
            # Manual calculation
            total_paid = PaymentItem.objects.filter(breakdown_item=bill).aggregate(
                total=models.Sum('amount_paid')
            )['total'] or Decimal('0.00')
            remaining_manual = max(bill.amount - total_paid, Decimal('0.00'))
            is_fully_paid_manual = remaining_manual <= Decimal('0.00')
            
            if is_fully_paid_property != is_fully_paid_manual:
                print(f"  ❌ BILL {bill.id}: is_fully_paid mismatch")
                print(f"     Property: {is_fully_paid_property}")
                print(f"     Manual: {is_fully_paid_manual}")
                print(f"     Amount: ${bill.amount}, Paid: ${total_paid}, Remaining: ${remaining_manual}")
        
        print("\n" + "=" * 60 + "\n")

def test_specific_student(student_id):
    """Test a specific student in detail"""
    try:
        student = Student.objects.get(id=student_id)
        print(f"=== Detailed Test for Student: {student.first_name} {student.last_name} ===\n")
        
        # Get all bills
        all_bills = PaymentBreakdown.objects.filter(student=student)
        
        print("All Bills:")
        for bill in all_bills:
            total_paid = PaymentItem.objects.filter(breakdown_item=bill).aggregate(
                total=models.Sum('amount_paid')
            )['total'] or Decimal('0.00')
            
            print(f"  Bill {bill.id}: {bill.description}")
            print(f"    Amount: ${bill.amount}")
            print(f"    Total Paid: ${total_paid}")
            print(f"    Remaining: ${bill.remaining_amount}")
            print(f"    Is Paid: {bill.is_paid}")
            print(f"    Is Fully Paid: {bill.is_fully_paid}")
            print(f"    Payment Status: {bill.payment_status}")
            print(f"    Payment Status Override: {bill.payment_status_override}")
            print(f"    Due Date: {bill.due_date}")
            print(f"    Late Date: {bill.late_date}")
            print()
        
        # Test payer view
        print("Payer View Calculation:")
        unpaid_bills = PaymentBreakdown.objects.filter(
            student=student,
            is_paid=False
        ).order_by('due_date')
        
        print(f"  Unpaid bills (is_paid=False): {unpaid_bills.count()}")
        for bill in unpaid_bills:
            print(f"    Bill {bill.id}: ${bill.remaining_amount}")
        
        # Test admin view
        print("\nAdmin View Calculation:")
        unpaid_bills_admin = [bill for bill in all_bills if not bill.is_fully_paid]
        print(f"  Unpaid bills (not is_fully_paid): {len(unpaid_bills_admin)}")
        for bill in unpaid_bills_admin:
            print(f"    Bill {bill.id}: ${bill.remaining_amount}")
        
    except Student.DoesNotExist:
        print(f"Student with ID {student_id} not found.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific student
        student_id = int(sys.argv[1])
        test_specific_student(student_id)
    else:
        # Test all students
        test_amount_calculations()
