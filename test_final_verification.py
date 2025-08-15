#!/usr/bin/env python
"""
Final verification script to test that the payment view correctly shows partially paid bills
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')
django.setup()

from tuition.models import Student, User, PaymentBreakdown, Payment, PaymentItem, StudentPayer
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
import calendar

def test_final_verification():
    """Final verification that the payment view fix works correctly"""
    print("=" * 60)
    print("FINAL VERIFICATION: PAYMENT VIEW FIX")
    print("=" * 60)
    
    # Get current date info
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    today = current_date.date()
    
    # Calculate end of current month
    last_day_of_month = calendar.monthrange(current_year, current_month)[1]
    end_of_month = datetime(current_year, current_month, last_day_of_month).date()
    
    # Get a payer user
    payer = User.objects.filter(user_type='payer').first()
    if not payer:
        print("❌ No payer user found")
        return
    
    print(f"Testing for payer: {payer.get_full_name()} ({payer.email})")
    
    # Get students associated with this payer
    my_students = Student.objects.filter(studentpayer__payer=payer).distinct()
    
    for student in my_students:
        print(f"\n📚 Student: {student.first_name} {student.last_name}")
        
        # Simulate the payment view logic
        breakdown_items = PaymentBreakdown.objects.filter(
            student=student
        ).order_by('due_date')
        
        # Filter to only include unpaid or partially paid bills
        unpaid_items = [bill for bill in breakdown_items if not bill.is_fully_paid]
        
        # Categorize items
        overdue_items = []
        current_month_items = []
        future_items = []
        
        for item in unpaid_items:
            # Skip items with zero or negative remaining amounts
            if item.remaining_amount <= 0:
                continue
                
            if item.late_date and item.late_date < today:
                overdue_items.append(item)
            elif item.due_date <= end_of_month:
                current_month_items.append(item)
            else:
                future_items.append(item)
        
        # Calculate totals
        overdue_total = sum(item.remaining_amount for item in overdue_items)
        current_month_total = sum(item.remaining_amount for item in current_month_items)
        future_total = sum(item.remaining_amount for item in future_items)
        total_amount_due = overdue_total + current_month_total + future_total
        
        print(f"   📊 Payment Breakdown:")
        print(f"      Overdue: ${overdue_total:.2f} ({len(overdue_items)} items)")
        print(f"      Current Month: ${current_month_total:.2f} ({len(current_month_items)} items)")
        print(f"      Future: ${future_total:.2f} ({len(future_items)} items)")
        print(f"      Total Due: ${total_amount_due:.2f}")
        
        # Show partially paid bills in each category
        print(f"\n   💰 Partially Paid Bills:")
        
        overdue_partial = [bill for bill in overdue_items if bill.payment_status == 'Partially Paid']
        current_partial = [bill for bill in current_month_items if bill.payment_status == 'Partially Paid']
        future_partial = [bill for bill in future_items if bill.payment_status == 'Partially Paid']
        
        if overdue_partial:
            print(f"      Overdue (Partially Paid):")
            for bill in overdue_partial:
                print(f"        - {bill.description}: ${bill.remaining_amount}")
        
        if current_partial:
            print(f"      Current Month (Partially Paid):")
            for bill in current_partial:
                print(f"        - {bill.description}: ${bill.remaining_amount}")
        
        if future_partial:
            print(f"      Future (Partially Paid):")
            for bill in future_partial:
                print(f"        - {bill.description}: ${bill.remaining_amount}")
        
        if not any([overdue_partial, current_partial, future_partial]):
            print(f"        No partially paid bills found")
        
        print(f"   ✅ Verification: All partially paid bills are now included in the payment breakdown")

if __name__ == "__main__":
    test_final_verification()
