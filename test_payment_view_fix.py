#!/usr/bin/env python
"""
Test script to verify that the payment view correctly includes partially paid bills
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

def test_payment_view_fix():
    """Test that the payment view correctly includes partially paid bills"""
    print("=" * 60)
    print("TESTING PAYMENT VIEW FIX FOR PARTIALLY PAID BILLS")
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
    print(f"Found {my_students.count()} students for this payer")
    
    for student in my_students:
        print(f"\n📚 Student: {student.first_name} {student.last_name}")
        
        # Test the old logic (is_paid=False)
        print("   🔍 Testing OLD logic (is_paid=False):")
        old_breakdown_items = PaymentBreakdown.objects.filter(
            student=student,
            is_paid=False
        ).order_by('due_date')
        
        old_unpaid_items = [bill for bill in old_breakdown_items if not bill.is_fully_paid]
        old_future_items = [bill for bill in old_unpaid_items if bill.due_date and bill.due_date > end_of_month]
        
        print(f"      Total unpaid bills: {len(old_unpaid_items)}")
        print(f"      Future items: {len(old_future_items)}")
        for bill in old_future_items:
            print(f"        - {bill.description}: ${bill.remaining_amount} ({bill.payment_status})")
        
        # Test the new logic (not is_fully_paid)
        print("   🔍 Testing NEW logic (not is_fully_paid):")
        new_breakdown_items = PaymentBreakdown.objects.filter(
            student=student
        ).order_by('due_date')
        new_unpaid_items = [bill for bill in new_breakdown_items if not bill.is_fully_paid]
        new_future_items = [bill for bill in new_unpaid_items if bill.due_date and bill.due_date > end_of_month]
        
        print(f"      Total unpaid bills: {len(new_unpaid_items)}")
        print(f"      Future items: {len(new_future_items)}")
        for bill in new_future_items:
            print(f"        - {bill.description}: ${bill.remaining_amount} ({bill.payment_status})")
        
        # Check for differences
        old_future_ids = {bill.id for bill in old_future_items}
        new_future_ids = {bill.id for bill in new_future_items}
        
        missing_in_old = new_future_ids - old_future_ids
        if missing_in_old:
            print("   ✅ FIX CONFIRMED: The following partially paid bills were missing in old logic:")
            for bill_id in missing_in_old:
                bill = next(bill for bill in new_future_items if bill.id == bill_id)
                print(f"        - {bill.description}: ${bill.remaining_amount} ({bill.payment_status})")
        else:
            print("   ℹ️  No differences found (all bills are fully unpaid)")
        
        # Calculate totals
        old_future_total = sum(bill.remaining_amount for bill in old_future_items)
        new_future_total = sum(bill.remaining_amount for bill in new_future_items)
        
        print(f"   💰 Future items totals:")
        print(f"      Old logic: ${old_future_total:.2f}")
        print(f"      New logic: ${new_future_total:.2f}")
        print(f"      Difference: ${new_future_total - old_future_total:.2f}")

if __name__ == "__main__":
    test_payment_view_fix()
