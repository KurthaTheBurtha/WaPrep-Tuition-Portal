from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.conf import settings

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('payer', 'Payer'),
        ('admin', 'Admin'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    contact_info = models.TextField(blank=True)
    user_id = models.CharField(max_length=30, unique=True, null=True, blank=False)
    stripe_customer_id = models.CharField(max_length=64, blank=True, null=True)
     
    def is_admin(self):
        return self.user_type == 'admin'

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
    notes = models.TextField(blank=True, help_text="admin's notes about the student")
    payers = models.ManyToManyField(User, through='StudentPayer', related_name='students')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class StudentPayer(models.Model):
    RELATIONSHIP_CHOICES = (
        ('mother', 'Mother'),
        ('father', 'Father'),
        ('guardian', 'Guardian'),
        ('other', 'Other'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    payer = models.ForeignKey(User, on_delete=models.CASCADE)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'payer')
        ordering = ['-is_primary', 'relationship']

    def __str__(self):
        return f"{self.payer.get_full_name()} - {self.get_relationship_display()} of {self.student}"

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
    bank_account = models.ForeignKey('BankAccount', on_delete=models.PROTECT, related_name='payments', null=True, blank=True)
    # Keep these fields for backward compatibility and for payments made without a saved bank account
    routing_number = models.CharField(max_length=9, null=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    account_type = models.CharField(max_length=10, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"Payment for {self.student} - {self.amount}"

    def save(self, *args, **kwargs):
        # If a bank account is provided, populate the routing_number, account_number, and account_type
        if self.bank_account and not self.routing_number:
            token_parts = self.bank_account.provider_token.split('_')
            if len(token_parts) == 2:
                self.routing_number = token_parts[0]
                self.account_number = token_parts[1]
                self.account_type = self.bank_account.account_type
        super().save(*args, **kwargs)

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
    
class Vendor(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    bill_vendor_id = models.CharField(max_length=64)

class BankAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    nickname = models.CharField(max_length=50, help_text="Label this account (e.g., 'Mom Checking')")
    account_type = models.CharField(max_length=10, choices=[('checking', 'Checking'), ('savings', 'Savings')])
    last4 = models.CharField(max_length=4)  # Only store last 4 digits
    provider_token = models.CharField(max_length=255)  # Token from payment provider
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_method_id = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"{self.nickname} (...{self.last4})"

class PaymentBreakdown(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payment_breakdowns')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - ${self.amount}"

    class Meta:
        ordering = ['due_date', 'created_at']

class PaymentItem(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='payment_items')
    breakdown_item = models.ForeignKey(PaymentBreakdown, on_delete=models.CASCADE, related_name='payment_items')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.breakdown_item.description} - ${self.amount_paid}"

    class Meta:
        unique_together = ('payment', 'breakdown_item')

class Card(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    nickname = models.CharField(max_length=100)
    last4 = models.CharField(max_length=4)
    brand = models.CharField(max_length=20)
    exp_month = models.PositiveSmallIntegerField()
    exp_year = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_method_id = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"{self.nickname} ({self.brand} ****{self.last4})"
