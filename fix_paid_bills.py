#!/usr/bin/env python
"""
Script to fix all existing bills that have payment_status_override='paid' 
but still have non-zero remaining_amount
"""
import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')
django.setup()

from tuition.models import Student, User, PaymentBreakdown, Payment, PaymentItem
from tuition.views import create_manual_payment_for_bill
from django.utils import timezone

def fix_paid_bills():
    """Fix all bills that have payment_status_override='paid' but non-zero remaining_amount"""
    print("=" * 60)
    print("FIXING PAID BILLS WITH NON-ZERO REMAINING AMOUNT")
    print("=" * 60)
    
    # Find all bills with payment_status_override='paid' but non-zero remaining_amount
    problematic_bills = []
    
    for bill in PaymentBreakdown.objects.all():
        if bill.payment_status_override == 'paid' and bill.remaining_amount > 0:
            problematic_bills.append(bill)
    
    print(f"Found {len(problematic_bills)} bills with payment_status_override='paid' but non-zero remaining amount")
    
    if not problematic_bills:
        print("No problematic bills found. All paid bills have correct remaining amounts.")
        return
    
    # Get or create an admin user for the manual payments
    try:
        admin_user = User.objects.filter(user_type='admin').first()
        if not admin_user:
            admin_user = User.objects.create_user(
                username="system_admin",
                email="system@example.com",
                password="systempass123",
                first_name="System",
                last_name="Admin",
                user_type="admin"
            )
            print(f"Created system admin user: {admin_user.first_name} {admin_user.last_name}")
        else:
            print(f"Using existing admin user: {admin_user.first_name} {admin_user.last_name}")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return
    
    # Fix each problematic bill
    fixed_count = 0
    error_count = 0
    
    for bill in problematic_bills:
        print(f"\nProcessing bill: {bill.description}")
        print(f"  Student: {bill.student.first_name} {bill.student.last_name}")
        print(f"  Amount: ${bill.amount}")
        print(f"  Current remaining amount: ${bill.remaining_amount}")
        print(f"  Payment status override: {bill.payment_status_override}")
        
        try:
            # Create manual payment for this bill
            manual_payment = create_manual_payment_for_bill(bill, bill.student, admin_user)
            
            if manual_payment:
                # Refresh the bill to get updated remaining_amount
                bill.refresh_from_db()
                print(f"  ✓ Created manual payment: ID {manual_payment.id}, Amount: ${manual_payment.amount}")
                print(f"  ✓ New remaining amount: ${bill.remaining_amount}")
                fixed_count += 1
            else:
                print(f"  ✗ Failed to create manual payment")
                error_count += 1
                
        except Exception as e:
            print(f"  ✗ Error processing bill: {e}")
            error_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("FIX SUMMARY")
    print("=" * 60)
    print(f"Total problematic bills: {len(problematic_bills)}")
    print(f"Successfully fixed: {fixed_count}")
    print(f"Errors: {error_count}")
    
    # Verify the fix
    print("\nVerifying fix...")
    remaining_problematic = []
    for bill in PaymentBreakdown.objects.filter(payment_status_override='paid'):
        if bill.remaining_amount > 0:
            remaining_problematic.append(bill)
    
    if remaining_problematic:
        print(f"⚠️  {len(remaining_problematic)} bills still have issues:")
        for bill in remaining_problematic:
            print(f"  - {bill.description}: ${bill.remaining_amount} remaining")
    else:
        print("✓ All paid bills now have $0.00 remaining amount!")
    
    print("\nFix completed!")

def show_bill_status():
    """Show current status of all bills"""
    print("=" * 60)
    print("CURRENT BILL STATUS")
    print("=" * 60)
    
    all_bills = PaymentBreakdown.objects.all().order_by('student__last_name', 'student__first_name', 'description')
    
    current_student = None
    for bill in all_bills:
        if current_student != bill.student:
            current_student = bill.student
            print(f"\nStudent: {bill.student.first_name} {bill.student.last_name}")
            print("-" * 40)
        
        status_icon = "✓" if bill.payment_status_override == 'paid' and bill.remaining_amount == 0 else "⚠️"
        print(f"{status_icon} {bill.description}: ${bill.amount} | Remaining: ${bill.remaining_amount} | Status: {bill.payment_status_override}")
    
    # Summary
    paid_bills = PaymentBreakdown.objects.filter(payment_status_override='paid')
    paid_with_zero = paid_bills.filter(remaining_amount=0).count()
    paid_with_remaining = paid_bills.filter(remaining_amount__gt=0).count()
    
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total bills: {PaymentBreakdown.objects.count()}")
    print(f"Paid bills: {paid_bills.count()}")
    print(f"  - With $0.00 remaining: {paid_with_zero}")
    print(f"  - With >$0.00 remaining: {paid_with_remaining}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_bill_status()
    else:
        fix_paid_bills()
