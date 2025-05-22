from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('parent', 'Parent'),
        ('accountant', 'Accountant'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    def is_accountant(self):
        return self.user_type == 'accountant'

class Student(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    
    student_id = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    grade = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, help_text="Accountant's notes about the student")
    parents = models.ManyToManyField(User, through='StudentParent', related_name='students')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class StudentParent(models.Model):
    RELATIONSHIP_CHOICES = (
        ('mother', 'Mother'),
        ('father', 'Father'),
        ('guardian', 'Guardian'),
        ('other', 'Other'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey(User, on_delete=models.CASCADE)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'parent')
        ordering = ['-is_primary', 'relationship']

    def __str__(self):
        return f"{self.parent.get_full_name()} - {self.get_relationship_display()} of {self.student}"

class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    receipt_number = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.student} - {self.amount}"

class PaymentReceipt(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='receipt')
    file = models.FileField(upload_to='receipts/')
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt for {self.payment}"

class PaymentReminder(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='reminders')
    reminder_date = models.DateField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reminder for {self.payment}"

class PaymentPlan(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payment_plans')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_installments = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Payment.STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment Plan for {self.student}"

class PaymentInstallment(models.Model):
    payment_plan = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE, related_name='installments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='installment')
    status = models.CharField(max_length=20, choices=Payment.STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Installment {self.id} for {self.payment_plan}"

class AccountRequest(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    child_first_name = models.CharField(max_length=100)
    child_last_name = models.CharField(max_length=100)
    email = models.EmailField()
    contact_info = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - Account Request"