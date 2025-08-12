from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .decorators import admin_required, payer_required
from django.utils import timezone
from datetime import datetime, timedelta, date
from .models import User, Student, Payment, StudentPayer, BankAccount, PaymentBreakdown, Card, PaymentItem, PasswordReset, AccountRequest
import random
import string
from django.core.mail import send_mail
from django.db import models
from .forms import AccountRequestForm
from django.conf import settings
from django.db.models import Sum
from decouple import config
from .bill_api import (
    get_session_id,
    create_vendor,
    create_bank_account,
    create_bill,
    pay_bill
)
import stripe
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from django.views.decorators.http import require_POST
from .forms import PayerProfileForm, EditPayerProfileForm, QuestionForm
from .utils import validate_password, generate_strong_password, clear_messages
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
import calendar
import logging
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.urls import reverse
from django.db import transaction

# Configure logging
logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.

def home(request):
    return render(request, 'select_login.html', {'show_navbar': False})

def payer_login(request):
    if request.method == 'POST':
        user_id = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            user = None
        if user and user.check_password(password) and user.user_type == 'payer':
            login(request, user)
            if not remember:
                request.session.set_expiry(0)  # Session expires when browser closes
            # If using temp password, force password change
            if user.check_password(password) and len(password) >= 16:  # temp passwords are long
                request.session['force_password_change'] = True
            return redirect('payer_welcome')
        else:
            messages.error(request, 'Invalid User ID or password for payer account.')
    return render(request, 'payer_login.html', {'hide_nav_items': True})



def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password) and user.user_type == 'admin':
                login(request, user)
                
                if not remember:
                    request.session.set_expiry(0)  # Session expires when browser closes
                
                return redirect('students')  # Redirect to students page
            else:
                messages.error(request, 'Invalid email or password for admin account.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password for admin account.')
    
    return render(request, 'admin_login.html', {'hide_nav_items': True})

def logout_view(request):
    logout(request)
    clear_messages(request)  # Clear any existing messages
    return redirect('home')

@require_POST
def ajax_logout(request):
    """AJAX endpoint for automatic logout due to inactivity"""
    logout(request)
    return JsonResponse({'status': 'success', 'message': 'Logged out due to inactivity'})

@login_required
def payment(request, student_id):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Check if the current user is authorized to pay for this student
    if not StudentPayer.objects.filter(student=student, payer=request.user).exists():
        messages.error(request, 'You are not authorized to make payments for this student.')
        return redirect('payer_dashboard')
    
    # Check for specific bill_id, month, overdue, or all_bills parameters
    bill_id = request.GET.get('bill_id')
    month_param = request.GET.get('month')
    overdue_param = request.GET.get('overdue')
    all_bills_param = request.GET.get('all_bills')
    
    if bill_id:
        # Show specific bill
        try:
            breakdown_items = PaymentBreakdown.objects.filter(
                id=bill_id,
                student=student,
                is_paid=False
            ).order_by('due_date')
        except PaymentBreakdown.DoesNotExist:
            breakdown_items = PaymentBreakdown.objects.none()
    elif month_param:
        # Show all unpaid bills for specific month
        try:
            year, month = month_param.split('-')
            year = int(year)
            month = int(month)
            
            from datetime import date, timedelta
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)
            
            breakdown_items = PaymentBreakdown.objects.filter(
                student=student,
                is_paid=False,
                due_date__gte=first_day,
                due_date__lte=last_day
            ).order_by('due_date')
        except (ValueError, IndexError):
            breakdown_items = PaymentBreakdown.objects.none()
    elif overdue_param:
        # Show all overdue bills
        today = timezone.now().date()
        breakdown_items = PaymentBreakdown.objects.filter(
            student=student,
            is_paid=False,
            late_date__lt=today
        ).order_by('due_date')
    elif all_bills_param:
        # Show all unpaid bills
        breakdown_items = PaymentBreakdown.objects.filter(
            student=student,
            is_paid=False
        ).order_by('due_date')
    else:
        # Default: show all unpaid bills (so we can categorize them properly)
        breakdown_items = PaymentBreakdown.objects.filter(
            student=student,
            is_paid=False
        ).order_by('due_date')
    
    # Categorize breakdown items
    from datetime import datetime, timedelta
    import calendar
    
    today = timezone.now().date()
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    
    # Calculate the last day of the current month
    last_day_of_month = calendar.monthrange(current_year, current_month)[1]
    end_of_month = datetime(current_year, current_month, last_day_of_month).date()
    
    # Categorize items (exclude items with zero or negative remaining amounts)
    overdue_items = []
    current_month_items = []
    future_items = []
    
    for item in breakdown_items:
        # Skip items with zero or negative remaining amounts
        if item.remaining_amount <= 0:
            continue
            
        if item.late_date and item.late_date < today:
            overdue_items.append(item)
        elif item.due_date <= end_of_month:
            current_month_items.append(item)
        else:
            future_items.append(item)
    
    # Calculate totals for each category using remaining amounts
    overdue_total = sum(item.remaining_amount for item in overdue_items)
    current_month_total = sum(item.remaining_amount for item in current_month_items)
    future_total = sum(item.remaining_amount for item in future_items)
    
    total_amount_due = overdue_total + current_month_total + future_total
    
    # Stripe integration
    stripe_publishable_key = settings.STRIPE_PUBLISHABLE_KEY
    customer_id = get_or_create_stripe_customer(request.user)
    
    # Create a PaymentIntent for the amount due (convert to cents)
    if total_amount_due > 0:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(total_amount_due * 100),
            currency='usd',
            customer=customer_id,
            setup_future_usage='off_session',
            payment_method_types=['card', 'us_bank_account'],
            metadata={
                'student_id': student_id,
                'user_id': request.user.id
            }
        )
        client_secret = payment_intent.client_secret
    else:
        client_secret = None
    
    # Determine what we're paying for
    if bill_id:
        payment_description = f"Payment for specific bill"
    elif month_param:
        try:
            year, month = month_param.split('-')
            year = int(year)
            month = int(month)
            from datetime import date, timedelta
            first_day = date(year, month, 1)
            payment_description = f"Payment for {first_day.strftime('%B %Y')}"
        except (ValueError, IndexError):
            payment_description = "Payment for selected items"
    elif overdue_param:
        payment_description = "Payment for overdue bills"
    elif all_bills_param:
        payment_description = "Payment for all unpaid bills"
    else:
        payment_description = "Payment for bills due by end of month"
    
    # Prepare bill data for JavaScript using remaining amounts
    import json
    overdue_items_json = json.dumps([{
        'id': item.id,
        'description': item.description,
        'amount': float(item.remaining_amount),
        'due_date': item.due_date.isoformat(),
        'late_date': item.late_date.isoformat() if item.late_date else None
    } for item in overdue_items])
    
    current_month_items_json = json.dumps([{
        'id': item.id,
        'description': item.description,
        'amount': float(item.remaining_amount),
        'due_date': item.due_date.isoformat(),
        'late_date': item.late_date.isoformat() if item.late_date else None
    } for item in current_month_items])
    
    future_items_json = json.dumps([{
        'id': item.id,
        'description': item.description,
        'amount': float(item.remaining_amount),
        'due_date': item.due_date.isoformat(),
        'late_date': item.late_date.isoformat() if item.late_date else None
    } for item in future_items])
    
    context = {
        'student_name': f"{student.first_name} {student.last_name}",
        'total_amount_due': total_amount_due,
        'breakdown_items': breakdown_items,
        'overdue_items': overdue_items,
        'current_month_items': current_month_items,
        'future_items': future_items,
        'overdue_items_json': overdue_items_json,
        'current_month_items_json': current_month_items_json,
        'future_items_json': future_items_json,
        'overdue_total': overdue_total,
        'current_month_total': current_month_total,
        'future_total': future_total,
        'student_id': student_id,
        'payment_description': payment_description,
        'STRIPE_PUBLISHABLE_KEY': stripe_publishable_key,
        'STRIPE_CLIENT_SECRET': client_secret,
        'bill_id': bill_id,
        'month_param': month_param,
        'overdue_param': overdue_param,
        'all_bills_param': all_bills_param,
    }
    return render(request, 'payment.html', context)

@login_required
@require_POST
def process_payment(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        amount = request.POST.get('amount')
        payment_intent_id = request.POST.get('payment_intent_id')
        saved_payment_method_id = request.POST.get('saved_payment_method_id')
        
        # Enhanced validation for amount
        try:
            amount_float = float(amount) if amount else 0
        except (ValueError, TypeError):
            amount_float = 0
        
        # Validate amount is greater than 0
        if not amount or amount_float <= 0:
            messages.error(request, 'Payment amount must be greater than $0.')
            return redirect('payer_dashboard')
        
        # Additional safety check - ensure amount is reasonable
        if amount_float > 100000:  # $100,000 limit
            messages.error(request, 'Payment amount exceeds maximum allowed limit.')
            return redirect('payer_dashboard')
        
        try:
            # Handle saved payment method
            if saved_payment_method_id:
                # Extract the actual payment method ID
                if saved_payment_method_id.startswith('saved_method_'):
                    actual_payment_method_id = saved_payment_method_id.replace('saved_method_', '')
                else:
                    actual_payment_method_id = saved_payment_method_id
                
                # Create a PaymentIntent using the saved payment method
                customer_id = get_or_create_stripe_customer(request.user)
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(amount_float * 100),  # Use validated amount
                    currency='usd',
                    customer=customer_id,
                    payment_method=actual_payment_method_id,
                    confirm=True,
                    off_session=True,
                    metadata={
                        'student_id': student_id,
                        'user_id': request.user.id
                    }
                )
                
                payment_intent_id = payment_intent.id
            else:
                # Handle new payment method
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Get payment method details for all payment statuses
            pm = stripe.PaymentMethod.retrieve(payment_intent.payment_method)
            payment_method_type = pm.type
            
            # Check if payment was successful
            if payment_intent.status == 'succeeded':
                # Payment was successful, now create database records
                
                # Get the bills that were actually being paid for
                # This should match the same filtering logic as the payment view
                bill_id = request.POST.get('bill_id')
                month_param = request.POST.get('month')
                overdue_param = request.POST.get('overdue')
                all_bills_param = request.POST.get('all_bills')
                
                if bill_id:
                    # Specific bill payment
                    payment_items = PaymentBreakdown.objects.filter(
                        id=bill_id,
                        student=student,
                        is_paid=False
                    )
                elif month_param:
                    # Month payment
                    try:
                        year, month = month_param.split('-')
                        year = int(year)
                        month = int(month)
                        
                        from datetime import date, timedelta
                        first_day = date(year, month, 1)
                        if month == 12:
                            last_day = date(year + 1, 1, 1) - timedelta(days=1)
                        else:
                            last_day = date(year, month + 1, 1) - timedelta(days=1)
                        
                        payment_items = PaymentBreakdown.objects.filter(
                            student=student,
                            is_paid=False,
                            due_date__gte=first_day,
                            due_date__lte=last_day
                        )
                    except (ValueError, IndexError):
                        payment_items = PaymentBreakdown.objects.none()
                elif overdue_param:
                    # Overdue payment
                    today = timezone.now().date()
                    payment_items = PaymentBreakdown.objects.filter(
                        student=student,
                        is_paid=False,
                        late_date__lt=today
                    )
                elif all_bills_param:
                    # All unpaid bills payment
                    payment_items = PaymentBreakdown.objects.filter(
                        student=student,
                        is_paid=False
                    )
                else:
                    # Default: bills due by end of current month
                    from datetime import datetime, timedelta
                    import calendar
                    
                    current_date = datetime.now()
                    current_month = current_date.month
                    current_year = current_date.year
                    today = current_date.date()
                    
                    # Calculate the last day of the current month
                    last_day_of_month = calendar.monthrange(current_year, current_month)[1]
                    end_of_month = datetime(current_year, current_month, last_day_of_month).date()
                    
                    payment_items = PaymentBreakdown.objects.filter(
                        student=student,
                        is_paid=False,
                        due_date__lte=end_of_month
                    )
                
                # Final validation before creating payment record
                if amount_float <= 0:
                    messages.error(request, 'Invalid payment amount. Payment cannot be processed.')
                    return redirect('payer_dashboard')
                
                # Create payment record only after confirming success
                payment = Payment.objects.create(
                    student=student,
                    payer=request.user,  # Set the payer who made the payment
                    amount=amount_float,  # Use validated amount
                    status='completed',
                    payment_method=payment_method_type,  # Save the payment method type
                    bank_account=None,  # No bank account reference stored
                    receipt_number=payment_intent.id
                )
                
                # Create PaymentItem records to link payment to breakdown items
                total_payment_amount = Decimal(str(amount_float))  # Use validated amount
                
                # Get all unpaid bills and categorize them by priority
                from datetime import datetime, timedelta
                import calendar
                
                today = timezone.now().date()
                current_date = datetime.now()
                current_month = current_date.month
                current_year = current_date.year
                
                # Calculate the last day of the current month
                last_day_of_month = calendar.monthrange(current_year, current_month)[1]
                end_of_month = datetime(current_year, current_month, last_day_of_month).date()
                
                # Get all unpaid bills
                all_unpaid_bills = PaymentBreakdown.objects.filter(
                    student=student,
                    is_paid=False
                ).order_by('due_date')
                
                # Categorize bills by priority
                overdue_bills = []
                current_month_bills = []
                future_bills = []
                
                for bill in all_unpaid_bills:
                    if bill.late_date and bill.late_date < today:
                        overdue_bills.append(bill)
                    elif bill.due_date <= end_of_month:
                        current_month_bills.append(bill)
                    else:
                        future_bills.append(bill)
                
                # Apply payment in priority order: overdue -> current month -> future
                remaining_amount = total_payment_amount
                bills_to_update = []
                
                # Process overdue bills first
                for bill in overdue_bills:
                    if remaining_amount <= 0:
                        break
                    
                    bill_remaining = Decimal(str(bill.remaining_amount))
                    bill_amount = min(remaining_amount, bill_remaining)
                    
                    # Create PaymentItem record
                    PaymentItem.objects.create(
                        payment=payment,
                        breakdown_item=bill,
                        amount_paid=bill_amount,
                        currency='USD'  # Default to USD
                    )
                    
                    # Check if bill is now fully paid
                    if bill_amount >= bill_remaining:
                        bill.is_paid = True
                    
                    bills_to_update.append(bill)
                    remaining_amount -= bill_amount
                
                # Process current month bills
                for bill in current_month_bills:
                    if remaining_amount <= 0:
                        break
                    
                    bill_remaining = Decimal(str(bill.remaining_amount))
                    bill_amount = min(remaining_amount, bill_remaining)
                    
                    # Create PaymentItem record
                    PaymentItem.objects.create(
                        payment=payment,
                        breakdown_item=bill,
                        amount_paid=bill_amount,
                        currency='USD'  # Default to USD
                    )
                    
                    # Check if bill is now fully paid
                    if bill_amount >= bill_remaining:
                        bill.is_paid = True
                    
                    bills_to_update.append(bill)
                    remaining_amount -= bill_amount
                
                # Process future bills
                for bill in future_bills:
                    if remaining_amount <= 0:
                        break
                    
                    bill_remaining = Decimal(str(bill.remaining_amount))
                    bill_amount = min(remaining_amount, bill_remaining)
                    
                    # Create PaymentItem record
                    PaymentItem.objects.create(
                        payment=payment,
                        breakdown_item=bill,
                        amount_paid=bill_amount,
                        currency='USD'  # Default to USD
                    )
                    
                    # Check if bill is now fully paid
                    if bill_amount >= bill_remaining:
                        bill.is_paid = True
                    
                    bills_to_update.append(bill)
                    remaining_amount -= bill_amount
                
                # Save all updated bills
                for bill in bills_to_update:
                    bill.save()
                
                # Determine payment method type for success message
                payment_method_name = "payment method"
                if payment_method_type == 'card':
                    payment_method_name = f"{pm.card.brand.title()} card ending in {pm.card.last4}"
                elif payment_method_type == 'us_bank_account':
                    payment_method_name = f"bank account ending in {pm.us_bank_account.last4}"
                
                messages.success(request, f"✅ Payment of ${amount_float:.2f} completed successfully using {payment_method_name}. A receipt is now available.")
                return redirect('payment_history')
                
            elif payment_intent.status == 'processing':
                # Payment is being processed (common for bank transfers)
                # Create a pending payment record so it shows up in payment history
                payment = Payment.objects.create(
                    student=student,
                    payer=request.user,  # Set the payer who made the payment
                    amount=amount_float,  # Use validated amount
                    status='pending',
                    payment_method=payment_method_type,  # Save the payment method type
                    bank_account=None,  # No bank account reference stored
                    receipt_number=payment_intent.id
                )
                
                messages.info(request, f"Payment of ${amount_float:.2f} is being processed. You'll receive a confirmation once it's completed.")
                return redirect('payment_history')
                
            elif payment_intent.status == 'requires_capture':
                # Payment requires capture (for manual capture scenarios)
                messages.warning(request, f"Payment of ${amount_float:.2f} requires manual capture. Please contact support.")
                return redirect('payment_history')
                
            else:
                # Payment failed or is in an unexpected state
                messages.error(request, f"Payment failed or incomplete. Status: {payment_intent.status}")
                return redirect('payment', student_id=student_id)
            
        except stripe.error.CardError as e:
            messages.error(request, f"Card error: {e.error.message}")
            return redirect('payment', student_id=student_id)
        except stripe.error.InvalidRequestError as e:
            messages.error(request, f"Invalid request: {e.error.message}")
            return redirect('payment', student_id=student_id)
        except Exception as e:
            messages.error(request, f"Payment failed: {str(e)}")
            return redirect('payment', student_id=student_id)
    
    return redirect('payment_history')

@login_required
def payment_history(request):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    # Get all students associated with this payer
    my_students = Student.objects.filter(studentpayer__payer=request.user).distinct()
    
    # Check and update pending payment statuses (only show messages for status changes)
    pending_payments = Payment.objects.filter(
        student__in=my_students,
        status='pending'
    )
    
    for payment in pending_payments:
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment.receipt_number)
            if payment_intent.status == 'succeeded':
                # Only show message if status is actually changing
                if payment.status == 'pending':
                    payment.status = 'completed'
                    payment.save()
                    messages.success(request, f"Payment of ${payment.amount} for {payment.student.first_name} {payment.student.last_name} has been completed successfully.")
                    
                    # If this payment doesn't have PaymentItem records yet, create them
                    if not PaymentItem.objects.filter(payment=payment).exists():
                        # Get current month's payment items
                        now = timezone.now()
                        current_month = now.month
                        current_year = now.year
                        payment_items = PaymentBreakdown.objects.filter(
                            student=payment.student,
                            is_paid=False,
                            due_date__year=current_year,
                            due_date__month=current_month
                        )
                        
                        # Create PaymentItem records to link payment to breakdown items
                        total_payment_amount = payment.amount
                        payment_items_list = list(payment_items)
                        
                        if payment_items_list:
                            # Calculate how much each item should be paid
                            total_items_amount = sum(item.amount for item in payment_items_list)
                            
                            for item in payment_items_list:
                                if total_items_amount > 0:
                                    # Calculate proportional amount for this item
                                    item_amount = (item.amount / total_items_amount) * total_payment_amount
                                    # Round to 2 decimal places
                                    item_amount = round(item_amount, 2)
                                else:
                                    item_amount = Decimal('0.00')
                                
                                # Create PaymentItem record
                                PaymentItem.objects.create(
                                    payment=payment,
                                    breakdown_item=item,
                                    amount_paid=item_amount,
                                    currency='USD'  # Default to USD
                                )
                            
                            # Mark payment items as paid
                            payment_items.update(is_paid=True)
                            messages.info(request, f"Bills have been marked as paid for {payment.student.first_name} {payment.student.last_name}.")
                
            elif payment_intent.status == 'failed':
                # Only show message if status is actually changing
                if payment.status == 'pending':
                    payment.status = 'failed'
                    payment.save()
                    messages.error(request, f"Payment of ${payment.amount} for {payment.student.first_name} {payment.student.last_name} has failed.")
        except:
            pass  # Ignore errors, continue with the view
    
    # Get all payments made by this specific payer for their students
    # This will include all payment types: Stripe payments, saved bank account payments, etc.
    # Including failed payments as requested
    payments = Payment.objects.filter(
        payer=request.user,
        student__in=my_students
    ).order_by('-payment_date')
    
    # Get bills that are marked as paid and should show in payment history
    # But exclude bills that are already covered by Payment records (to avoid duplicates)
    paid_bills = PaymentBreakdown.objects.filter(
        student__in=my_students,
        is_paid=True,
        show_in_payment_history=True,
        payment_items__isnull=True  # Only bills that aren't part of a Payment record
    ).order_by('-updated_at')  # Use updated_at as the "payment date" for bills
    
    # Create a combined list of payments and bills for display
    all_transactions = []
    
    # Add regular payments with breakdown details
    for payment in payments:
        # Get the bills covered by this payment
        payment_items = payment.payment_items.all().select_related('breakdown_item')
        bills_covered = [item.breakdown_item for item in payment_items]
        
        # Create description with bill details
        if bills_covered:
            bill_descriptions = [f"{bill.description} (${item.amount_paid})" 
                               for item, bill in zip(payment_items, bills_covered)]
            description = f"Payment for {payment.student.first_name} {payment.student.last_name}: " + ", ".join(bill_descriptions)
        else:
            description = f'Payment - {payment.student.first_name} {payment.student.last_name}'
        
        all_transactions.append({
            'type': 'payment',
            'object': payment,
            'date': payment.payment_date,
            'amount': payment.amount,
            'student': payment.student,
            'status': payment.status,
            'description': description,
            'receipt_number': payment.receipt_number,
            'bills_covered': bills_covered,
            'payment_items': payment_items,
        })
    
    # Add paid bills that should show in history (only standalone bills, not part of payments)
    for bill in paid_bills:
        all_transactions.append({
            'type': 'bill',
            'object': bill,
            'date': bill.updated_at,  # Use when the bill was marked as paid
            'amount': bill.amount,
            'student': bill.student,
            'status': 'completed',
            'description': f'Bill - {bill.description}',
            'receipt_number': f'BILL-{bill.id}',
        })
    
    # Sort all transactions by date (most recent first)
    all_transactions.sort(key=lambda x: x['date'], reverse=True)
    
    # Add a message if no transactions are found
    if not all_transactions:
        messages.info(request, "No payment history found. Payments will appear here once you make transactions.")
    
    context = {
        'payments': payments,
        'my_students': my_students,
        'all_transactions': all_transactions,
    }
    return render(request, 'payment_history.html', context)

@login_required
def download_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    # Only allow payers to access their own payments, but allow admins to access any
    if request.user.user_type == 'payer':
        if not Student.objects.filter(id=payment.student.id, studentpayer__payer=request.user).exists():
            messages.error(request, 'You do not have permission to access this receipt.')
            return redirect('payment_history')
    elif request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    # Header
    p.setFont('Helvetica-Bold', 18)
    p.drawString(50, y, 'WAPrep Tuition Payment Receipt')
    y -= 30
    p.setFont('Helvetica', 12)
    p.drawString(50, y, f'Receipt #: {payment.receipt_number}')
    y -= 20
    p.drawString(50, y, f'Date: {payment.payment_date.strftime("%B %d, %Y %I:%M %p")}')
    y -= 20
    payer_name = payment.payer.get_full_name() if payment.payer else 'N/A'
    payer_email = payment.payer.email if payment.payer else 'N/A'
    p.drawString(50, y, f'Payer: {payer_name} ({payer_email})')
    y -= 20
    p.drawString(50, y, f'Student: {payment.student.first_name} {payment.student.last_name}')
    y -= 20
    p.drawString(50, y, f'Amount: ${payment.amount:.2f}')
    y -= 20
    p.drawString(50, y, f'Status: {payment.status.capitalize()}')
    y -= 30
    # Payment Breakdown
    payment_items = PaymentItem.objects.filter(payment=payment).select_related('breakdown_item')
    if payment_items.exists():
        p.setFont('Helvetica-Bold', 14)
        p.drawString(50, y, 'Payment Breakdown:')
        y -= 20
        p.setFont('Helvetica-Bold', 12)
        p.drawString(50, y, 'Description')
        p.drawString(250, y, 'Due Date')
        p.drawString(400, y, 'Amount Paid')
        y -= 15
        p.setFont('Helvetica', 12)
        for item in payment_items:
            desc = item.breakdown_item.description
            due = item.breakdown_item.due_date.strftime('%b %d, %Y') if item.breakdown_item.due_date else 'N/A'
            amt = f"${item.amount_paid:.2f}"
            p.drawString(50, y, desc[:30])
            p.drawString(250, y, due)
            p.drawString(400, y, amt)
            y -= 15
            if y < 80:
                p.showPage()
                y = height - 50
                p.setFont('Helvetica', 12)
        # Subtotal
        p.setFont('Helvetica-Bold', 12)
        p.drawString(250, y, 'Total:')
        p.drawString(400, y, f"${payment.amount:.2f}")
        y -= 20
    else:
        p.setFont('Helvetica-Oblique', 11)
        p.drawString(50, y, 'Detailed breakdown not available for this payment.')
        y -= 20
    # Footer
    p.setFont('Helvetica-Oblique', 10)
    p.drawString(50, y, 'Thank you for your payment!')
    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.receipt_number}.pdf"'
    return response

@login_required
def payment_detail(request, payment_id):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Check that the user is allowed to access this payment
    if not Student.objects.filter(id=payment.student.id, studentpayer__payer=request.user).exists():
        messages.error(request, 'You do not have permission to access this payment.')
        return redirect('payment_history')
    
    # Get payment items (breakdown of what was paid for)
    payment_items = PaymentItem.objects.filter(payment=payment).select_related('breakdown_item')
    
    # If no payment items exist, create a fallback display
    if not payment_items.exists():
        # This might happen for older payments before PaymentItem was implemented
        # Show a generic breakdown
        payment_items = []
        context = {
            'payment': payment,
            'payment_items': payment_items,
            'has_breakdown': False,
        }
    else:
        context = {
            'payment': payment,
            'payment_items': payment_items,
            'has_breakdown': True,
        }
    
    return render(request, 'payment_detail.html', context)

@login_required
@admin_required
def admin_dashboard(request):
    
    # In a real application, these would come from a database
    context = {
        'total_payments': 15000.00,
        'pending_payments': 2500.00,
        'total_students': 45,
        'recent_payments': [
            {
                'date': 'Feb 15, 2024',
                'student_name': 'John Doe',
                'amount': 500.00,
                'status': 'Completed'
            },
            {
                'date': 'Feb 14, 2024',
                'student_name': 'Jane Smith',
                'amount': 500.00,
                'status': 'Pending'
            }
        ]
    }
    return render(request, 'admin_dashboard.html', context)

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            # Check if user exists with this email
            user = User.objects.get(email=email)
            
            # Generate a unique token
            import secrets
            token = secrets.token_urlsafe(32)
            
            # Create password reset record
            PasswordReset.objects.create(
                user=user,
                token=token
            )
            
            # Send reset email
            reset_url = request.build_absolute_uri(f'/reset-password/{token}/')
            subject = 'WAPrep Tuition Portal - Password Reset'
            message = f"""
Hello {user.first_name},

You have requested to reset your password for the WAPrep Tuition Portal.

To reset your password, please click the following link:
{reset_url}

This link will expire in 24 hours.

If you did not request this password reset, please ignore this email.

Best regards,
WAPrep Administration
            """.strip()
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, 'Password reset link has been sent to your email address.')
            return redirect('payer_login')
            
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(request, 'If an account with that email exists, a password reset link has been sent.')
            return redirect('payer_login')
        except Exception as e:
            messages.error(request, f'Error sending reset email: {str(e)}')
            return redirect('forgot_password')
    
    return render(request, 'forgot_password.html')

def forgot_id(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            # Check if user exists with this email
            user = User.objects.get(email=email)
            
            # Generate a new user ID
            new_user_id = generate_unique_user_id(user.first_name, user.last_name)
            
            # Update the user's ID
            user.user_id = new_user_id
            user.save()
            
            # Send new user ID email
            subject = 'WAPrep Tuition Portal - Your New User ID'
            message = f"""
Hello {user.first_name},

You have requested a new user ID for the WAPrep Tuition Portal.

Your new User ID is: {new_user_id}

Please use this new ID to log in to your account. Your old ID is no longer valid.

Please keep this information secure and do not share it with others.

If you did not request this new ID, please contact us immediately.

Best regards,
WAPrep Administration
            """.strip()
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, 'Your new user ID has been sent to your email address.')
            return redirect('payer_login')
            
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(request, 'If an account with that email exists, your new user ID has been sent.')
            return redirect('payer_login')
        except Exception as e:
            messages.error(request, f'Error generating new user ID: {str(e)}')
            return redirect('forgot_password')
    
    return redirect('forgot_password')

@login_required
def students(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'Only admins can access this page.')
        return redirect('admin_login')
    
    # Get search parameters
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'first_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Start with all students
    students = Student.objects.all()
    
    # Apply search filter
    if search_query:
        students = students.filter(
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(grade__icontains=search_query)
        )
    
    # Apply sorting
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    
    # Handle special sorting cases
    if sort_by in ['first_name', '-first_name']:
        students = students.order_by(sort_by, 'last_name')
    elif sort_by in ['last_name', '-last_name']:
        students = students.order_by(sort_by, 'first_name')
    else:
        students = students.order_by(sort_by)
    
    payers = User.objects.filter(user_type='payer')
    
    context = {
        'students': students,
        'payers': payers,
        'search_query': search_query,
        'sort_by': sort_by.replace('-', '') if sort_by.startswith('-') else sort_by,
        'sort_order': sort_order,
    }
    return render(request, 'students.html', context)

def generate_student_id(first_name, last_name, birthday):
    """
    Generate a unique student ID in the format #XXMMDDYYYY:
    - # is a digit 0-9 (random, but must ensure uniqueness)
    - XX is first and last initial (uppercase)
    - MMDDYYYY is birth date
    """
    first_initial = (first_name[0] if first_name else 'X').upper()
    last_initial = (last_name[0] if last_name else 'X').upper()
    initials = f"{first_initial}{last_initial}"

    # Format birthday
    try:
        birthday_str = birthday.strftime('%m%d%Y')
    except Exception:
        birthday_str = '00000000'

    base_id = f"{initials}{birthday_str}"

    # Ensure unique ID by randomizing the leading digit
    tried_digits = set()
    while len(tried_digits) < 10:
        leading_digit = str(random.randint(0, 9))
        full_id = f"{leading_digit}{base_id}"
        if not Student.objects.filter(student_id=full_id).exists():
            return full_id
        tried_digits.add(int(leading_digit))

    # If all 10 digits have been tried and are taken, fallback
    raise ValueError("Unable to generate a unique student ID after 10 attempts.")

@login_required
def add_student(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        grade = request.POST.get('grade')
        birthday = request.POST.get('date_of_birth')
        payer_id = request.POST.get('payer_id')
        relationship = request.POST.get('relationship', 'other')
        is_primary = request.POST.get('is_primary', False) == 'on'

        # Generate student ID
        try:
            birthday_date = datetime.strptime(birthday, '%Y-%m-%d')
            student_id = generate_student_id(first_name, last_name, birthday_date)
        except ValueError:
            messages.error(request, 'Invalid birthday format')
            return redirect('students')

        # Check for existing student with same name and birth date
        existing_student = Student.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            date_of_birth=birthday_date
        ).first()
        
        if existing_student:
            messages.warning(request, f'A student named {first_name} {last_name} with birth date {birthday_date.strftime("%m/%d/%Y")} already exists (ID: {existing_student.student_id}).')
            return redirect('students')

        # Convert grade to integer
        try:
            grade_int = int(grade) if grade else 1
        except (ValueError, TypeError):
            grade_int = 1
            
        # Create student
        try:
            student = Student.objects.create(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=birthday_date,
                grade=grade_int,
            )

            # Add payer relationship
            if payer_id:
                payer = User.objects.get(id=payer_id)
                StudentPayer.objects.create(
                    student=student,
                    payer=payer,
                    relationship=relationship,
                    is_primary=is_primary
                )

            messages.success(request, 'Student added successfully')
        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
            return redirect('students')
            
        return redirect('students')
    return redirect('students')

@login_required
@require_POST
def delete_student(request):
    # Only allow payer users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = get_object_or_404(Student, id=student_id)
            student_name = f"{student.first_name} {student.last_name}"
            student.delete()
            messages.success(request, f'Student {student_name} deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting student: {str(e)}')
    
    return redirect('students')

def select_login(request):
    return render(request, 'select_login.html', {'show_navbar': False})

@login_required
def update_student_notes(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        notes = request.POST.get('notes')
        
        try:
            student = get_object_or_404(Student, id=student_id)
            student.notes = notes
            student.save()
            messages.success(request, f'Notes updated for {student.first_name} {student.last_name}')
        except Exception as e:
            messages.error(request, f'Error updating notes: {str(e)}')
    
    return redirect('students')

@login_required
@require_POST
def update_student(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        grade = request.POST.get('grade')
        date_of_birth = request.POST.get('date_of_birth')
        status = request.POST.get('status')
        
        try:
            student = get_object_or_404(Student, id=student_id)
            student.first_name = first_name
            student.last_name = last_name
            student.grade = grade
            student.date_of_birth = date_of_birth
            student.status = status
            student.save()
            messages.success(request, f'Student {first_name} {last_name} updated successfully')
        except Exception as e:
            messages.error(request, f'Error updating student: {str(e)}')
    
    return redirect('students')

def generate_unique_user_id(first_name, last_name):
    """
    Generate a unique 6-character user ID with numbers and special characters.
    Format: 6 characters including letters, numbers, and special characters
    Example: K8#mN2
    """
    # Define character sets
    letters = string.ascii_letters  # a-z, A-Z
    digits = string.digits  # 0-9
    special_chars = "!@#$%^&*"  # Special characters (avoiding problematic ones)
    
    # Combine all character sets
    all_chars = letters + digits + special_chars
    
    # Generate unique 6-character user ID
    max_attempts = 1000  # Prevent infinite loop
    attempts = 0
    
    while attempts < max_attempts:
        # Generate 6-character ID with at least one letter, one number, and one special character
        user_id = ''.join(random.choices(all_chars, k=6))
        
        # Ensure it contains at least one letter, one number, and one special character
        has_letter = any(c in letters for c in user_id)
        has_digit = any(c in digits for c in user_id)
        has_special = any(c in special_chars for c in user_id)
        
        if has_letter and has_digit and has_special:
            # Check if this user_id already exists
            if not User.objects.filter(user_id=user_id).exists():
                return user_id
        
        attempts += 1
    
    # Fallback: if we can't generate a unique ID with the pattern, use a simpler approach
    while True:
        user_id = 'P' + ''.join(random.choices(string.ascii_uppercase + string.digits + "!@#$%^&*", k=5))
        if not User.objects.filter(user_id=user_id).exists():
            return user_id

@login_required
def add_payer_to_student(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        payer_id = request.POST.get('payer_id')  # For existing payer selection
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        relationship = request.POST.get('relationship')
        is_primary = request.POST.get('is_primary', False) == 'on'
        
        try:
            student = get_object_or_404(Student, id=student_id)
            
            # Handle existing payer selection
            if payer_id:
                payer = get_object_or_404(User, id=payer_id)
                if payer.user_type != 'payer':
                    messages.error(request, f'Selected user is not a payer.')
                    return redirect('student_profile', student_id=student_id)
            else:
                # Handle new payer creation
                if not email or not first_name or not last_name:
                    messages.error(request, 'Please provide all required information for new payer.')
                    return redirect('student_profile', student_id=student_id)
                
                # Check if user already exists by email
                if User.objects.filter(email=email).exists():
                    payer = User.objects.get(email=email)
                    if payer.user_type != 'payer':
                        messages.error(request, f'User with email {email} exists but is not a payer.')
                        return redirect('student_profile', student_id=student_id)
                else:
                    # Create new user with temporary password
                    import secrets
                    temp_password = secrets.token_urlsafe(12)
                    user_id = generate_unique_user_id(first_name, last_name)
                    payer = User.objects.create_user(
                        username=user_id,  # Set username to user_id for login
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        password=temp_password,
                        user_type='payer',
                        user_id=user_id,
                        is_active=False
                    )
                    # Note: Activation email will be sent manually via admin interface
            
            # Validate relationship is provided
            if not relationship:
                messages.error(request, 'Please select a relationship.')
                return redirect('student_profile', student_id=student_id)
            
            # If this is set as primary, unset any existing primary payer
            if is_primary:
                StudentPayer.objects.filter(student=student, is_primary=True).update(is_primary=False)
            
            # Check if relationship already exists
            if StudentPayer.objects.filter(student=student, payer=payer).exists():
                messages.warning(request, f'{payer.get_full_name()} is already linked to {student} as a {relationship}.')
            else:
                StudentPayer.objects.create(
                    student=student,
                    payer=payer,
                    relationship=relationship,
                    is_primary=is_primary
                )
                messages.success(request, f'Added {payer.get_full_name()} as {relationship} for {student}.')
        except Exception as e:
            messages.error(request, f'Error adding payer: {str(e)}')
    
    return redirect('student_profile', student_id=student_id)

@login_required
def send_activation_email(request, student_payer_id):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    try:
        student_payer = get_object_or_404(StudentPayer, id=student_payer_id)
        payer = student_payer.payer
        student = student_payer.student
        
        # Generate new temporary password
        import secrets
        temp_password = secrets.token_urlsafe(12)
        payer.set_password(temp_password)
        payer.save()
        
        # Send activation email
        activation_url = request.build_absolute_uri(f'/activate-account/{payer.id}/{temp_password}/')
        subject = 'WAPrep Tuition Portal - Account Activation'
        message = f"""
Hello {payer.first_name},

You have been added as a payer for {student.first_name} {student.last_name} at Washington Preparatory School.

Your User ID: {payer.user_id}
Your Temporary Password: {temp_password}

To activate your account, please click the following link:
{activation_url}

After activation, you will be required to change your password

If you have any questions, please contact us.

Best regards,
WAPrep Administration
        """.strip()
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [payer.email],
            fail_silently=False,
        )
        
        messages.success(request, f'Activation email sent to {payer.email}.')
    except Exception as e:
        messages.error(request, f'Error sending activation email: {str(e)}')
    
    return redirect('student_profile', student_id=student_payer.student.id)

@login_required
def send_activation_reminders(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            # Get all unactivated payers
            unactivated_payers = User.objects.filter(
                user_type='payer',
                is_active=False
            ).distinct()
            
            if not unactivated_payers.exists():
                messages.info(request, 'No unactivated payers found.')
                return redirect('students')
            
            success_count = 0
            error_count = 0
            
            for payer in unactivated_payers:
                try:
                    # Generate new temporary password
                    import secrets
                    temp_password = secrets.token_urlsafe(12)
                    payer.set_password(temp_password)
                    payer.save()
                    
                    # Get associated students for context
                    student_payers = StudentPayer.objects.filter(payer=payer)
                    student_names = [f"{sp.student.first_name} {sp.student.last_name}" for sp in student_payers]
                    students_text = ", ".join(student_names) if student_names else "students"
                    
                    # Send activation email
                    activation_url = request.build_absolute_uri(f'/activate-account/{payer.id}/{temp_password}/')
                    subject = 'WAPrep Tuition Portal - Account Activation Reminder'
                    message = f"""
Hello {payer.first_name},

This is a reminder that you have an account at Washington Preparatory School's Tuition Portal that needs to be activated.

You are listed as a payer for: {students_text}

Your User ID: {payer.user_id}
Your Temporary Password: {temp_password}

To activate your account, please click the following link:
{activation_url}

After activation, you will be required to change your password.

If you have any questions, please contact us.

Best regards,
WAPrep Administration
                    """.strip()
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [payer.email],
                        fail_silently=False,
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    # Log the error but continue with other payers
                    print(f"Error sending activation email to {payer.email}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Activation reminders sent to {success_count} payer(s).')
            if error_count > 0:
                messages.warning(request, f'Failed to send {error_count} reminder(s). Check logs for details.')
                
        except Exception as e:
            messages.error(request, f'Error sending activation reminders: {str(e)}')
    
    return redirect('students')

def activate_account(request, user_id, temp_password):
    try:
        user = get_object_or_404(User, id=user_id)
        if user.check_password(temp_password):
            # Store user info in session for activation process
            request.session['activation_user_id'] = user.id
            request.session['activation_temp_password'] = temp_password
            # Redirect to activation page
            messages.success(request, 'Please set your new password to activate your account.')
            return redirect('activation_setup')
        else:
            messages.error(request, 'Invalid activation link.')
            return redirect('payer_login')
    except Exception as e:
        messages.error(request, 'Error activating account.')
        return redirect('payer_login')

def activation_setup(request):
    # Check if user has valid activation session
    user_id = request.session.get('activation_user_id')
    temp_password = request.session.get('activation_temp_password')
    
    if not user_id or not temp_password:
        messages.error(request, 'Invalid activation session.')
        return redirect('payer_login')
    
    try:
        user = get_object_or_404(User, id=user_id)
        if not user.check_password(temp_password):
            messages.error(request, 'Invalid activation session.')
            return redirect('payer_login')
        
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
            else:
                # Use the new password validation with user parameter
                is_valid, message = validate_password(new_password, user)
                if not is_valid:
                    messages.error(request, message)
                else:
                    try:
                        # Store password in history before changing it
                        from .models import PasswordHistory
                        PasswordHistory.store_password(user, new_password)
                        
                        # Set new password and activate account
                        user.set_password(new_password)
                        user.is_active = True
                        user.save()
                        
                        # Clear activation session before logging in
                        if 'activation_user_id' in request.session:
                            del request.session['activation_user_id']
                        if 'activation_temp_password' in request.session:
                            del request.session['activation_temp_password']
                        
                        # Log the user in
                        login(request, user)
                        
                        messages.success(request, 'Account activated successfully with secure password! Welcome to your dashboard.')
                        return redirect('payer_dashboard')
                    except Exception as e:
                        messages.error(request, f'Error saving password: {str(e)}')
        
        return render(request, 'activation_setup.html', {'user': user})
        
    except Exception as e:
        messages.error(request, f'Error during activation: {str(e)}')
        return redirect('payer_login')

@login_required
def remove_payer_from_student(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        payer_id = request.POST.get('payer_id')
        
        try:
            student = get_object_or_404(Student, id=student_id)
            payer = get_object_or_404(User, id=payer_id)
            
            # Don't allow removing the last payer
            if student.payers.count() <= 1:
                messages.error(request, 'Cannot remove the last payer from a student')
                return redirect('students')
            
            StudentPayer.objects.filter(student=student, payer=payer).delete()
            messages.success(request, f'Removed {payer.get_full_name()} from {student}')
        except Exception as e:
            messages.error(request, f'Error removing payer: {str(e)}')
    
    return redirect('students')

@login_required
def admin_reports(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'Only admins can access this page.')
        return redirect('admin_login')
    
    # Get the selected year from query parameters, default to current year
    from datetime import datetime
    selected_year = request.GET.get('year', datetime.now().year)
    
    # Get all payments for the selected year
    payments = Payment.objects.filter(
        payment_date__year=selected_year
    ).order_by('-payment_date')
    
    # Calculate total amount for the year
    total_amount = payments.aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Get monthly totals
    monthly_totals = {}
    for month in range(1, 13):
        month_payments = payments.filter(payment_date__month=month)
        month_total = month_payments.aggregate(total=models.Sum('amount'))['total'] or 0
        monthly_totals[month] = {
            'total': month_total,
            'count': month_payments.count()
        }
    
    # Get list of available years (from first payment to current year)
    first_payment = Payment.objects.order_by('payment_date').first()
    if first_payment:
        start_year = first_payment.payment_date.year
    else:
        start_year = datetime.now().year
    end_year = datetime.now().year
    available_years = range(start_year, end_year + 1)
    
    context = {
        'selected_year': int(selected_year),
        'available_years': available_years,
        'total_amount': total_amount,
        'monthly_totals': monthly_totals,
        'payments': payments,
    }
    return render(request, 'admin_reports.html', context)

@login_required
@payer_required
def payer_dashboard(request):
    
    # Get students already associated with this payer
    my_students = Student.objects.filter(studentpayer__payer=request.user).distinct()

    # Get current month and year using system datetime instead of Django timezone
    # Django timezone.now() seems to be showing incorrect date
    from datetime import datetime, timedelta
    import calendar
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    today = current_date.date()

    # Calculate the last day of the current month
    last_day_of_month = calendar.monthrange(current_year, current_month)[1]
    end_of_month = datetime(current_year, current_month, last_day_of_month).date()

    # Calculate total amount owed and get payment breakdowns
    total_amount_owed = 0
    
    for student in my_students:
        # Get all unpaid payment breakdown items using correct payment logic
        breakdown_items = student.payment_breakdowns.filter(due_date__isnull=False)
        unpaid_items = [bill for bill in breakdown_items if not bill.is_fully_paid]
        
        # Get overdue items (past late_date)
        overdue_items = [bill for bill in unpaid_items if bill.late_date and bill.late_date < today]
        student.overdue_items = overdue_items
        student.overdue_amount = sum(bill.remaining_amount for bill in overdue_items)
        student.overdue_count = len(overdue_items)
        
        # Get upcoming items (due by the end of the current month)
        # Show bills that are due by the end of the current month
        upcoming_items = [bill for bill in unpaid_items if bill.due_date and bill.due_date <= end_of_month]
        student.upcoming_items = upcoming_items
        student.upcoming_amount = sum(bill.remaining_amount for bill in upcoming_items)
        student.upcoming_count = len(upcoming_items)
        
        # Set due date to end of current month
        student.next_due_date = end_of_month
        
        # Calculate total amount owed
        total_amount_owed += student.overdue_amount + student.upcoming_amount
    
    context = {
        'my_students': my_students,
        'total_amount_owed': total_amount_owed,
    }
    return render(request, 'payer_dashboard.html', context)

@login_required
def add_student_to_payer(request):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    

    if request.method == 'POST':
        print("POST to add_student_to_payer received:", request.POST)
        student_id = request.POST.get('student_id')
        relationship = request.POST.get('relationship', 'other')
        is_primary = request.POST.get('is_primary', False) == 'on'
        
        try:
            student = get_object_or_404(Student, id=student_id)
            
            # Check if the student is already linked to this payer
            if StudentPayer.objects.filter(student=student, payer=request.user).exists():
                messages.warning(request, f'{student.first_name} {student.last_name} is already linked to your account.')
                return redirect('payer_dashboard')

            # If this is set as primary, unset any existing primary payer
            if is_primary:
                StudentPayer.objects.filter(student=student, is_primary=True).update(is_primary=False)
            
            # Create the payer-student relationship
            StudentPayer.objects.create(
                student=student,
                payer=request.user,
                relationship=relationship,
                is_primary=is_primary
            )
            messages.success(request, f'Successfully added {student.first_name} {student.last_name} to your account')
        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
    
    return redirect('payer_dashboard')

def student_profile(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    payers = User.objects.filter(user_type='payer')  # filter to only payer users

    return render(request, 'student_profile.html', {
        'student': student,
        'payers': payers,
    })

def request_account_view(request):
    if request.method == 'POST':
        form = AccountRequestForm(request.POST)
        if form.is_valid():
            request_obj = form.save()

            # Email content
            subject = 'New Payer Account Request'
            message = f"""
A new payer has submitted an account request:

Name: {request_obj.first_name} {request_obj.last_name}
Email: {request_obj.email}
Students Responsible For: {request_obj.student_names}

Please review and follow up accordingly.
            """.strip()

            send_mail(
                subject,
                message,  
                settings.DEFAULT_FROM_EMAIL,  # Use settings instead of config
                ['info@waprep.org'],
                fail_silently=False,
            )

            messages.success(request, 'Your request has been submitted. We will contact you soon.')
            return redirect('payer_login')
    else:
        form = AccountRequestForm()
    
    return render(request, 'request_account.html', {'form': form})

@login_required
def payer_welcome(request):
    # Only allow payer users
    if request.user.user_type != 'payer':
        return redirect('payer_login')
    # Force password change if flagged
    if request.session.get('force_password_change', False):
        messages.warning(request, 'Please change your password before continuing.')
        return redirect('payer_profile')
    return render(request, 'payer_welcome.html')



@login_required
def inline_edit_student_field(request):
    """Handle inline editing of student fields via AJAX"""
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        field_name = request.POST.get('field_name')
        field_value = request.POST.get('field_value')
        
        try:
            student = get_object_or_404(Student, id=student_id)
            
            # Validate field name
            allowed_fields = ['first_name', 'last_name', 'grade', 'status', 'notes', 'date_of_birth']
            if field_name not in allowed_fields:
                return JsonResponse({'error': 'Invalid field'}, status=400)
            
            # Set the field value with validation for grade
            if field_name == 'grade':
                try:
                    grade_int = int(field_value) if field_value else 1
                    setattr(student, field_name, grade_int)
                except (ValueError, TypeError):
                    return JsonResponse({'error': 'Grade must be a valid number'}, status=400)
            else:
                setattr(student, field_name, field_value)
            student.save()
            
            # Return the formatted value for display
            if field_name == 'status':
                display_value = student.get_status_display()
            elif field_name == 'grade':
                display_value = f"Grade {field_value}"
            elif field_name == 'notes':
                display_value = field_value if field_value else "No notes added yet."
            elif field_name == 'date_of_birth':
                try:
                    date_obj = datetime.strptime(field_value, '%Y-%m-%d').date()
                    display_value = date_obj.strftime('%b %d, %Y')
                except:
                    display_value = field_value
            else:
                display_value = field_value
                
            return JsonResponse({
                'success': True,
                'display_value': display_value,
                'message': f'{field_name.replace("_", " ").title()} updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def inline_edit_payer_field(request):
    """Handle inline editing of payer fields via AJAX"""
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        student_payer_id = request.POST.get('student_payer_id')
        field_name = request.POST.get('field_name')
        field_value = request.POST.get('field_value')
        is_primary = request.POST.get('is_primary')
        
        try:
            student_payer = get_object_or_404(StudentPayer, id=student_payer_id)
            
            # Validate field name
            allowed_fields = ['first_name', 'last_name', 'email', 'relationship']
            if field_name not in allowed_fields:
                return JsonResponse({'error': 'Invalid field'}, status=400)
            
            if field_name in ['first_name', 'last_name']:
                # Update the payer's name
                payer = student_payer.payer
                setattr(payer, field_name, field_value)
                payer.save()
                display_value = f"{payer.first_name} {payer.last_name}"
                
            elif field_name == 'email':
                # Update the payer's email
                payer = student_payer.payer
                payer.email = field_value
                payer.save()
                display_value = field_value
                
            elif field_name == 'relationship':
                # Update the relationship
                student_payer.relationship = field_value
                student_payer.save()
                display_value = student_payer.get_relationship_display()
                
            else:
                return JsonResponse({'error': 'Invalid field'}, status=400)
                
            return JsonResponse({
                'success': True,
                'display_value': display_value,
                'message': f'{field_name.replace("_", " ").title()} updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def monthly_bills(request, student_id, month_key):
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Parse the month key (format: YYYY-MM)
    try:
        year, month = month_key.split('-')
        year = int(year)
        month = int(month)
        
        # Get the first and last day of the month
        from datetime import datetime, date
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        month_display = first_day.strftime('%B %Y')
        
    except (ValueError, IndexError):
        messages.error(request, 'Invalid month format.')
        return redirect('student_months', student_id=student_id)
    
    # Get all bills for this student in this month
    bills = student.payment_breakdowns.filter(
        due_date__gte=first_day,
        due_date__lte=last_day
    )
    
    # Convert to list and sort by overdue status
    bills_list = list(bills)
    from django.utils import timezone
    today = timezone.now().date()
    
    def sort_key(bill):
        # Overdue bills go first (priority 0)
        if bill.late_date and bill.late_date < today and not bill.is_fully_paid:
            days_overdue = (today - bill.late_date).days
            return (0, -days_overdue, bill.due_date or today)  # Negative for reverse sort
        
        # Current unpaid bills go second (priority 1)
        if not bill.is_fully_paid:
            return (1, 0, bill.due_date or today)
        
        # Paid bills go last (priority 2)
        return (2, 0, bill.due_date or today)
    
    bills_list.sort(key=sort_key)
    
    # Calculate totals using correct payment logic
    total_amount = bills.aggregate(total=models.Sum('amount'))['total'] or 0
    total_bills = bills.count()
    
    # Count bills by payment status, respecting payment_status_override
    paid_bills = sum(1 for bill in bills if (bill.is_fully_paid or bill.payment_status_override == 'paid'))
    unpaid_bills = sum(1 for bill in bills if not (bill.is_fully_paid or bill.payment_status_override == 'paid'))
    
    # Calculate amounts using correct payment logic, respecting payment_status_override
    # For paid_amount: sum fully paid bills + paid portion of partially paid bills
    paid_amount = sum(
        bill.amount if (bill.is_fully_paid or bill.payment_status_override == 'paid') else (bill.amount - bill.remaining_amount)
        for bill in bills
    )
    unpaid_amount = sum(
        bill.remaining_amount if bill.payment_status_override == 'unpaid' else Decimal('0.00')
        for bill in bills 
        if not (bill.is_fully_paid or bill.payment_status_override == 'paid')
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            date_incurred = request.POST.get('date_incurred')
            late_date = request.POST.get('late_date')
            payment_status = request.POST.get('payment_status', 'unpaid')
            try:
                PaymentBreakdown.objects.create(
                    student=student,
                    description=description,
                    amount=amount,
                    currency='USD',  # Default currency
                    due_date=due_date,
                    date_incurred=date_incurred if date_incurred else None,
                    late_date=late_date if late_date else None,
                    payment_status_override=payment_status,
                    is_paid=(payment_status == 'paid'),  # Keep is_paid for backward compatibility
                    show_in_payment_history=True  # Always show in payment history for new bills
                )
                messages.success(request, 'Bill added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding bill: {str(e)}')
        elif action == 'edit':
            bill_id = request.POST.get('bill_id')
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            date_incurred = request.POST.get('date_incurred')
            late_date = request.POST.get('late_date')
            payment_status = request.POST.get('payment_status', 'unpaid')
            show_in_payment_history = request.POST.get('show_in_payment_history') == 'on'
            try:
                bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                
                # Store the old payment status to check if it changed to 'paid'
                old_payment_status = bill.payment_status_override
                
                bill.description = description
                bill.amount = amount
                bill.due_date = due_date
                bill.date_incurred = date_incurred if date_incurred else None
                bill.late_date = late_date if late_date else None
                bill.payment_status_override = payment_status
                bill.is_paid = (payment_status == 'paid')  # Keep is_paid for backward compatibility
                bill.show_in_payment_history = show_in_payment_history
                bill.save()
                
                # If the bill was marked as 'paid', create a manual payment to zero out the remaining amount
                if payment_status == 'paid' and old_payment_status != 'paid':
                    manual_payment = create_manual_payment_for_bill(bill, student, request.user)
                    if manual_payment:
                        messages.success(request, f'Bill updated successfully. Manual payment of ${bill.remaining_amount} created to mark as paid.')
                    else:
                        messages.success(request, 'Bill updated successfully.')
                else:
                    messages.success(request, 'Bill updated successfully.')
                    
            except PaymentBreakdown.DoesNotExist:
                messages.error(request, 'Bill not found.')
            except Exception as e:
                messages.error(request, f'Error updating bill: {str(e)}')
        elif action == 'remove':
            bill_id = request.POST.get('bill_id')
            try:
                bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                bill.delete()
                messages.success(request, 'Bill removed successfully.')
            except Exception as e:
                messages.error(request, f'Error removing bill: {str(e)}')
        elif action == 'add_payment':
            payer_id = request.POST.get('payer_id')
            amount = request.POST.get('amount')
            payment_date = request.POST.get('payment_date')
            status = 'completed'  # Always completed since payment status option is removed
            payment_method = request.POST.get('payment_method', 'manual')
            notes = request.POST.get('notes', '')
            bill_ids = request.POST.getlist('bill_ids')
            
            # Enhanced validation for amount
            try:
                amount_float = float(amount) if amount else 0
            except (ValueError, TypeError):
                amount_float = 0
            
            # Validate amount is greater than 0
            if not amount or amount_float <= 0:
                messages.error(request, 'Payment amount must be greater than $0.')
                return redirect('monthly_bills', student_id=student_id, month_key=month_key)
            
            # Additional safety check - ensure amount is reasonable
            if amount_float > 100000:  # $100,000 limit
                messages.error(request, 'Payment amount exceeds maximum allowed limit.')
                return redirect('monthly_bills', student_id=student_id, month_key=month_key)
            
            try:
                payer = User.objects.get(id=payer_id, user_type='payer')
                
                # Create the payment
                payment = Payment.objects.create(
                    student=student,
                    payer=payer,
                    amount=amount,
                    payment_date=payment_date,
                    status=status,
                    payment_method=payment_method,
                    notes=notes,
                    receipt_number=f"MANUAL-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    currency='USD'  # Default to USD for manual payments
                )
                
                # Create payment items for each selected bill
                total_paid = 0
                for bill_id in bill_ids:
                    bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                    bill_amount = request.POST.get(f'bill_amount_{bill_id}', bill.amount)
                    
                    PaymentItem.objects.create(
                        payment=payment,
                        breakdown_item=bill,
                        amount_paid=bill_amount,
                        currency='USD'  # Default to USD
                    )
                    
                    total_paid += float(bill_amount)
                    
                    # Mark bill as paid if payment status is completed
                    if status == 'completed':
                        bill.is_paid = True
                        bill.save()
                
                # Update student's current balance
                if status == 'completed':
                    student.current_balance = student.current_balance - total_paid
                    student.save()
                
                messages.success(request, f'Payment of ${amount} added successfully for {payer.first_name} {payer.last_name}.')
                
            except User.DoesNotExist:
                messages.error(request, 'Selected payer not found.')
            except PaymentBreakdown.DoesNotExist:
                messages.error(request, 'One or more selected bills not found.')
            except Exception as e:
                messages.error(request, f'Error adding payment: {str(e)}')
        
        return redirect('monthly_bills', student_id=student_id, month_key=month_key)
    
    # Get payments for this student in this month
    payments = Payment.objects.filter(
        student=student,
        payment_date__gte=first_day,
        payment_date__lte=last_day
    ).order_by('-payment_date')
    
    # Get payers associated with this student
    student_payers = User.objects.filter(
        studentpayer__student=student,
        user_type='payer'
    ).order_by('first_name', 'last_name')
    
    context = {
        'student': student,
        'month_key': month_key,
        'month_display': month_display,
        'bills': bills_list,
        'payments': payments,
        'student_payers': student_payers,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'unpaid_amount': unpaid_amount,
        'total_bills': total_bills,
        'paid_bills': paid_bills,
        'unpaid_bills': unpaid_bills,
        'first_day': first_day,
        'last_day': last_day
    }
    return render(request, 'monthly_bills.html', context)

@login_required
def student_months(request, student_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Handle POST request for adding bills
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            date_incurred = request.POST.get('date_incurred')
            late_date = request.POST.get('late_date')
            payment_status = request.POST.get('payment_status', 'unpaid')
            try:
                bill = PaymentBreakdown.objects.create(
                    student=student,
                    description=description,
                    amount=amount,
                    currency='USD',  # Default currency
                    due_date=due_date,
                    date_incurred=date_incurred if date_incurred else None,
                    late_date=late_date if late_date else None,
                    payment_status_override=payment_status,
                    is_paid=(payment_status == 'paid'),  # Keep is_paid for backward compatibility
                    show_in_payment_history=True  # Always show in payment history for new bills
                )
                
                # If the bill was created as 'paid', create a manual payment to zero out the remaining amount
                if payment_status == 'paid':
                    manual_payment = create_manual_payment_for_bill(bill, student, request.user)
                    if manual_payment:
                        messages.success(request, f'Bill added successfully. Manual payment of ${bill.remaining_amount} created to mark as paid.')
                    else:
                        messages.success(request, 'Bill added successfully.')
                else:
                    messages.success(request, 'Bill added successfully.')
                    
            except Exception as e:
                messages.error(request, f'Error adding bill: {str(e)}')
        
        return redirect('student_months', student_id=student_id)
    
    # Get all bills for this student with due dates
    all_bills = student.payment_breakdowns.filter(due_date__isnull=False).order_by('due_date')
    
    # Define the billing cycle: January 2025 to May 2026
    billing_cycle_months = []
    
    # Add January 2025 to May 2025
    for month in range(1, 6):  # January (1) to May (5)
        month_key = f"2025-{month:02d}"
        month_display = f"{calendar.month_name[month]} 2025"
        billing_cycle_months.append((month_key, month_display))
    
    # Add June 2025 to December 2025
    for month in range(6, 13):  # June (6) to December (12)
        month_key = f"2025-{month:02d}"
        month_display = f"{calendar.month_name[month]} 2025"
        billing_cycle_months.append((month_key, month_display))
    
    # Add January 2026 to May 2026
    for month in range(1, 6):  # January (1) to May (5)
        month_key = f"2026-{month:02d}"
        month_display = f"{calendar.month_name[month]} 2026"
        billing_cycle_months.append((month_key, month_display))

    # Group bills by month
    monthly_billing = {}
    for bill in all_bills:
        month_key = bill.due_date.strftime('%Y-%m')
        month_display = bill.due_date.strftime('%B %Y')
        if month_key not in monthly_billing:
            monthly_billing[month_key] = {
                'month_display': month_display,
                'month_key': month_key,
                'total_bills': 0,
                'total_amount': 0,
                'paid_bills': 0,
                'unpaid_bills': 0,
                'paid_amount': 0,
                'unpaid_amount': 0
            }
        monthly_billing[month_key]['total_bills'] += 1
        monthly_billing[month_key]['total_amount'] += bill.amount
        
        # Use the correct payment status logic, respecting payment_status_override
        if bill.is_fully_paid or bill.payment_status_override == 'paid':
            monthly_billing[month_key]['paid_bills'] += 1
            monthly_billing[month_key]['paid_amount'] += bill.amount
        else:
            monthly_billing[month_key]['unpaid_bills'] += 1
            # Use remaining amount for unpaid bills to account for partial payments
            if bill.payment_status_override == 'unpaid':
                monthly_billing[month_key]['unpaid_amount'] += bill.remaining_amount
            else:
                monthly_billing[month_key]['unpaid_amount'] += Decimal('0.00')
            # Add paid portion of partially paid bills to paid_amount
            if bill.remaining_amount < bill.amount:
                monthly_billing[month_key]['paid_amount'] += (bill.amount - bill.remaining_amount)

    # Create the final sorted months list in billing cycle order
    sorted_months = []
    for month_key, month_display in billing_cycle_months:
        if month_key in monthly_billing:
            # Month has bills, use existing data
            sorted_months.append((month_key, monthly_billing[month_key]))
        else:
            # Month has no bills, create empty entry
            sorted_months.append((month_key, {
                'month_display': month_display,
                'month_key': month_key,
                'total_bills': 0,
                'total_amount': 0,
                'paid_bills': 0,
                'unpaid_bills': 0,
                'paid_amount': 0,
                'unpaid_amount': 0
            }))
    
    # Calculate student totals using correct payment logic
    total_bills = all_bills.count()
    total_amount = all_bills.aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Count bills by payment status, respecting payment_status_override
    paid_bills = sum(1 for bill in all_bills if (bill.is_fully_paid or bill.payment_status_override == 'paid'))
    unpaid_bills = sum(1 for bill in all_bills if not (bill.is_fully_paid or bill.payment_status_override == 'paid'))
    
    # Calculate amounts using correct payment logic, respecting payment_status_override
    # For paid_amount: sum fully paid bills + paid portion of partially paid bills
    paid_amount = sum(
        bill.amount if (bill.is_fully_paid or bill.payment_status_override == 'paid') else (bill.amount - bill.remaining_amount)
        for bill in all_bills
    )
    unpaid_amount = sum(
        bill.remaining_amount if bill.payment_status_override == 'unpaid' else Decimal('0.00')
        for bill in all_bills 
        if not (bill.is_fully_paid or bill.payment_status_override == 'paid')
    )
    
    context = {
        'student': student,
        'monthly_billing': sorted_months,
        'total_bills': total_bills,
        'total_amount': total_amount,
        'paid_bills': paid_bills,
        'unpaid_bills': unpaid_bills,
        'paid_amount': paid_amount,
        'unpaid_amount': unpaid_amount,
    }
    return render(request, 'student_months.html', context)

@login_required
def payer_profile_view(request):
    if request.user.user_type != 'payer':
        return redirect('payer_dashboard')  # or return 403
    # If forced, require password change and profile completion
    force_change = request.session.get('force_password_change', False)
    if request.method == 'POST':
        form = PayerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            # If password is being changed, validate and clear the force flag
            new_password = request.POST.get('new_password')
            if new_password:
                # Use the new password validation with user parameter
                is_valid, message = validate_password(new_password, user)
                if not is_valid:
                    messages.error(request, message)
                    return render(request, 'payer_profile.html', {'form': form, 'force_change': force_change})
                
                # Store password in history before changing it
                from .models import PasswordHistory
                PasswordHistory.store_password(user, new_password)
                
                user.set_password(new_password)
                user.save()
                request.session['force_password_change'] = False
                messages.success(request, 'Password changed successfully with secure password!')
                login(request, user)
            request.session['force_password_change'] = False
            messages.success(request, 'Profile updated successfully!')
            return redirect('payer_profile')
    else:
        form = PayerProfileForm(instance=request.user)
    return render(request, 'payer_profile.html', {'form': form, 'force_change': force_change})

@login_required
def edit_payer_profile(request):
    if request.method == 'POST':
        form = EditPayerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            # Gather data but don't save
            cleaned_data = form.cleaned_data
            subject = 'Payer Profile Update Request'
            message = f"""
A payer has requested a profile update.

User ID: {request.user.username}
Name: {request.user.get_full_name()}
Email: {request.user.email}

Requested Changes:
------------------
First Name: {cleaned_data.get('first_name')}
Last Name: {cleaned_data.get('last_name')}
Email: {cleaned_data.get('email')}

Please review and apply changes manually if appropriate.
    """

            # Send email to provider
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['info@waprep.org'],  # change to actual recipient
                fail_silently=False
            )
            messages.success(request, "Your profile update request has been sent successfully.")
            return redirect('payer_profile')  # Redirect after request submitted
    else:
        form = EditPayerProfileForm(instance=request.user)

    return render(request, 'edit_payer_profile.html', {'form': form})

@login_required
def ask_question_view(request):
    if request.user.user_type != 'payer':
        messages.error(request, 'Only payers can ask questions.')
        return redirect('payer_login')

    # Get only the logged-in payer's students
    my_students = Student.objects.filter(studentpayer__payer=request.user).distinct()
    student_choices = [(s.id, f"{s.first_name} {s.last_name} (Balance: ${s.current_balance:.2f} | Due: {s.due_date.strftime('%b %d, %Y') if s.due_date else 'No due date'})") for s in my_students]

    if request.method == 'POST':
        form = QuestionForm(student_choices, request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            student_ids = form.cleaned_data['students']
            message = form.cleaned_data['message']

            selected_students = Student.objects.filter(id__in=student_ids)
            student_lines = []
            for s in selected_students:
                balance = f"${s.current_balance:.2f}" if s.current_balance is not None else "N/A"
                due = s.due_date.strftime("%b %d, %Y") if s.due_date else "No due date"
                student_lines.append(f"{s.first_name} {s.last_name} – Balance: {balance}, Due: {due}")

            email_subject = f"Question from Payer: {subject}"
            email_body = f"""
A Payer has submitted a question from their dashboard:

User ID: {request.user.username}
Name: {request.user.get_full_name()}
Email: {request.user.email}

Students:
{chr(10).join(student_lines) if student_lines else 'None selected'}

Message:
{message}
""".strip()

            send_mail(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                ['info@waprep.org'],
                fail_silently=False,
            )

            messages.success(request, 'Your question has been submitted. We will contact you soon.')
            return redirect('payer_dashboard')
    else:
        form = QuestionForm(student_choices)

    # Return to payer_dashboard.html or a dedicated ask_question.html
    return render(request, 'payer_dashboard.html', {'form': form})

def add_vendor_view(request):
    if request.method == 'POST':
        vendor_data = {
            "name": request.POST['name'],
            "email": request.POST['email']
        }
        session_id = get_session_id()
        result = create_vendor(session_id, vendor_data)
        # Save to your local DB if needed
        return redirect('success_page')

    return render(request, 'add_vendor.html')

@login_required
def add_bank_account(request):
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank_account = form.save(commit=False)
            bank_account.payer = request.user  # assumes user is logged in as a payer
            # Store only last 4 digits for security
            full_account_number = request.POST.get('account_number')
            bank_account.account_number_last4 = full_account_number[-4:]
            bank_account.save()
            messages.success(request, "Bank account added successfully.")
            return redirect('make_payment')
    else:
        form = BankAccountForm()
    return render(request, 'add_bank_account.html', {'form': form})

@login_required
def add_payment_method(request):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    stripe_publishable_key = settings.STRIPE_PUBLISHABLE_KEY
    # Get or create Stripe customer
    customer_id = get_or_create_stripe_customer(request.user)
    # Create a SetupIntent for this customer with support for both cards and bank accounts
    setup_intent = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=['card', 'us_bank_account'],
        usage='off_session'  # Allow future payments
    )
    client_secret = setup_intent.client_secret
    
    if request.method == 'POST':
        payment_method_id = request.POST.get('payment_method_id')
        try:
            # Retrieve the PaymentMethod from Stripe
            pm = stripe.PaymentMethod.retrieve(payment_method_id)
            # Attach to customer (if not already attached)
            if not pm.customer:
                stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
            # Save to Card or BankAccount model
            if pm.type == 'card':
                card = pm.card
                brand = card.brand.title()
                last4 = card.last4
                exp_month = card.exp_month
                exp_year = card.exp_year
                Card.objects.create(
                    user=request.user,
                    nickname=f'{brand} ****{last4}',
                    last4=last4,
                    brand=brand,
                    exp_month=exp_month,
                    exp_year=exp_year,
                    stripe_payment_method_id=payment_method_id
                )
                messages.success(request, f'{brand} card ending in {last4} added successfully.')
            elif pm.type == 'us_bank_account':
                bank = pm.us_bank_account
                last4 = bank.last4
                account_type = bank.account_type
                BankAccount.objects.create(
                    user=request.user,
                    nickname=f'{account_type.title()} ****{last4}',
                    account_type=account_type,
                    last4=last4,
                    provider_token='',  # Not used with Stripe
                    stripe_payment_method_id=payment_method_id
                )
                messages.success(request, f'{account_type.title()} account ending in {last4} added successfully.')
            else:
                messages.error(request, f'Unsupported payment method type: {pm.type}')
            return redirect('payer_dashboard')
        except Exception as e:
            messages.error(request, f'Error adding payment method: {str(e)}')
    return render(request, 'add_payment_method.html', {
        'STRIPE_PUBLISHABLE_KEY': stripe_publishable_key,
        'STRIPE_CLIENT_SECRET': client_secret,
    })

def get_or_create_stripe_customer(user):
    if user.stripe_customer_id:
        return user.stripe_customer_id
    # Create customer in Stripe
    customer = stripe.Customer.create(
        email=user.email,
        name=user.get_full_name() or user.username
    )
    user.stripe_customer_id = customer.id
    user.save(update_fields=["stripe_customer_id"])
    return customer.id

@login_required
def manage_billing(request):
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    # Get search and sort parameters
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'student_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Get all students with their billing summary
    students = Student.objects.all()
    
    # Apply search filter
    if search_query:
        students = students.filter(
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(grade__icontains=search_query)
        )
    
    # Apply sorting to students
    if sort_by == 'student_name':
        if sort_order == 'desc':
            students = students.order_by('-last_name', '-first_name')
        else:
            students = students.order_by('last_name', 'first_name')
    elif sort_by == 'student_id':
        if sort_order == 'desc':
            students = students.order_by('-student_id')
        else:
            students = students.order_by('student_id')
    elif sort_by == 'grade':
        if sort_order == 'desc':
            students = students.order_by('-grade')
        else:
            students = students.order_by('grade')
    else:
        # Default sorting
        students = students.order_by('last_name', 'first_name')
    
    student_billing = []
    
    for student in students:
        # Get all bills for this student
        all_bills = student.payment_breakdowns.filter(due_date__isnull=False)
        
        # Calculate totals using correct payment logic
        total_bills = all_bills.count()
        total_amount = all_bills.aggregate(total=models.Sum('amount'))['total'] or 0
        
        # Count bills by payment status, respecting payment_status_override
        paid_bills = sum(1 for bill in all_bills if (bill.is_fully_paid or bill.payment_status_override == 'paid'))
        unpaid_bills = sum(1 for bill in all_bills if not (bill.is_fully_paid or bill.payment_status_override == 'paid'))
        
        # Calculate amounts using correct payment logic, respecting payment_status_override
        # For paid_amount: sum fully paid bills + paid portion of partially paid bills
        paid_amount = sum(
            bill.amount if (bill.is_fully_paid or bill.payment_status_override == 'paid') else (bill.amount - bill.remaining_amount)
            for bill in all_bills
        )
        unpaid_amount = sum(
            bill.remaining_amount if bill.payment_status_override == 'unpaid' else Decimal('0.00')
            for bill in all_bills 
            if not (bill.is_fully_paid or bill.payment_status_override == 'paid')
        )
        
        # Get unique months for this student
        months = all_bills.dates('due_date', 'month', order='DESC')
        
        student_billing.append({
            'student': student,
            'total_bills': total_bills,
            'total_amount': total_amount,
            'paid_bills': paid_bills,
            'unpaid_bills': unpaid_bills,
            'paid_amount': paid_amount,
            'unpaid_amount': unpaid_amount,
            'months_count': len(months),
            'months': months
        })
    
    # Apply additional sorting to student_billing list if needed
    if sort_by in ['total_amount', 'paid_amount', 'unpaid_amount', 'total_bills']:
        reverse_sort = sort_order == 'desc'
        student_billing.sort(key=lambda x: x[sort_by], reverse=reverse_sort)
    
    # Calculate overall statistics
    total_students = len(student_billing)
    total_all_bills = sum(s['total_bills'] for s in student_billing)
    total_all_amount = sum(s['total_amount'] for s in student_billing)
    total_all_paid = sum(s['paid_amount'] for s in student_billing)
    total_all_unpaid = sum(s['unpaid_amount'] for s in student_billing)
    
    context = {
        'student_billing': student_billing,
        'total_students': total_students,
        'total_all_bills': total_all_bills,
        'total_all_amount': total_all_amount,
        'total_all_paid': total_all_paid,
        'total_all_unpaid': total_all_unpaid,
        'search_query': search_query,
        'sort_by': sort_by,
        'sort_order': sort_order,
    }
    return render(request, 'manage_billing.html', context)

@login_required
def student_bills(request, student_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    student = get_object_or_404(Student, id=student_id)
    # Get all bills and sort them logically: overdue first, then by due date
    all_bills = student.payment_breakdowns.all()
    
    # Convert to list and sort by priority: overdue > unpaid > paid, then by due date
    bills_list = list(all_bills)
    from django.utils import timezone
    today = timezone.now().date()
    
    def sort_key(bill):
        # Overdue bills go first (priority 0)
        if bill.late_date and bill.late_date < today and not bill.is_fully_paid:
            days_overdue = (today - bill.late_date).days
            return (0, -days_overdue, bill.due_date or today)  # Negative for reverse sort
        
        # Current unpaid bills go second (priority 1)
        if not bill.is_fully_paid:
            return (1, 0, bill.due_date or today)
        
        # Paid bills go last (priority 2)
        return (2, 0, bill.due_date or today)
    
    bills_list.sort(key=sort_key)
    bills = bills_list
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date_str = request.POST.get('due_date')
            date_incurred_str = request.POST.get('date_incurred')
            late_date_str = request.POST.get('late_date')
            payment_status = request.POST.get('payment_status', 'unpaid')
            
            try:
                # Convert string dates to date objects
                from datetime import datetime
                
                due_date = None
                if due_date_str:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                
                date_incurred = None
                if date_incurred_str:
                    date_incurred = datetime.strptime(date_incurred_str, '%Y-%m-%d').date()
                else:
                    # Use today's date if not provided
                    date_incurred = datetime.now().date()
                
                late_date = None
                if late_date_str:
                    late_date = datetime.strptime(late_date_str, '%Y-%m-%d').date()
                
                PaymentBreakdown.objects.create(
                    student=student,
                    description=description,
                    amount=amount,
                    currency='USD',  # Default currency
                    due_date=due_date,
                    date_incurred=date_incurred,
                    late_date=late_date,
                    payment_status_override=payment_status,
                    is_paid=(payment_status == 'paid'),  # Keep is_paid for backward compatibility
                    show_in_payment_history=True  # Always show in payment history for new bills
                )
                messages.success(request, 'Bill added successfully.')
            except ValueError as e:
                messages.error(request, f'Invalid date format: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error adding bill: {str(e)}')
        elif action == 'edit':
            bill_id = request.POST.get('bill_id')
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date_str = request.POST.get('due_date')
            date_incurred_str = request.POST.get('date_incurred')
            late_date_str = request.POST.get('late_date')
            payment_status = request.POST.get('payment_status', 'unpaid')
            show_in_payment_history = request.POST.get('show_in_payment_history') == 'on'
            
            try:
                # Convert string dates to date objects
                from datetime import datetime
                
                due_date = None
                if due_date_str:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                
                date_incurred = None
                if date_incurred_str:
                    date_incurred = datetime.strptime(date_incurred_str, '%Y-%m-%d').date()
                else:
                    # Use today's date if not provided
                    date_incurred = datetime.now().date()
                
                late_date = None
                if late_date_str:
                    late_date = datetime.strptime(late_date_str, '%Y-%m-%d').date()
                
                bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                
                # Store the old payment status to check if it changed to 'paid'
                old_payment_status = bill.payment_status_override
                
                bill.description = description
                bill.amount = amount
                bill.due_date = due_date
                bill.date_incurred = date_incurred
                bill.late_date = late_date
                bill.payment_status_override = payment_status
                bill.is_paid = (payment_status == 'paid')  # Keep is_paid for backward compatibility
                bill.show_in_payment_history = show_in_payment_history
                bill.save()
                
                # If the bill was marked as 'paid', create a manual payment to zero out the remaining amount
                if payment_status == 'paid' and old_payment_status != 'paid':
                    manual_payment = create_manual_payment_for_bill(bill, student, request.user)
                    if manual_payment:
                        messages.success(request, f'Bill updated successfully. Manual payment of ${bill.remaining_amount} created to mark as paid.')
                    else:
                        messages.success(request, 'Bill updated successfully.')
                else:
                    messages.success(request, 'Bill updated successfully.')
                    
            except PaymentBreakdown.DoesNotExist:
                messages.error(request, 'Bill not found.')
            except ValueError as e:
                messages.error(request, f'Invalid date format: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error updating bill: {str(e)}')
        elif action == 'remove':
            bill_id = request.POST.get('bill_id')
            try:
                bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                bill.delete()
                messages.success(request, 'Bill removed successfully.')
            except Exception as e:
                messages.error(request, f'Error removing bill: {str(e)}')
        elif action == 'add_payment':
            payer_id = request.POST.get('payer_id')
            amount = request.POST.get('amount')
            payment_date = request.POST.get('payment_date')
            status = 'completed'  # Always completed since payment status option is removed
            payment_method = request.POST.get('payment_method', 'manual')
            notes = request.POST.get('notes', '')
            bill_ids = request.POST.getlist('bill_ids')
            
            # Enhanced validation for amount
            try:
                amount_float = float(amount) if amount else 0
            except (ValueError, TypeError):
                amount_float = 0
            
            # Validate amount is greater than 0
            if not amount or amount_float <= 0:
                messages.error(request, 'Payment amount must be greater than $0.')
                return redirect('student_bills', student_id=student.id)
            
            # Additional safety check - ensure amount is reasonable
            if amount_float > 100000:  # $100,000 limit
                messages.error(request, 'Payment amount exceeds maximum allowed limit.')
                return redirect('student_bills', student_id=student.id)
            
            try:
                payer = User.objects.get(id=payer_id, user_type='payer')
                
                # Create the payment
                payment = Payment.objects.create(
                    student=student,
                    payer=payer,
                    amount=amount,
                    payment_date=payment_date,
                    status=status,
                    payment_method=payment_method,
                    notes=notes,
                    receipt_number=f"MANUAL-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    currency='USD'  # Default to USD for manual payments
                )
                
                # Create payment items for each selected bill
                total_paid = 0
                for bill_id in bill_ids:
                    bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                    bill_amount = request.POST.get(f'bill_amount_{bill_id}', bill.amount)
                    
                    PaymentItem.objects.create(
                        payment=payment,
                        breakdown_item=bill,
                        amount_paid=bill_amount,
                        currency='USD'  # Default to USD
                    )
                    
                    total_paid += float(bill_amount)
                    
                    # Mark bill as paid if payment status is completed
                    if status == 'completed':
                        bill.is_paid = True
                        bill.save()
                
                # Update student's current balance
                if status == 'completed':
                    student.current_balance = student.current_balance - total_paid
                    student.save()
                
                messages.success(request, f'Payment of ${amount} added successfully for {payer.first_name} {payer.last_name}.')
                
            except User.DoesNotExist:
                messages.error(request, 'Selected payer not found.')
            except PaymentBreakdown.DoesNotExist:
                messages.error(request, 'One or more selected bills not found.')
            except Exception as e:
                messages.error(request, f'Error adding payment: {str(e)}')
        
        return redirect('student_bills', student_id=student.id)
    
    # Get payments for this student, grouped by month
    payments_by_month = {}
    payments = Payment.objects.filter(student=student).order_by('-payment_date')
    
    for payment in payments:
        month_key = payment.payment_date.strftime('%Y-%m')
        if month_key not in payments_by_month:
            payments_by_month[month_key] = []
        payments_by_month[month_key].append(payment)
    
    # Get payers associated with this student
    student_payers = User.objects.filter(
        studentpayer__student=student,
        user_type='payer'
    ).order_by('first_name', 'last_name')
    
    context = {
        'student': student,
        'bills': bills,
        'payments_by_month': payments_by_month,
        'student_payers': student_payers,
    }
    return render(request, 'student_bills.html', context)

def reset_password(request, token):
    try:
        # Find the password reset record
        password_reset = PasswordReset.objects.get(token=token, used=False)
        
        # Check if token is expired
        if password_reset.is_expired():
            messages.error(request, 'Password reset link has expired. Please request a new one.')
            return redirect('forgot_password')
        
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
            else:
                # Use the new password validation with user parameter
                user = password_reset.user
                is_valid, message = validate_password(new_password, user)
                if not is_valid:
                    messages.error(request, message)
                else:
                    # Store password in history before changing it
                    from .models import PasswordHistory
                    PasswordHistory.store_password(user, new_password)
                    
                    # Set new password
                    user.set_password(new_password)
                    user.save()
                    
                    # Mark token as used
                    password_reset.used = True
                    password_reset.save()
                    
                    messages.success(request, 'Password has been reset successfully with secure password. You can now log in with your new password.')
                    return redirect('payer_login')
        
        return render(request, 'reset_password.html', {'token': token})
        
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid or expired password reset link.')
        return redirect('forgot_password')
    except Exception as e:
        messages.error(request, f'Error resetting password: {str(e)}')
        return redirect('forgot_password')

def create_test_user(request):
    """Simple view to create a test user - REMOVE IN PRODUCTION"""
    if request.method == 'POST':
        try:
            # Create a test payer user
            user_id = generate_unique_user_id("Test", "Payer")
            user = User.objects.create_user(
                username=user_id,
                first_name="Test",
                last_name="Payer",
                email="test@example.com",
                password="Test123!@#",
                user_type='payer',
                user_id=user_id,
                is_active=True
            )
            
            # Create a test admin user
            admin_user = User.objects.create_user(
                username="admin@waprep.org",
                first_name="Admin",
                last_name="User",
                email="admin@waprep.org",
                password="Admin123!@#",
                user_type='admin',
                user_id="admin@waprep.org",
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            
            return render(request, 'create_test_users_success.html', {
                'payer_user_id': user_id,
                'payer_email': 'test@example.com',
                'payer_password': 'Test123!@#',
                'admin_email': 'admin@waprep.org',
                'admin_password': 'Admin123!@#'
            })
            
        except Exception as e:
            return render(request, 'create_test_users_error.html', {
                'error': str(e)
            })
    
    return render(request, 'create_test_users.html')
def create_superuser_view(request):
    """Web view to create a superuser for staging server"""
    # Only allow in staging/production environments
    if not settings.DEBUG:
        # Check for a secret token in the URL or environment
        token = request.GET.get('token') or request.POST.get('token')
        expected_token = config('SUPERUSER_TOKEN', default='WAPrep2024!')
        
        if token != expected_token:
            return HttpResponse('Unauthorized', status=403)
    
    if request.method == 'POST':
        email = request.POST.get('email', 'admin@waprep.org')
        password = request.POST.get('password', 'WAPrep2024!')
        first_name = request.POST.get('first_name', 'Admin')
        last_name = request.POST.get('last_name', 'User')
        
        try:
            # Check if superuser already exists
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                if user.is_superuser:
                    messages.warning(request, f'Superuser with email {email} already exists.')
                else:
                    # Make existing user a superuser
                    user.is_superuser = True
                    user.is_staff = True
                    user.user_type = 'admin'
                    user.set_password(password)
                    user.save()
                    messages.success(request, f'Existing user {email} has been promoted to superuser.')
            else:
                # Create new superuser
                user = User.objects.create_superuser(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    user_type='admin',
                    user_id='ADMIN01'
                )
                messages.success(request, f'Superuser created successfully! Email: {email}, Password: {password}')
            
            return redirect('admin_login')
            
        except Exception as e:
            messages.error(request, f'Error creating superuser: {str(e)}')
    
    return render(request, 'create_superuser.html')

@login_required
def manage_payment_methods(request):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    # Get or create Stripe customer
    customer_id = get_or_create_stripe_customer(request.user)
    
    # Get saved payment methods from Stripe
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type='card'
        )
        
        bank_accounts = stripe.PaymentMethod.list(
            customer=customer_id,
            type='us_bank_account'
        )
        
        # Combine and sort by creation date
        all_payment_methods = []
        
        for pm in payment_methods.data:
            all_payment_methods.append({
                'id': pm.id,
                'type': 'card',
                'brand': pm.card.brand.title(),
                'last4': pm.card.last4,
                'exp_month': pm.card.exp_month,
                'exp_year': pm.card.exp_year,
                'created': pm.created,
                'status': 'active'
            })
        
        for pm in bank_accounts.data:
            all_payment_methods.append({
                'id': pm.id,
                'type': 'bank_account',
                'bank_name': pm.us_bank_account.bank_name,
                'last4': pm.us_bank_account.last4,
                'account_type': pm.us_bank_account.account_type,
                'created': pm.created,
                'status': pm.us_bank_account.status
            })
        
        # Sort by creation date (newest first)
        all_payment_methods.sort(key=lambda x: x['created'], reverse=True)
        
    except Exception as e:
        messages.error(request, f'Error loading payment methods: {str(e)}')
        all_payment_methods = []
    
    # Get local database records for comparison
    local_cards = Card.objects.filter(user=request.user)
    local_bank_accounts = BankAccount.objects.filter(user=request.user)
    
    context = {
        'payment_methods': all_payment_methods,
        'local_cards': local_cards,
        'local_bank_accounts': local_bank_accounts,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'manage_payment_methods.html', context)

@login_required
def complete_bank_verification(request, payment_method_id):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    try:
        # Retrieve the payment method
        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
        
        # Check if it's a bank account that needs verification
        if payment_method.type == 'us_bank_account' and payment_method.us_bank_account.status == 'new':
            # Create a SetupIntent to complete verification
            customer_id = get_or_create_stripe_customer(request.user)
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method=payment_method_id,
                usage='off_session'
            )
            
            context = {
                'payment_method': payment_method,
                'setup_intent': setup_intent,
                'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
                'STRIPE_CLIENT_SECRET': setup_intent.client_secret,
            }
            return render(request, 'complete_bank_verification.html', context)
        else:
            messages.error(request, 'This payment method does not require verification or is not a bank account.')
            return redirect('manage_payment_methods')
            
    except Exception as e:
        messages.error(request, f'Error completing verification: {str(e)}')
        return redirect('manage_payment_methods')

@login_required
def remove_payment_method(request, payment_method_id):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    if request.method == 'POST':
        try:
            # Detach from Stripe customer
            stripe.PaymentMethod.detach(payment_method_id)
            
            # Remove from local database
            Card.objects.filter(stripe_payment_method_id=payment_method_id).delete()
            BankAccount.objects.filter(stripe_payment_method_id=payment_method_id).delete()
            
            messages.success(request, 'Payment method removed successfully.')
        except Exception as e:
            messages.error(request, f'Error removing payment method: {str(e)}')
    
    return redirect('manage_payment_methods')

@login_required
def inline_edit_payment_notes(request):
    """Handle AJAX request to update payment notes inline"""
    print(f"inline_edit_payment_notes called - method: {request.method}, user: {request.user}")
    
    if request.user.user_type != 'admin':
        print("Permission denied - user is not admin")
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'POST':
        try:
            import json
            print(f"Request body: {request.body}")
            data = json.loads(request.body)
            payment_id = data.get('payment_id')
            notes = data.get('notes', '').strip()
            
            print(f"Payment ID: {payment_id}, Notes: {notes}")
            
            payment = get_object_or_404(Payment, id=payment_id)
            payment.notes = notes if notes else None
            payment.save()
            
            print(f"Payment {payment_id} notes updated successfully")
            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Error in inline_edit_payment_notes: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    print("Invalid request method")
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks to update payment statuses"""
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    # Get the webhook secret from settings
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    if not webhook_secret:
        # For development, allow webhook without secret
        if settings.DEBUG:
            webhook_secret = 'whsec_test'  # Dummy secret for development
        else:
            return HttpResponse(status=500)
    
    # Get the webhook payload
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)
    
    # Handle the event
    print(f"Webhook received: {event['type']}")  # Debug logging
    
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        print(f"Payment succeeded: {payment_intent['id']}")  # Debug logging
        
        # Update payment status to completed
        try:
            payment = Payment.objects.get(receipt_number=payment_intent['id'])
            payment.status = 'completed'
            payment.save()
            print(f"Payment {payment.id} updated to completed")  # Debug logging
            
            # If this payment doesn't have PaymentItem records yet, create them
            if not PaymentItem.objects.filter(payment=payment).exists():
                # Get current month's payment items
                now = timezone.now()
                current_month = now.month
                current_year = now.year
                payment_items = PaymentBreakdown.objects.filter(
                    student=payment.student,
                    is_paid=False,
                    due_date__year=current_year,
                    due_date__month=current_month
                )
                
                # Create PaymentItem records to link payment to breakdown items
                total_payment_amount = payment.amount
                payment_items_list = list(payment_items)
                
                if payment_items_list:
                    # Calculate how much each item should be paid
                    total_items_amount = sum(item.amount for item in payment_items_list)
                    
                    for item in payment_items_list:
                        if total_items_amount > 0:
                            # Calculate proportional amount for this item
                            item_amount = (item.amount / total_items_amount) * total_payment_amount
                            # Round to 2 decimal places
                            item_amount = round(item_amount, 2)
                        else:
                            item_amount = Decimal('0.00')
                        
                        # Create PaymentItem record
                        PaymentItem.objects.create(
                            payment=payment,
                            breakdown_item=item,
                            amount_paid=item_amount,
                            currency='USD'  # Default to USD
                        )
                    
                    # Mark payment items as paid
                    payment_items.update(is_paid=True)
                    print(f"Payment {payment.id} bills marked as paid")  # Debug logging
            else:
                # Mark existing payment breakdown items as paid
                payment_items = PaymentItem.objects.filter(payment=payment)
                for payment_item in payment_items:
                    payment_item.breakdown_item.is_paid = True
                    payment_item.breakdown_item.save()
                
        except Payment.DoesNotExist:
            # Payment record doesn't exist, create it
            student_id = payment_intent['metadata'].get('student_id')
            if student_id:
                student = Student.objects.get(id=student_id)
                # Get the user from metadata
                user_id = payment_intent['metadata'].get('user_id')
                payer = None
                if user_id:
                    try:
                        payer = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        pass
                
                payment = Payment.objects.create(
                    student=student,
                    payer=payer,  # Set the payer from metadata
                    amount=Decimal(payment_intent['amount']) / 100,
                    status='completed',
                    receipt_number=payment_intent['id']
                )
                
                # Create payment items for current month's bills
                now = timezone.now()
                current_month = now.month
                current_year = now.year
                payment_items = PaymentBreakdown.objects.filter(
                    student=student,
                    is_paid=False,
                    due_date__year=current_year,
                    due_date__month=current_month
                )
                
                total_payment_amount = Decimal(payment_intent['amount']) / 100
                payment_items_list = list(payment_items)
                
                if payment_items_list:
                    total_items_amount = sum(item.amount for item in payment_items_list)
                    
                    for item in payment_items_list:
                        if total_items_amount > 0:
                            item_amount = (item.amount / total_items_amount) * total_payment_amount
                            item_amount = round(item_amount, 2)
                        else:
                            item_amount = Decimal('0.00')
                        
                        PaymentItem.objects.create(
                            payment=payment,
                            breakdown_item=item,
                            amount_paid=item_amount,
                            currency='USD'  # Default to USD
                        )
                    
                    payment_items.update(is_paid=True)
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        # Update payment status to failed
        try:
            payment = Payment.objects.get(receipt_number=payment_intent['id'])
            payment.status = 'failed'
            payment.save()
        except Payment.DoesNotExist:
            pass  # Payment record doesn't exist, nothing to update
    
    return HttpResponse(status=200)


# Monitoring and Health Check Views

def health_check(request):
    """
    Health check endpoint for monitoring systems.
    """
    try:
        from .utils import log_system_health
        from .models import AuditLog, SecurityEvent, SystemHealth
        import psutil
        
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': {}
        }
        
        # Database health check
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            health_status['checks']['database'] = {'status': 'healthy', 'message': 'Database connection OK'}
        except Exception as e:
            health_status['checks']['database'] = {'status': 'critical', 'message': f'Database error: {str(e)}'}
            health_status['status'] = 'critical'
        
        # System resource checks
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_status = 'healthy'
            if memory.percent > 90:
                memory_status = 'critical'
            elif memory.percent > 80:
                memory_status = 'warning'
            
            health_status['checks']['memory'] = {
                'status': memory_status,
                'message': f'Memory usage: {memory.percent:.1f}%',
                'usage_percent': memory.percent
            }
            
            if memory_status != 'healthy':
                health_status['status'] = 'warning'
            
            # Disk usage
            disk = psutil.disk_usage('.')
            disk_status = 'healthy'
            if disk.percent > 90:
                disk_status = 'critical'
            elif disk.percent > 80:
                disk_status = 'warning'
            
            health_status['checks']['disk'] = {
                'status': disk_status,
                'message': f'Disk usage: {disk.percent:.1f}%',
                'usage_percent': disk.percent
            }
            
            if disk_status != 'healthy':
                health_status['status'] = 'warning'
                
        except Exception as e:
            health_status['checks']['system'] = {'status': 'critical', 'message': f'System check error: {str(e)}'}
            health_status['status'] = 'critical'
        
        # Audit system health
        try:
            recent_logs = AuditLog.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
            
            recent_security_events = SecurityEvent.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
            
            audit_status = 'healthy'
            if recent_security_events > 10:
                audit_status = 'warning'
            
            health_status['checks']['audit_system'] = {
                'status': audit_status,
                'message': f'Audit logs: {recent_logs}, Security events: {recent_security_events}',
                'recent_logs': recent_logs,
                'recent_security_events': recent_security_events
            }
            
        except Exception as e:
            health_status['checks']['audit_system'] = {'status': 'critical', 'message': f'Audit system error: {str(e)}'}
            health_status['status'] = 'critical'
        
        # Log the health check
        try:
            log_system_health(
                'health_check_endpoint',
                health_status['status'].upper(),
                f"Health check completed with status: {health_status['status']}",
                health_status['checks']
            )
        except Exception as e:
            # Don't fail the health check if logging fails
            health_status['checks']['logging'] = {'status': 'warning', 'message': f'Logging error: {str(e)}'}
        
        return JsonResponse(health_status)
        
    except Exception as e:
        # Catch any unexpected errors and return a proper error response
        error_response = {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }
        return JsonResponse(error_response, status=500)


def custom_404(request, exception):
    """
    Custom 404 error handler.
    """
    return render(request, '404.html', status=404)
@login_required
def audit_summary(request):
    """
    Audit summary endpoint for monitoring dashboard.
    """
    from .utils import get_audit_summary
    
    # Only allow admin users
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    days = int(request.GET.get('days', 30))
    summary = get_audit_summary(days)
    
    return JsonResponse(summary)


@login_required
def security_events(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    # Get recent security events
    from .models import SecurityEvent
    events = SecurityEvent.objects.all().order_by('-timestamp')[:50]
    
    context = {
        'events': events,
    }
    return render(request, 'security_events.html', context)

@login_required
def mass_add_bills(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        try:
            # Get form data
            description = request.POST.get('description', '').strip()
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            show_in_payment_history = request.POST.get('show_in_payment_history') == 'on'
            
            # Validate required fields
            if not description:
                messages.error(request, 'Description is required.')
                return redirect('manage_billing')
            
            if not amount or float(amount) <= 0:
                messages.error(request, 'Amount must be greater than 0.')
                return redirect('manage_billing')
            
            if not due_date:
                messages.error(request, 'Due date is required.')
                return redirect('manage_billing')
            
            # Get selected student IDs from the form
            student_ids = request.POST.get('student_ids', '').split(',')
            student_ids = [sid.strip() for sid in student_ids if sid.strip()]
            
            if not student_ids:
                messages.error(request, 'No students selected.')
                return redirect('manage_billing')
            
            success_count = 0
            error_count = 0
            error_details = []
            
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id)
                    PaymentBreakdown.objects.create(
                        student=student,
                        description=description,
                        amount=amount,
                        currency='USD',  # Default currency
                        due_date=due_date,
                        is_paid=False,
                        show_in_payment_history=show_in_payment_history
                    )
                    success_count += 1
                except Student.DoesNotExist:
                    error_count += 1
                    error_details.append(f"Student ID {student_id} not found")
                except Exception as e:
                    error_count += 1
                    error_details.append(f"Student {student_id}: {str(e)}")
                    print(f"Error adding bill to student {student_id}: {str(e)}")
            
            # Show detailed success/error messages
            if success_count > 0:
                messages.success(request, f'Successfully added bills to {success_count} student(s).')
            if error_count > 0:
                error_msg = f'Failed to add bills to {error_count} student(s).'
                if len(error_details) <= 3:  # Show details if not too many
                    error_msg += f' Details: {", ".join(error_details)}'
                messages.warning(request, error_msg)
                
        except Exception as e:
            messages.error(request, f'Error adding bills: {str(e)}')
    
    return redirect('manage_billing')

@login_required
def mass_billing_actions(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        student_ids = request.POST.get('student_ids', '').split(',')
        student_ids = [sid.strip() for sid in student_ids if sid.strip()]
        
        if not student_ids:
            messages.error(request, 'No students selected.')
            return redirect('manage_billing')
        
        if action == 'send_reminders':
            success_count = 0
            error_count = 0
            no_bills_count = 0
            no_payers_count = 0
            error_details = []
            
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id)
                    
                    # Get all payers for this student
                    student_payers = StudentPayer.objects.filter(student=student)
                    
                    if not student_payers.exists():
                        no_payers_count += 1
                        continue
                    
                    # Get unpaid bills for this student
                    unpaid_bills = PaymentBreakdown.objects.filter(
                        student=student,
                        is_paid=False
                    ).order_by('due_date')
                    
                    if not unpaid_bills.exists():
                        no_bills_count += 1
                        continue
                    
                    # Calculate total unpaid amount
                    total_unpaid = unpaid_bills.aggregate(total=models.Sum('amount'))['total'] or 0
                    
                    # Send reminders to all active payers
                    payer_emails_sent = 0
                    for student_payer in student_payers:
                        payer = student_payer.payer
                        
                        # Only send to active payers
                        if not payer.is_active:
                            continue
                        
                        # Create bill reminder email
                        subject = 'WAPrep Tuition Portal - Bill Reminder'
                        message = f"""
Hello {payer.first_name},

This is a reminder that you have outstanding bills for {student.first_name} {student.last_name} at Washington Preparatory School.

Total Outstanding Amount: ${total_unpaid:.2f}

Outstanding Bills:
"""
                        
                        for bill in unpaid_bills:
                            message += f"- {bill.description}: ${bill.amount:.2f} (Due: {bill.due_date.strftime('%B %d, %Y')})\n"
                        
                        message += f"""

To view and pay these bills, please log in to your account at:
{request.build_absolute_uri('/')}

If you have any questions, please contact us.

Best regards,
WAPrep Administration
                        """.strip()
                        
                        try:
                            send_mail(
                                subject,
                                message,
                                settings.DEFAULT_FROM_EMAIL,
                                [payer.email],
                                fail_silently=False,
                            )
                            payer_emails_sent += 1
                        except Exception as e:
                            error_details.append(f"Failed to send to {payer.email}: {str(e)}")
                            print(f"Error sending reminder to {payer.email}: {str(e)}")
                    
                    if payer_emails_sent > 0:
                        success_count += 1
                    else:
                        error_count += 1
                            
                except Student.DoesNotExist:
                    error_count += 1
                    error_details.append(f"Student ID {student_id} not found")
                except Exception as e:
                    error_count += 1
                    error_details.append(f"Student {student_id}: {str(e)}")
                    print(f"Error processing student {student_id}: {str(e)}")
            
            # Show detailed success/error messages
            if success_count > 0:
                messages.success(request, f'Successfully sent bill reminders for {success_count} student(s).')
            if no_bills_count > 0:
                messages.info(request, f'{no_bills_count} student(s) have no unpaid bills.')
            if no_payers_count > 0:
                messages.info(request, f'{no_payers_count} student(s) have no associated payers.')
            if error_count > 0:
                error_msg = f'Failed to send reminders for {error_count} student(s).'
                if len(error_details) <= 3:  # Show details if not too many
                    error_msg += f' Details: {", ".join(error_details)}'
                messages.warning(request, error_msg)
        else:
            messages.error(request, 'Invalid action specified.')
    
    return redirect('manage_billing')

@login_required
def payer_view_upcoming_bills(request, student_id):
    """View for payers to see upcoming bills by month for a specific student"""
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    # Check if the payer is associated with this student
    try:
        student_payer = StudentPayer.objects.get(student_id=student_id, payer=request.user)
    except StudentPayer.DoesNotExist:
        messages.error(request, 'You do not have access to this student.')
        return redirect('payer_dashboard')
    
    student = get_object_or_404(Student, id=student_id)
    
    # Define the billing cycle: June 2025 to May 2026
    import calendar
    billing_cycle_months = []
    
    # Add June 2025 to December 2025
    for month in range(6, 13):  # June (6) to December (12)
        month_key = f"2025-{month:02d}"
        month_display = f"{calendar.month_name[month]} 2025"
        billing_cycle_months.append((month_key, month_display))
    
    # Add January 2026 to May 2026
    for month in range(1, 6):  # January (1) to May (5)
        month_key = f"2026-{month:02d}"
        month_display = f"{calendar.month_name[month]} 2026"
        billing_cycle_months.append((month_key, month_display))

    # Get all bills for this student with due dates
    all_bills = student.payment_breakdowns.filter(due_date__isnull=False).order_by('due_date')
    
    # Group bills by month
    monthly_billing = {}
    for bill in all_bills:
        month_key = bill.due_date.strftime('%Y-%m')
        month_display = bill.due_date.strftime('%B %Y')
        if month_key not in monthly_billing:
            monthly_billing[month_key] = {
                'month_display': month_display,
                'month_key': month_key,
                'bills': [],
                'total_amount': 0,
                'paid_amount': 0,
                'unpaid_amount': 0,
                'total_bills': 0,
                'paid_bills': 0,
                'unpaid_bills': 0
            }
        monthly_billing[month_key]['bills'].append(bill)
        monthly_billing[month_key]['total_amount'] += bill.amount  # Keep original amount for total
        monthly_billing[month_key]['total_bills'] += 1
        if bill.is_fully_paid or bill.payment_status_override == 'paid':
            monthly_billing[month_key]['paid_amount'] += bill.amount
            monthly_billing[month_key]['paid_bills'] += 1
        else:
            if bill.payment_status_override == 'unpaid':
                monthly_billing[month_key]['unpaid_amount'] += bill.remaining_amount  # Use remaining amount for unpaid
            else:
                monthly_billing[month_key]['unpaid_amount'] += Decimal('0.00')
            monthly_billing[month_key]['unpaid_bills'] += 1

    # Sort bills within each month by status (unpaid first, then paid)
    from django.utils import timezone
    today = timezone.now().date()
    
    def sort_bills_by_status(bill):
        # Unpaid bills go first (priority 0)
        if not bill.is_fully_paid:
            # Overdue bills go first within unpaid
            if bill.is_overdue:
                days_overdue = (today - bill.late_date).days if bill.late_date else 0
                return (0, -days_overdue, bill.due_date or today)  # Negative for reverse sort
            # Current unpaid bills go second
            return (1, 0, bill.due_date or today)
        # Paid bills go last (priority 2)
        return (2, 0, bill.due_date or today)
    
    # Sort bills in each month
    for month_data in monthly_billing.values():
        month_data['bills'].sort(key=sort_bills_by_status)

    # Get current month for default expansion
    from datetime import datetime
    current_month_key = datetime.now().strftime('%Y-%m')
    
    # Create the final sorted months list in billing cycle order
    sorted_months = []
    for month_key, month_display in billing_cycle_months:
        if month_key in monthly_billing:
            # Month has bills, use existing data
            month_data = monthly_billing[month_key].copy()
            month_data['is_current_month'] = (month_key == current_month_key)
            sorted_months.append((month_key, month_data))
        else:
            # Month has no bills, create empty entry
            sorted_months.append((month_key, {
                'month_display': month_display,
                'month_key': month_key,
                'bills': [],
                'total_amount': 0,
                'paid_amount': 0,
                'unpaid_amount': 0,
                'total_bills': 0,
                'paid_bills': 0,
                'unpaid_bills': 0,
                'is_current_month': (month_key == current_month_key)
            }))
    
    # Calculate student totals using remaining amounts for unpaid bills, respecting payment_status_override
    total_bills = all_bills.count()
    total_amount = all_bills.aggregate(total=models.Sum('amount'))['total'] or 0
    paid_bills = sum(1 for bill in all_bills if (bill.is_fully_paid or bill.payment_status_override == 'paid'))
    unpaid_bills = sum(1 for bill in all_bills if not (bill.is_fully_paid or bill.payment_status_override == 'paid'))
    paid_amount = sum(
        bill.amount if (bill.is_fully_paid or bill.payment_status_override == 'paid') else (bill.amount - bill.remaining_amount)
        for bill in all_bills
    )
    unpaid_amount = sum(
        bill.remaining_amount if bill.payment_status_override == 'unpaid' else Decimal('0.00')
        for bill in all_bills 
        if not (bill.is_fully_paid or bill.payment_status_override == 'paid')
    )
    
    context = {
        'student': student,
        'monthly_billing': sorted_months,
        'total_bills': total_bills,
        'total_amount': total_amount,
        'paid_bills': paid_bills,
        'unpaid_bills': unpaid_bills,
        'paid_amount': paid_amount,
        'unpaid_amount': unpaid_amount,
    }
    return render(request, 'payer_upcoming_bills.html', context)

def create_manual_payment_for_bill(bill, student, admin_user):
    """
    Create a manual payment to mark a bill as paid when payment_status_override is set to 'paid'.
    This ensures the remaining_amount is zeroed out and financial totals are updated correctly.
    """
    try:
        # Check if there's already a manual payment for this bill
        existing_payment = PaymentItem.objects.filter(
            breakdown_item=bill,
            payment__payment_method='manual',
            payment__notes__icontains='Status override payment'
        ).first()
        
        if existing_payment:
            # Update existing payment if needed
            return existing_payment.payment
        
        # Get the first payer associated with this student
        payer = User.objects.filter(
            studentpayer__student=student,
            user_type='payer'
        ).first()
        
        if not payer:
            # If no payer exists, create a system payment
            payer = None
        
        # Calculate the amount needed to fully pay the bill
        remaining_amount = bill.remaining_amount
        if remaining_amount <= 0:
            return None  # Bill is already fully paid
        
        # Create the payment
        payment = Payment.objects.create(
            student=student,
            payer=payer,
            amount=remaining_amount,
            payment_date=timezone.now().date(),
            status='completed',
            payment_method='manual',
            notes=f'Status override payment - {admin_user.first_name} {admin_user.last_name} marked bill as paid',
            receipt_number=f"OVERRIDE-{timezone.now().strftime('%Y%m%d%H%M%S%f')}",
            currency='USD'
        )
        
        # Create payment item
        PaymentItem.objects.create(
            payment=payment,
            breakdown_item=bill,
            amount_paid=remaining_amount,
            currency='USD'
        )
        
        # Update student's current balance
        student.current_balance = student.current_balance - remaining_amount
        student.save()
        
        logger.info(f"Created manual payment of ${remaining_amount} for bill {bill.id} (Status override)")
        return payment
        
    except Exception as e:
        logger.error(f"Error creating manual payment for bill {bill.id}: {str(e)}")
        return None



