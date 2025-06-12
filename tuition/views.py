from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Student, Payment, Studentpayer, BankAccount, PaymentBreakdown
import random
import string
from django.core.mail import send_mail
from django.db import models
from .forms import AccountRequestForm
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



# Create your views here.

def home(request):
    return render(request, 'select_login.html', {'show_navbar': False})

def payer_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.user_type == 'payer':
            login(request, user)

            if not remember:
                request.session.set_expiry(0)  # Session expires when browser closes

            return redirect('payer_welcome')
        else:
            messages.error(request, 'Invalid username or password for payer account.')

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
    student = get_object_or_404(Student, id=student_id)
    
    # Get current month and year
    now = timezone.now()
    current_month = now.month
    current_year = now.year
    
    # Get only current month's payment breakdown items
    breakdown_items = PaymentBreakdown.objects.filter(
        student=student,
        is_paid=False,
        due_date__year=current_year,
        due_date__month=current_month
    ).order_by('due_date')
    
    # Calculate total amount due for current month
    total_amount_due = breakdown_items.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get user's saved bank accounts
    bank_accounts = BankAccount.objects.filter(user=request.user)
    
    context = {
        'student_name': f"{student.first_name} {student.last_name}",
        'total_amount_due': total_amount_due,
        'breakdown_items': breakdown_items,
        'bank_accounts': bank_accounts,
        'student_id': student_id,
        'current_month': now.strftime('%B %Y')  # e.g., "March 2024"
    }
    
    return render(request, 'payment.html', context)

@login_required
def process_payment(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        
        try:
            # Get BILL session
            session_id = get_session_id()
            
            if payment_method == 'new':
                # Use new bank account details
                name = request.POST.get('account_holder')
                routing_number = request.POST.get('routing_number')
                account_number = request.POST.get('account_number')
                account_type = request.POST.get('account_type')
                
                # Save new bank account if user is a payer
                if request.user.user_type == 'payer':
                    bank_account = BankAccount.objects.create(
                        user=request.user,
                        nickname=f"{name}'s {account_type.capitalize()}",
                        account_type=account_type,
                        last4=account_number[-4:],
                        provider_token=f"{routing_number}_{account_number}"
                    )
            else:
                # Use existing bank account
                bank_account = BankAccount.objects.get(id=payment_method, user=request.user)
                name = request.user.get_full_name()
                token_parts = bank_account.provider_token.split('_')
                routing_number = token_parts[0]
                account_number = token_parts[1]
                account_type = bank_account.account_type
            
            # Create vendor
            vendor_id = create_vendor(session_id, {
                "name": name,
                "email": request.user.email
            })
            
            # Create bank account in BILL
            bank_response = create_bank_account(session_id, vendor_id, {
                "bankAccountNumber": account_number,
                "routingNumber": routing_number,
                "accountType": account_type,
                "bankAccountName": name
            })
            
            # Create bill
            bill_id = create_bill(session_id, vendor_id, {
                "amount": str(amount),
                "description": f"Tuition payment for {student.first_name} {student.last_name}"
            })
            
            # Process payment
            payment_response = pay_bill(session_id, bill_id)
            
            # Create payment record
            payment = Payment.objects.create(
                student=student,
                amount=amount,
                status='pending',
                bank_account=bank_account if 'bank_account' in locals() else None,
                routing_number=routing_number,
                account_number=account_number,
                account_type=account_type,
                receipt_number=payment_response.get('id', '')  # Use BILL payment ID as receipt number
            )
            
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
        return redirect('admin_login')
        
    # In a real application, this would come from a database
    payments = [
        {
            'id': 1,
            'date': 'Feb 15, 2024',
            'amount': 500.00,
            'status': 'Completed'
        },
        {
            'id': 2,
            'date': 'Jan 15, 2024',
            'amount': 500.00,
            'status': 'Completed'
        }
    ]
    return render(request, 'payment_history.html', {'payments': payments})

@login_required
def download_receipt(request, payment_id):
    # Only allow payer users
    if request.user.user_type != 'payer':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
        
    # In a real application, you would:
    # 1. Fetch the payment details from the database
    # 2. Generate a PDF receipt
    # 3. Return the PDF file
    return HttpResponse("Receipt download functionality will be implemented here")

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
    
    students = Student.objects.all()
    payers = User.objects.filter(user_type='payer')
    
    context = {
        'students': students,
        'payers': payers,
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
                Studentpayer.objects.create(
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

@login_required
def add_payer_to_student(request):
    # Only allow admin users
    if request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        payer_id = request.POST.get('payer_id')
        relationship = request.POST.get('relationship')
        is_primary = request.POST.get('is_primary', False) == 'on'
        
        try:
            student = get_object_or_404(Student, id=student_id)
            payer = get_object_or_404(User, id=payer_id)
            
            # If this is set as primary, unset any existing primary payer
            if is_primary:
                Studentpayer.objects.filter(student=student, is_primary=True).update(is_primary=False)
            
            Studentpayer.objects.create(
                student=student,
                payer=payer,
                relationship=relationship,
                is_primary=is_primary
            )
            messages.success(request, f'Added {payer.get_full_name()} as {relationship} for {student}')
        except Exception as e:
            messages.error(request, f'Error adding payer: {str(e)}')
    
    return redirect('students')

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
            
            Studentpayer.objects.filter(student=student, payer=payer).delete()
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
    
    # Get students already associated with this payer
    my_students = Student.objects.filter(studentpayer__payer=request.user).distinct()

    # Get current month and year
    current_date = timezone.now()
    current_month = current_date.month
    current_year = current_date.year

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
        
        # Calculate totals
        student_total = breakdown_items.aggregate(total=Sum('amount'))['total'] or 0
        student_month_total = current_month_items.aggregate(total=Sum('amount'))['total'] or 0
        
        total_amount_owed += student_total
        current_month_total += student_month_total
        
        # Add breakdown items to student object for template access
        student.breakdown_items = breakdown_items
        student.current_month_items = current_month_items
        student.total_due = student_total
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
            if Studentpayer.objects.filter(student=student, payer=request.user).exists():
                messages.warning(request, f'{student.first_name} {student.last_name} is already linked to your account.')
                return redirect('payer_dashboard')

            # If this is set as primary, unset any existing primary payer
            if is_primary:
                Studentpayer.objects.filter(student=student, is_primary=True).update(is_primary=False)
            
            # Create the payer-student relationship
            Studentpayer.objects.create(
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
    if request.user.user_type != 'payer':
        return redirect('admin_login')  # or show 403
    return render(request, 'payer_welcome.html')

@login_required
def payer_profile_view(request):
    if request.user.user_type != 'payer':
        return redirect('payer_dashboard')  # or return 403

    if request.method == 'POST':
        form = PayerProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('payer_profile')
    else:
        form = PayerProfileForm(instance=request.user)

    return render(request, 'payer_profile.html', {'form': form})

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