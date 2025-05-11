from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from .models import User, Student, Payment, StudentParent
import random
import string
from django.core.mail import send_mail
from django.db import models

# Create your views here.

def home(request):
    return render(request, 'tuition/select_login.html', {'show_navbar': False})

def parent_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password) and user.user_type == 'parent':
                login(request, user)
                
                if not remember:
                    request.session.set_expiry(0)  # Session expires when browser closes
                
                return redirect('tuition:parent_dashboard')  # Redirect to parent dashboard
            else:
                messages.error(request, 'Invalid email or password for parent account.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password for parent account.')
    
    return render(request, 'tuition/parent_login.html', {'hide_nav_items': True})

def parent_signup(request):
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
            user.user_type = 'parent'
            user.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect('tuition:parent_dashboard')

    return render(request, 'tuition/parent_signup.html')

def accountant_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password) and user.user_type == 'accountant':
                login(request, user)
                
                if not remember:
                    request.session.set_expiry(0)  # Session expires when browser closes
                
                return redirect('tuition:students')  # Redirect to students page
            else:
                messages.error(request, 'Invalid email or password for accountant account.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password for accountant account.')
    
    return render(request, 'tuition/accountant_login.html', {'hide_nav_items': True})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('tuition:home')

@login_required
def payment(request):
    # Only allow parent users
    if request.user.user_type != 'parent':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:accountant_login')
        
    # In a real application, these would come from a database
    context = {
        'amount_due': 500.00,
        'due_date': (timezone.now() + timedelta(days=15)).strftime('%B %d, %Y')
    }
    return render(request, 'tuition/payment.html', context)

@login_required
def process_payment(request):
    # Only allow parent users
    if request.user.user_type != 'parent':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:accountant_login')
        
    if request.method == 'POST':
        # In a real application, you would:
        # 1. Validate the payment details
        # 2. Process the payment through a payment gateway
        # 3. Store the payment record in the database
        # 4. Send a confirmation email
        messages.success(request, 'Payment processed successfully!')
        return redirect('tuition:payment_history')
    return redirect('tuition:payment')

@login_required
def payment_history(request):
    # Only allow parent users
    if request.user.user_type != 'parent':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:accountant_login')
        
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
    return render(request, 'tuition/payment_history.html', {'payments': payments})

@login_required
def download_receipt(request, payment_id):
    # Only allow parent users
    if request.user.user_type != 'parent':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:accountant_login')
        
    # In a real application, you would:
    # 1. Fetch the payment details from the database
    # 2. Generate a PDF receipt
    # 3. Return the PDF file
    return HttpResponse("Receipt download functionality will be implemented here")

@login_required
def accountant_dashboard(request):
    # Only accessible by accountants
    if request.user.user_type != 'accountant':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:parent_login')
    
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
    return render(request, 'tuition/accountant_dashboard.html', context)

def forgot_password(request):
    return render(request, 'tuition/forgot_password.html')

@login_required
def students(request):
    if request.user.user_type != 'accountant':
        messages.error(request, 'Only accountants can access this page.')
        return redirect('tuition:accountant_login')
    
    students = Student.objects.all()
    parents = User.objects.filter(user_type='parent')
    
    context = {
        'students': students,
        'parents': parents,
    }
    return render(request, 'tuition/students.html', context)

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
        parent_id = request.POST.get('parent_id')
        relationship = request.POST.get('relationship', 'other')
        is_primary = request.POST.get('is_primary', False) == 'on'

        # Generate student ID
        try:
            birthday_date = datetime.strptime(birthday, '%Y-%m-%d')
            student_id = generate_student_id(first_name, last_name, birthday_date)
        except:
            messages.error(request, 'Invalid birthday format')
            return redirect('tuition:students')

        try:
            # Create student
            student = Student.objects.create(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=birthday_date,
                grade=grade,
            )

            # Add parent relationship
            if parent_id:
                parent = User.objects.get(id=parent_id)
                StudentParent.objects.create(
                    student=student,
                    parent=parent,
                    relationship=relationship,
                    is_primary=is_primary
                )

            messages.success(request, 'Student added successfully')
        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
            return redirect('tuition:students')
            
        return redirect('tuition:students')
    return redirect('tuition:students')

@login_required
def delete_student(request):
    # Only allow parent users
    if request.user.user_type != 'accountant':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:home')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = get_object_or_404(Student, id=student_id)
            student_name = f"{student.first_name} {student.last_name}"
            student.delete()
            messages.success(request, f'Student {student_name} deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting student: {str(e)}')
    
    return redirect('tuition:students')

def select_login(request):
    return render(request, 'tuition/select_login.html', {'show_navbar': False})

@login_required
def update_student_notes(request):
    # Only allow accountant users
    if request.user.user_type != 'accountant':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:parent_login')
    
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
    
    return redirect('tuition:students')

@login_required
def update_student(request):
    # Only allow accountant users
    if request.user.user_type != 'accountant':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:accountant_login')
    
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
    
    return redirect('tuition:students')

@login_required
def add_parent_to_student(request):
    # Only allow accountant users
    if request.user.user_type != 'accountant':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:accountant_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        parent_id = request.POST.get('parent_id')
        relationship = request.POST.get('relationship')
        is_primary = request.POST.get('is_primary', False) == 'on'
        
        try:
            student = get_object_or_404(Student, id=student_id)
            parent = get_object_or_404(User, id=parent_id)
            
            # If this is set as primary, unset any existing primary parent
            if is_primary:
                StudentParent.objects.filter(student=student, is_primary=True).update(is_primary=False)
            
            StudentParent.objects.create(
                student=student,
                parent=parent,
                relationship=relationship,
                is_primary=is_primary
            )
            messages.success(request, f'Added {parent.get_full_name()} as {relationship} for {student}')
        except Exception as e:
            messages.error(request, f'Error adding parent: {str(e)}')
    
    return redirect('tuition:students')

@login_required
def remove_parent_from_student(request):
    # Only allow accountant users
    if request.user.user_type != 'accountant':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:accountant_login')
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        parent_id = request.POST.get('parent_id')
        
        try:
            student = get_object_or_404(Student, id=student_id)
            parent = get_object_or_404(User, id=parent_id)
            
            # Don't allow removing the last parent
            if student.parents.count() <= 1:
                messages.error(request, 'Cannot remove the last parent from a student')
                return redirect('tuition:students')
            
            StudentParent.objects.filter(student=student, parent=parent).delete()
            messages.success(request, f'Removed {parent.get_full_name()} from {student}')
        except Exception as e:
            messages.error(request, f'Error removing parent: {str(e)}')
    
    return redirect('tuition:students')

@login_required
def accountant_reports(request):
    # Only allow accountant users
    if request.user.user_type != 'accountant':
        messages.error(request, 'Only accountants can access this page.')
        return redirect('tuition:accountant_login')
    
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
    return render(request, 'tuition/accountant_reports.html', context)

@login_required
def parent_dashboard(request):
    # Only allow parent users
    if request.user.user_type != 'parent':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:parent_login')
    
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Get all students that are not already associated with this parent
    available_students = Student.objects.exclude(
        studentparent__parent=request.user
    ).order_by('first_name', 'last_name')
    
    # If there's a search query, filter the students
    if search_query:
        available_students = available_students.filter(
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(student_id__icontains=search_query)
        )
    
    # Get students already associated with this parent
    my_students = Student.objects.filter(studentparent__parent=request.user).distinct()

    
    context = {
        'available_students': available_students,
        'my_students': my_students,
        'search_query': search_query,
    }
    return render(request, 'tuition/parent_dashboard.html', context)

@login_required
def add_student_to_parent(request):
    # Only allow parent users
    if request.user.user_type != 'parent':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('tuition:parent_login')
    

    if request.method == 'POST':
        print("POST to add_student_to_parent received:", request.POST)
        student_id = request.POST.get('student_id')
        relationship = request.POST.get('relationship', 'other')
        is_primary = request.POST.get('is_primary', False) == 'on'
        
        try:
            student = get_object_or_404(Student, id=student_id)
            
            # Check if the student is already linked to this parent
            if StudentParent.objects.filter(student=student, parent=request.user).exists():
                messages.warning(request, f'{student.first_name} {student.last_name} is already linked to your account.')
                return redirect('tuition:parent_dashboard')

            # If this is set as primary, unset any existing primary parent
            if is_primary:
                StudentParent.objects.filter(student=student, is_primary=True).update(is_primary=False)
            
            # Create the parent-student relationship
            StudentParent.objects.create(
                student=student,
                parent=request.user,
                relationship=relationship,
                is_primary=is_primary
            )
            messages.success(request, f'Successfully added {student.first_name} {student.last_name} to your account')
        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
    
    return redirect('tuition:parent_dashboard')
