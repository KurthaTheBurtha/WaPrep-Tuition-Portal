from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Student, Payment, StudentPayer, BankAccount, PaymentBreakdown, Card, PaymentItem, PasswordReset
import random
import string
from django.core.mail import send_mail
from django.db import models
from .forms import AccountRequestForm, ProfileCompletionForm
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
from .utils import validate_password, generate_strong_password
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt

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
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')

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
    
    now = timezone.now()
    current_month = now.month
    current_year = now.year
    breakdown_items = PaymentBreakdown.objects.filter(
        student=student,
        is_paid=False,
        due_date__year=current_year,
        due_date__month=current_month
    ).order_by('due_date')
    total_amount_due = breakdown_items.aggregate(total=Sum('amount'))['total'] or 0
    
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
    
    context = {
        'student_name': f"{student.first_name} {student.last_name}",
        'total_amount_due': total_amount_due,
        'breakdown_items': breakdown_items,
        'student_id': student_id,
        'current_month': now.strftime('%B %Y'),
        'STRIPE_PUBLISHABLE_KEY': stripe_publishable_key,
        'STRIPE_CLIENT_SECRET': client_secret,
    }
    return render(request, 'payment.html', context)

@login_required
def process_payment(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        amount = request.POST.get('amount')
        payment_intent_id = request.POST.get('payment_intent_id')
        saved_payment_method_id = request.POST.get('saved_payment_method_id')
        
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
                    amount=int(float(amount) * 100),
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
            
            # Check if payment was successful
            if payment_intent.status == 'succeeded':
                # Payment was successful, now create database records
                
                # Get payment method details for display purposes only (not stored)
                pm = stripe.PaymentMethod.retrieve(payment_intent.payment_method)
                payment_method_type = pm.type
                
                # Get current month's payment items
                now = timezone.now()
                current_month = now.month
                current_year = now.year
                payment_items = PaymentBreakdown.objects.filter(
                    student=student,
                    is_paid=False,
                    due_date__year=current_year,
                    due_date__month=current_month
                )
                
                # Create payment record only after confirming success
                payment = Payment.objects.create(
                    student=student,
                    amount=amount,
                    status='completed',
                    bank_account=None,  # No bank account reference stored
                    receipt_number=payment_intent.id
                )
                
                # Create PaymentItem records to link payment to breakdown items
                total_payment_amount = Decimal(str(amount))
                payment_items_list = list(payment_items)
                
                if payment_items_list:
                    # Calculate how much each item should be paid
                    # For now, we'll distribute the payment proportionally across all items
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
                            amount_paid=item_amount
                        )
                    
                    # Mark payment items as paid
                    payment_items.update(is_paid=True)
                
                # Determine payment method type for success message
                payment_method_name = "payment method"
                if payment_method_type == 'card':
                    payment_method_name = f"{pm.card.brand.title()} card ending in {pm.card.last4}"
                elif payment_method_type == 'us_bank_account':
                    payment_method_name = f"bank account ending in {pm.us_bank_account.last4}"
                
                messages.success(request, f"✅ Payment of ${amount} completed successfully using {payment_method_name}. A receipt is now available.")
                return redirect('payment_history')
                
            elif payment_intent.status == 'processing':
                # Payment is being processed (common for bank transfers)
                # Create a pending payment record so it shows up in payment history
                payment = Payment.objects.create(
                    student=student,
                    amount=amount,
                    status='pending',
                    bank_account=None,  # No bank account reference stored
                    receipt_number=payment_intent.id
                )
                
                messages.info(request, f"Payment of ${amount} is being processed. You'll receive a confirmation once it's completed.")
                return redirect('payment_history')
                
            elif payment_intent.status == 'requires_capture':
                # Payment requires capture (for manual capture scenarios)
                messages.warning(request, f"Payment of ${amount} requires manual capture. Please contact support.")
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
    
    # Check and update pending payment statuses
    pending_payments = Payment.objects.filter(
        student__in=my_students,
        status='pending'
    )
    
    for payment in pending_payments:
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment.receipt_number)
            if payment_intent.status == 'succeeded':
                payment.status = 'completed'
                payment.save()
                
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
                                amount_paid=item_amount
                            )
                        
                        # Mark payment items as paid
                        payment_items.update(is_paid=True)
                
            elif payment_intent.status == 'failed':
                payment.status = 'failed'
                payment.save()
        except:
            pass  # Ignore errors, continue with the view
    
    # Get all payments for students associated with this payer
    # This will include all payment types: Stripe payments, saved bank account payments, etc.
    payments = Payment.objects.filter(
        student__in=my_students
    ).order_by('-payment_date')
    
    # Get bills that are marked as paid and should show in payment history
    paid_bills = PaymentBreakdown.objects.filter(
        student__in=my_students,
        is_paid=True,
        show_in_payment_history=True
    ).order_by('-updated_at')  # Use updated_at as the "payment date" for bills
    
    # Create a combined list of payments and bills for display
    all_transactions = []
    
    # Add regular payments
    for payment in payments:
        all_transactions.append({
            'type': 'payment',
            'object': payment,
            'date': payment.payment_date,
            'amount': payment.amount,
            'student': payment.student,
            'status': payment.status,
            'description': f'Payment - {payment.student.first_name} {payment.student.last_name}',
            'receipt_number': payment.receipt_number,
        })
    
    # Add paid bills that should show in history
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
    
    context = {
        'payments': payments,
        'my_students': my_students,
        'all_transactions': all_transactions,
    }
    return render(request, 'payment_history.html', context)

@login_required
def download_receipt(request, payment_id):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    payment = get_object_or_404(Payment, id=payment_id)
    # Check that the user is allowed to access this payment
    if not Student.objects.filter(id=payment.student.id, studentpayer__payer=request.user).exists():
        messages.error(request, 'You do not have permission to access this receipt.')
        return redirect('payment_history')
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
    p.drawString(50, y, f'Payer: {request.user.get_full_name()} ({request.user.email})')
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
def admin_dashboard(request):
    # Only accessible by admins
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
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
            models.Q(student_id__icontains=search_query) |
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
        except:
            messages.error(request, 'Invalid birthday format')
            return redirect('students')

        try:
            # Create student
            student = Student.objects.create(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=birthday_date,
                grade=grade,
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
def payer_dashboard(request):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('payer_login')
    
    # Get students already associated with this payer
    my_students = Student.objects.filter(studentpayer__payer=request.user).distinct()

    # Get current month and year using system datetime instead of Django timezone
    # Django timezone.now() seems to be showing incorrect date
    from datetime import datetime
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    today = current_date.date()

    # Calculate total amount owed and get payment breakdowns
    total_amount_owed = 0
    current_month_total = 0
    
    for student in my_students:
        # Get all unpaid payment breakdown items
        breakdown_items = student.payment_breakdowns.filter(is_paid=False)
        # Get current month's items
        current_month_items = breakdown_items.filter(
            due_date__month=current_month,
            due_date__year=current_year
        )
        # Get overdue items
        overdue_items = breakdown_items.filter(due_date__lt=today)
        student.overdue_items = overdue_items
        # Calculate tuition/boarding total (case-insensitive search)
        tuition_boarding_items = breakdown_items.filter(
            models.Q(description__icontains='tuition') | models.Q(description__icontains='boarding')
        )
        tuition_boarding_total = tuition_boarding_items.aggregate(total=Sum('amount'))['total'] or 0
        student.total_due = tuition_boarding_total
        # Calculate other totals
        student_month_total = current_month_items.aggregate(total=Sum('amount'))['total'] or 0
        total_amount_owed += tuition_boarding_total
        current_month_total += student_month_total
        # Add breakdown items to student object for template access
        student.breakdown_items = breakdown_items
        student.current_month_items = current_month_items
        student.monthly_due = student_month_total
    
    context = {
        'my_students': my_students,
        'total_amount_owed': total_amount_owed,
        'current_month_total': current_month_total,
        'current_month': current_date.strftime('%B %Y'),
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
                config('DEFAULT_FROM_EMAIL'),  # Uses DEFAULT_FROM_EMAIL
                ['kschimmel@waprep.org'],
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

def profile_completion(request):
    # Allow both active and inactive users who are logged in
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to access this page.')
        return redirect('payer_login')
    
    if request.user.user_type != 'payer':
        messages.error(request, 'Only payers can access this page.')
        return redirect('payer_login')

    if request.method == 'POST':
        form = ProfileCompletionForm(request.POST, user=request.user)
        if form.is_valid():
            # Set the new password
            new_password = form.cleaned_data.get('new_password1')
            if new_password:
                # Store password in history before changing it
                from .models import PasswordHistory
                PasswordHistory.store_password(request.user, new_password)
                
                request.user.set_password(new_password)
                # Activate the user when they set their password
                request.user.is_active = True
                request.user.save()
            
            # Re-authenticate the user with the new password
            login(request, request.user)
            
            messages.success(request, 'Profile completed successfully with secure password! You can now access your dashboard.')
            return redirect('payer_dashboard')
    else:
        form = ProfileCompletionForm(user=request.user)

    return render(request, 'profile_completion.html', {'form': form})

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
            
            # Set the field value
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
    ).order_by('due_date')
    
    # Calculate totals
    total_amount = bills.aggregate(total=models.Sum('amount'))['total'] or 0
    paid_amount = bills.filter(is_paid=True).aggregate(total=models.Sum('amount'))['total'] or 0
    unpaid_amount = bills.filter(is_paid=False).aggregate(total=models.Sum('amount'))['total'] or 0
    total_bills = bills.count()
    paid_bills = bills.filter(is_paid=True).count()
    unpaid_bills = bills.filter(is_paid=False).count()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            show_in_payment_history = request.POST.get('show_in_payment_history') == 'on'
            try:
                PaymentBreakdown.objects.create(
                    student=student,
                    description=description,
                    amount=amount,
                    due_date=due_date,
                    is_paid=False,
                    show_in_payment_history=show_in_payment_history
                )
                messages.success(request, 'Bill added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding bill: {str(e)}')
        elif action == 'edit':
            bill_id = request.POST.get('bill_id')
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            is_paid = request.POST.get('is_paid') == 'on'
            show_in_payment_history = request.POST.get('show_in_payment_history') == 'on'
            try:
                bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                bill.description = description
                bill.amount = amount
                bill.due_date = due_date
                bill.is_paid = is_paid
                bill.show_in_payment_history = show_in_payment_history
                bill.save()
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
        
        return redirect('monthly_bills', student_id=student_id, month_key=month_key)
    
    context = {
        'student': student,
        'month_key': month_key,
        'month_display': month_display,
        'bills': bills,
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
    
    # Get all bills for this student with due dates
    all_bills = student.payment_breakdowns.filter(due_date__isnull=False).order_by('-due_date')
    
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
        
        if bill.is_paid:
            monthly_billing[month_key]['paid_bills'] += 1
            monthly_billing[month_key]['paid_amount'] += bill.amount
        else:
            monthly_billing[month_key]['unpaid_bills'] += 1
            monthly_billing[month_key]['unpaid_amount'] += bill.amount
    
    # Sort by month key (earliest first)
    sorted_months = sorted(monthly_billing.items(), key=lambda x: x[0], reverse=False)
    
    # Calculate student totals
    total_bills = all_bills.count()
    total_amount = all_bills.aggregate(total=models.Sum('amount'))['total'] or 0
    paid_bills = all_bills.filter(is_paid=True).count()
    unpaid_bills = all_bills.filter(is_paid=False).count()
    paid_amount = all_bills.filter(is_paid=True).aggregate(total=models.Sum('amount'))['total'] or 0
    unpaid_amount = all_bills.filter(is_paid=False).aggregate(total=models.Sum('amount'))['total'] or 0
    
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
                ['kschimmel@waprep.org'],  # change to actual recipient
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
    my_students = Student.objects.filter(StudentPayer__payer=request.user).distinct()
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
                ['kschimmel@waprep.org'],
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
    
    # Get all students with their billing summary
    students = Student.objects.all().order_by('last_name', 'first_name')
    student_billing = []
    
    for student in students:
        # Get all bills for this student
        all_bills = student.payment_breakdowns.filter(due_date__isnull=False)
        
        # Calculate totals
        total_bills = all_bills.count()
        total_amount = all_bills.aggregate(total=models.Sum('amount'))['total'] or 0
        paid_bills = all_bills.filter(is_paid=True).count()
        unpaid_bills = all_bills.filter(is_paid=False).count()
        paid_amount = all_bills.filter(is_paid=True).aggregate(total=models.Sum('amount'))['total'] or 0
        unpaid_amount = all_bills.filter(is_paid=False).aggregate(total=models.Sum('amount'))['total'] or 0
        
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
    }
    return render(request, 'manage_billing.html', context)

@login_required
def student_bills(request, student_id):
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    student = get_object_or_404(Student, id=student_id)
    bills = student.payment_breakdowns.all().order_by('-due_date')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            show_in_payment_history = request.POST.get('show_in_payment_history') == 'on'
            try:
                PaymentBreakdown.objects.create(
                    student=student,
                    description=description,
                    amount=amount,
                    due_date=due_date,
                    is_paid=False,
                    show_in_payment_history=show_in_payment_history
                )
                messages.success(request, 'Bill added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding bill: {str(e)}')
        elif action == 'edit':
            bill_id = request.POST.get('bill_id')
            description = request.POST.get('description')
            amount = request.POST.get('amount')
            due_date = request.POST.get('due_date')
            is_paid = request.POST.get('is_paid') == 'on'
            show_in_payment_history = request.POST.get('show_in_payment_history') == 'on'
            try:
                bill = PaymentBreakdown.objects.get(id=bill_id, student=student)
                bill.description = description
                bill.amount = amount
                bill.due_date = due_date
                bill.is_paid = is_paid
                bill.show_in_payment_history = show_in_payment_history
                bill.save()
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
        return redirect('student_bills', student_id=student.id)
    context = {
        'student': student,
        'bills': bills,
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
                            amount_paid=item_amount
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
                payment = Payment.objects.create(
                    student=student,
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
                            amount_paid=item_amount
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

