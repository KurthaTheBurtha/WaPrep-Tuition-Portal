from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Student, Payment, StudentPayer, BankAccount, PaymentBreakdown, Card, PaymentItem
import random
import string
from django.core.mail import send_mail
from django.db import models
from .forms import AccountRequestForm, ProfileCompletionForm
from django.conf import settings
from .forms import PayerProfileForm, EditPayerProfileForm, QuestionForm
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

def payer_signup(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
        else:
            user = User.objects.create_user(username=email, first_name=first_name, last_name=last_name, email=email, password=password)
            user.user_type = 'payer'
            user.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect('payer_dashboard')

    return render(request, 'payer_signup.html')

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
    
    # Check if user has completed their profile
    if not request.user.phone_number or not request.user.address:
        messages.warning(request, 'Please complete your profile before making payments.')
        return redirect('profile_completion')
    
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
        try:
            # Retrieve the PaymentIntent from Stripe
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if payment_intent.status not in ['succeeded', 'processing', 'requires_capture']:
                messages.error(request, f"Payment failed or incomplete. Status: {payment_intent.status}")
                return redirect('payment', student_id=student_id)
            # Get payment method details
            pm = stripe.PaymentMethod.retrieve(payment_intent.payment_method)
            # Save payment record
            from .models import Card, BankAccount
            bank_account = None
            card = None
            payment_method_type = pm.type
            if payment_method_type == 'card':
                card_obj, _ = Card.objects.get_or_create(
                    user=request.user,
                    stripe_payment_method_id=pm.id,
                    defaults={
                        'nickname': f"{pm.card.brand.title()} ****{pm.card.last4}",
                        'last4': pm.card.last4,
                        'brand': pm.card.brand.title(),
                        'exp_month': pm.card.exp_month,
                        'exp_year': pm.card.exp_year,
                    }
                )
                card = card_obj
            elif payment_method_type == 'us_bank_account':
                bank_obj, _ = BankAccount.objects.get_or_create(
                    user=request.user,
                    stripe_payment_method_id=pm.id,
                    defaults={
                        'nickname': f"Bank ****{pm.us_bank_account.last4}",
                        'account_type': pm.us_bank_account.account_type,
                        'last4': pm.us_bank_account.last4,
                        'provider_token': '',
                    }
                )
                bank_account = bank_obj
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
            # Create payment record
            payment = Payment.objects.create(
                student=student,
                amount=amount,
                status='completed' if payment_intent.status == 'succeeded' else 'pending',
                bank_account=bank_account,
                receipt_number=payment_intent.id
            )
            
            # Create PaymentItem records to link payment to breakdown items
            total_payment_amount = float(amount)
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
                        item_amount = 0
                    
                    # Create PaymentItem record
                    PaymentItem.objects.create(
                        payment=payment,
                        breakdown_item=item,
                        amount_paid=item_amount
                    )
                
                # Mark payment items as paid
                payment_items.update(is_paid=True)
            
            messages.success(request, f"✅ Payment of ${amount} submitted successfully. A receipt will be available once the payment is processed.")
            return redirect('payment_history')
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
    
    # Check if user has completed their profile
    if not request.user.phone_number or not request.user.address:
        messages.warning(request, 'Please complete your profile before viewing payment history.')
        return redirect('profile_completion')
    
    # Get all students associated with this payer
    my_students = Student.objects.filter(studentpayer__payer=request.user).distinct()
    
    # Get payments made by this payer (through their bank accounts or direct payment info)
    # First, get payments made through saved bank accounts
    bank_account_payments = Payment.objects.filter(
        bank_account__user=request.user
    )
    
    # Also get payments where the payer might have used direct payment info
    # This is a fallback for payments that don't have a bank_account reference
    direct_payments = Payment.objects.filter(
        student__in=my_students,
        bank_account__isnull=True  # Only payments without bank account reference
    )
    
    # Combine both querysets and order by payment date
    payments = (bank_account_payments | direct_payments).distinct().order_by('-payment_date')
    
    context = {
        'payments': payments,
        'my_students': my_students,
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
    p.drawString(50, y, 'Waprep Tuition Payment Receipt')
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
    return render(request, 'forgot_password.html')

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
    Generate a unique user ID based on first and last name.
    Format: First letter of first name + first letter of last name + last 4 digits of last name + random 3 digits
    Example: John Smith -> JSith123
    """
    # Clean and normalize names
    first_name = first_name.strip().upper()
    last_name = last_name.strip().upper()
    
    # Get first letter of first name
    first_initial = first_name[0] if first_name else 'X'
    
    # Get first letter of last name
    last_initial = last_name[0] if last_name else 'X'
    
    # Get last 4 characters of last name (or pad with X if shorter)
    last_part = last_name[-4:] if len(last_name) >= 4 else last_name.ljust(4, 'X')
    
    # Generate base user ID
    base_user_id = f"{first_initial}{last_initial}{last_part}"
    
    # Add random 3 digits to ensure uniqueness
    counter = 1
    while True:
        if counter == 1:
            user_id = base_user_id
        else:
            user_id = f"{base_user_id}{counter:03d}"
        
        if not User.objects.filter(user_id=user_id).exists():
            return user_id
        
        counter += 1
        if counter > 999:  # Prevent infinite loop
            # Fallback to original random method
            return 'P' + ''.join(random.choices(string.digits, k=7))

@login_required
def add_payer_to_student(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        relationship = request.POST.get('relationship')
        is_primary = request.POST.get('is_primary', False) == 'on'
        
        try:
            student = get_object_or_404(Student, id=student_id)
            
            # Check if user already exists
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
                    user_id=user_id
                )
                # Send activation email
                activation_url = request.build_absolute_uri(f'/activate-account/{payer.id}/{temp_password}/')
                subject = 'Welcome to WaPrep Tuition Portal - Activate Your Account'
                message = f"""
Hello {first_name},

Welcome to the Washington Preparatory School Tuition Portal!

You have been added as a payer for {student.first_name} {student.last_name}.

Your User ID: {user_id}
Your Temporary Password: {temp_password}

To activate your account, please click the following link:
{activation_url}

After activation, you will be required to:
1. Change your password
2. Add your phone number (required)
3. Add your address (required)
4. Add any additional contact information (optional)

If you have any questions, please contact us.

Best regards,
WaPrep Administration
                """.strip()
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            
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
                messages.success(request, f'Added {payer.get_full_name()} as {relationship} for {student}. Activation email sent to {email}.')
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
        subject = 'WaPrep Tuition Portal - Account Activation'
        message = f"""
Hello {payer.first_name},

You have been added as a payer for {student.first_name} {student.last_name} at Washington Preparatory School.

Your User ID: {payer.user_id}
Your Temporary Password: {temp_password}

To activate your account, please click the following link:
{activation_url}

After activation, you will be required to:
1. Change your password
2. Add your phone number (required)
3. Add your address (required)
4. Add any additional contact information (optional)

If you have any questions, please contact us.

Best regards,
WaPrep Administration
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
            # Log the user in
            login(request, user)
            # Redirect to profile completion
            messages.success(request, 'Account activated successfully! Please complete your profile.')
            return redirect('profile_completion')
        else:
            messages.error(request, 'Invalid activation link.')
            return redirect('payer_login')
    except Exception as e:
        messages.error(request, 'Error activating account.')
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
    selected_year = request.GET.get('year', timezone.now().year)
    
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
        start_year = timezone.now().year
    end_year = timezone.now().year
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
    
    # Check if user has completed their profile (phone number and address are required)
    if not request.user.phone_number or not request.user.address:
        messages.warning(request, 'Please complete your profile before accessing the dashboard.')
        return redirect('profile_completion')
    
    # Get students already associated with this payer
    my_students = Student.objects.filter(studentpayer__payer=request.user).distinct()

    # Get current month and year
    current_date = timezone.now()
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
Other Contact Info: {request_obj.contact_info}

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
        messages.warning(request, 'Please change your password and complete your profile (address and phone required) before continuing.')
        return redirect('payer_profile')
    return render(request, 'payer_welcome.html')

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
            # If password is being changed, clear the force flag
            new_password = request.POST.get('new_password')
            if new_password:
                user.set_password(new_password)
                user.save()
                request.session['force_password_change'] = False
                messages.success(request, 'Password changed successfully!')
                login(request, user)
            # Check required fields
            if user.phone_number and user.address:
                request.session['force_password_change'] = False
                messages.success(request, 'Profile updated successfully!')
            else:
                messages.warning(request, 'Please complete your address and phone number to continue.')
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
Phone Number: {cleaned_data.get('phone_number')}
Address: {cleaned_data.get('address')}
Contact Info: {cleaned_data.get('contact_info')}

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
    
    # Check if user has completed their profile
    if not request.user.phone_number or not request.user.address:
        messages.warning(request, 'Please complete your profile before adding payment methods.')
        return redirect('profile_completion')
    
    stripe_publishable_key = settings.STRIPE_PUBLISHABLE_KEY
    # Get or create Stripe customer
    customer_id = get_or_create_stripe_customer(request.user)
    # Create a SetupIntent for this customer
    setup_intent = stripe.SetupIntent.create(customer=customer_id)
    client_secret = setup_intent.client_secret
    print('DEBUG STRIPE_PUBLISHABLE_KEY:', stripe_publishable_key)
    print('DEBUG STRIPE_CLIENT_SECRET:', client_secret)
    if request.method == 'POST':
        payment_method_id = request.POST.get('payment_method_id')
        nickname = request.POST.get('nickname')
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
                    nickname=nickname or f'{brand} ****{last4}',
                    last4=last4,
                    brand=brand,
                    exp_month=exp_month,
                    exp_year=exp_year,
                    stripe_payment_method_id=payment_method_id
                )
                messages.success(request, 'Card added successfully.')
            elif pm.type == 'us_bank_account':
                bank = pm.us_bank_account
                last4 = bank.last4
                account_type = bank.account_type
                BankAccount.objects.create(
                    user=request.user,
                    nickname=nickname or f'Bank ****{last4}',
                    account_type=account_type,
                    last4=last4,
                    provider_token='',  # Not used with Stripe
                    stripe_payment_method_id=payment_method_id
                )
                messages.success(request, 'Bank account added successfully.')
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
    students = Student.objects.all()
    # Calculate total amount owed for each student
    student_billing = []
    for student in students:
        total_owed = student.payment_breakdowns.filter(is_paid=False).aggregate(total=models.Sum('amount'))['total'] or 0
        student_billing.append({
            'student': student,
            'total_owed': total_owed,
        })
    context = {
        'student_billing': student_billing,
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
            try:
                PaymentBreakdown.objects.create(
                    student=student,
                    description=description,
                    amount=amount,
                    due_date=due_date,
                    is_paid=False
                )
                messages.success(request, 'Bill added successfully.')
            except Exception as e:
                messages.error(request, f'Error adding bill: {str(e)}')
        elif action == 'remove':
            bill_id = request.POST.get('bill_id')
            try:
                bill = PaymentBreakdown.objects.get(id=bill_id)
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

@login_required
def profile_completion(request):
    if request.user.user_type != 'payer':
        messages.error(request, 'Only payers can access this page.')
        return redirect('payer_login')

    if request.method == 'POST':
        form = ProfileCompletionForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Set the new password
            new_password = form.cleaned_data.get('new_password1')
            if new_password:
                user.set_password(new_password)
            
            user.save()
            
            # Re-authenticate the user with the new password
            login(request, user)
            
            messages.success(request, 'Profile completed successfully! You can now access your dashboard.')
            return redirect('payer_dashboard')
    else:
        form = ProfileCompletionForm(instance=request.user)

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