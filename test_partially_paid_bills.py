#!/usr/bin/env python
"""
Test script to investigate partially paid bills in payment breakdown
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

def test_partially_paid_bills():
    """Test how partially paid bills are handled in payment breakdown"""
    print("=" * 60)
    print("TESTING PARTIALLY PAID BILLS IN PAYMENT BREAKDOWN")
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
    
    total_amount_owed = 0
    
    for student in my_students:
        print(f"\n📚 Student: {student.first_name} {student.last_name}")
        
        # Get all payment breakdown items
        breakdown_items = student.payment_breakdowns.filter(due_date__isnull=False)
        print(f"   Total bills: {breakdown_items.count()}")
        
        # Get unpaid items (including partially paid)
        unpaid_items = [bill for bill in breakdown_items if not bill.is_fully_paid]
        print(f"   Unpaid bills (including partially paid): {len(unpaid_items)}")
        
        # Show details of each unpaid bill
        for bill in unpaid_items:
            print(f"   💰 Bill: {bill.description}")
            print(f"      Original Amount: ${bill.amount}")
            print(f"      Remaining Amount: ${bill.remaining_amount}")
            print(f"      Payment Status: {bill.payment_status}")
            print(f"      Is Fully Paid: {bill.is_fully_paid}")
            print(f"      Due Date: {bill.due_date}")
            print(f"      Late Date: {bill.late_date}")
            
            # Show payment items
            payment_items = bill.payment_items.all()
            if payment_items:
                print(f"      Payment Items:")
                for item in payment_items:
                    print(f"        - ${item.amount_paid} (Payment: {item.payment.receipt_number})")
            else:
                print(f"      No payment items")
            print()
        
        # Categorize bills like the payer_dashboard view does
        overdue_items = [bill for bill in unpaid_items if bill.late_date and bill.late_date < today]
        upcoming_items = [bill for bill in unpaid_items if bill.due_date and bill.due_date <= end_of_month]
        future_items = [bill for bill in unpaid_items if bill.due_date and bill.due_date > end_of_month]
        
        overdue_amount = sum(bill.remaining_amount for bill in overdue_items)
        upcoming_amount = sum(bill.remaining_amount for bill in upcoming_items)
        future_amount = sum(bill.remaining_amount for bill in future_items)
        
        print(f"   📊 Amount Breakdown:")
        print(f"      Overdue: ${overdue_amount:.2f} ({len(overdue_items)} items)")
        print(f"      Upcoming: ${upcoming_amount:.2f} ({len(upcoming_items)} items)")
        print(f"      Future: ${future_amount:.2f} ({len(future_items)} items)")
        print(f"      Total: ${overdue_amount + upcoming_amount + future_amount:.2f}")
        
        # Add to total
        student_total = overdue_amount + upcoming_amount + future_amount
        total_amount_owed += student_total
    
    print(f"\n💰 TOTAL AMOUNT OWED: ${total_amount_owed:.2f}")
    
    # Test the payer_dashboard view logic
    print(f"\n" + "=" * 60)
    print("TESTING PAYER_DASHBOARD VIEW LOGIC")
    print("=" * 60)
    
    # Simulate the payer_dashboard view calculation
    view_total_amount_owed = 0
    
    for student in my_students:
        breakdown_items = student.payment_breakdowns.filter(due_date__isnull=False)
        unpaid_items = [bill for bill in breakdown_items if not bill.is_fully_paid]
        
        overdue_items = [bill for bill in unpaid_items if bill.late_date and bill.late_date < today]
        upcoming_items = [bill for bill in unpaid_items if bill.due_date and bill.due_date <= end_of_month]
        future_items = [bill for bill in unpaid_items if bill.due_date and bill.due_date > end_of_month]
        
        overdue_amount = sum(bill.remaining_amount for bill in overdue_items)
        upcoming_amount = sum(bill.remaining_amount for bill in upcoming_items)
        future_amount = sum(bill.remaining_amount for bill in future_items)
        
        view_total_amount_owed += overdue_amount + upcoming_amount + future_amount
    
    print(f"View calculation total: ${view_total_amount_owed:.2f}")
    print(f"Manual calculation total: ${total_amount_owed:.2f}")
    print(f"Match: {'✅' if view_total_amount_owed == total_amount_owed else '❌'}")

if __name__ == "__main__":
    test_partially_paid_bills()
