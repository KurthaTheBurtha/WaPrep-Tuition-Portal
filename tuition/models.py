import sys
import json
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.conf import settings

# Compatibility for JSONField on SQLite
try:
    from django.db.models import JSONField as NativeJSONField
except ImportError:
    NativeJSONField = None

def get_json_field(*args, **kwargs):
    # Use TextField for SQLite, JSONField for others
    from django.db import connection
    if connection.vendor == 'sqlite':
        return models.TextField(*args, **kwargs)
    if NativeJSONField is not None:
        return NativeJSONField(*args, **kwargs)
    return models.TextField(*args, **kwargs)


# Audit Mixins
class AuditMixin:
    """
    Mixin to automatically track changes to model instances.
    """
    
    def save(self, *args, **kwargs):
        # Check if this is a new instance or an update
        is_new = self.pk is None
        
        if is_new:
            # This is a new instance
            result = super().save(*args, **kwargs)
            
            # Log creation
            from .utils import log_audit_event, create_data_version
            log_audit_event(
                action='CREATE',
                model_name=self.__class__.__name__,
                record_id=self.pk,
                user=getattr(self, '_current_user', None),
                description=f"Created new {self.__class__.__name__} record",
                metadata={'fields': self._get_field_values()}
            )
            
            # Create initial version
            create_data_version(
                model_name=self.__class__.__name__,
                record_id=self.pk,
                data_snapshot=self._get_field_values(),
                user=getattr(self, '_current_user', None)
            )
            
        else:
            # This is an update - get the old instance
            from .utils import log_audit_event, create_data_version, get_model_changes
            old_instance = self.__class__.objects.get(pk=self.pk)
            changes = get_model_changes(old_instance, self)
            
            result = super().save(*args, **kwargs)
            
            # Log each change
            for field_name, change_data in changes.items():
                log_audit_event(
                    action='UPDATE',
                    model_name=self.__class__.__name__,
                    record_id=self.pk,
                    user=getattr(self, '_current_user', None),
                    field_name=field_name,
                    old_value=str(change_data['old']),
                    new_value=str(change_data['new']),
                    description=f"Updated {field_name} field",
                    metadata={'changes': changes}
                )
            
            # Create new version if there were changes
            if changes:
                create_data_version(
                    model_name=self.__class__.__name__,
                    record_id=self.pk,
                    data_snapshot=self._get_field_values(),
                    user=getattr(self, '_current_user', None)
                )
        
        return result
    
    def delete(self, *args, **kwargs):
        # Log deletion before actually deleting
        from .utils import log_audit_event
        log_audit_event(
            action='DELETE',
            model_name=self.__class__.__name__,
            record_id=self.pk,
            user=getattr(self, '_current_user', None),
            description=f"Deleted {self.__class__.__name__} record",
            metadata={'fields': self._get_field_values()}
        )
        
        return super().delete(*args, **kwargs)
    
    def _get_field_values(self):
        """
        Get all field values as a dictionary.
        """
        data = {}
        for field in self._meta.fields:
            if not field.name.startswith('_'):
                value = getattr(self, field.name)
                # Convert non-serializable objects to strings
                if hasattr(value, 'isoformat'):  # datetime objects
                    data[field.name] = value.isoformat()
                else:
                    data[field.name] = str(value) if value is not None else None
        return data
    
    @classmethod
    def set_current_user(cls, user):
        """
        Set the current user for audit logging.
        This should be called before saving instances.
        """
        cls._current_user = user


class StudentAuditMixin(AuditMixin):
    """
    Specialized audit mixin for Student model with additional tracking.
    """
    
    def save(self, *args, **kwargs):
        # Track balance changes specifically
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                if old_instance.current_balance != self.current_balance:
                    from .utils import log_audit_event
                    log_audit_event(
                        action='UPDATE',
                        model_name=self.__class__.__name__,
                        record_id=self.pk,
                        user=getattr(self, '_current_user', None),
                        field_name='current_balance',
                        old_value=str(old_instance.current_balance),
                        new_value=str(self.current_balance),
                        description=f"Student balance changed from ${old_instance.current_balance} to ${self.current_balance}",
                        metadata={'balance_change': float(self.current_balance - old_instance.current_balance)}
                    )
            except self.__class__.DoesNotExist:
                pass
        
        return super().save(*args, **kwargs)


class PaymentAuditMixin(AuditMixin):
    """
    Specialized audit mixin for Payment model with additional tracking.
    """
    
    def save(self, *args, **kwargs):
        # Track payment status changes
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    from .utils import log_audit_event
                    log_audit_event(
                        action='UPDATE',
                        model_name=self.__class__.__name__,
                        record_id=self.pk,
                        user=getattr(self, '_current_user', None),
                        field_name='status',
                        old_value=old_instance.status,
                        new_value=self.status,
                        description=f"Payment status changed from {old_instance.status} to {self.status}",
                        metadata={
                            'payment_amount': float(self.amount),
                            'student_id': self.student.id,
                            'payer_id': self.payer.id if self.payer else None
                        }
                    )
            except self.__class__.DoesNotExist:
                pass
        
        return super().save(*args, **kwargs)


class UserAuditMixin(AuditMixin):
    """
    Specialized audit mixin for User model with additional tracking.
    """
    
    def save(self, *args, **kwargs):
        # Track password changes
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                if old_instance.password != self.password:
                    from .utils import log_audit_event
                    log_audit_event(
                        action='PASSWORD_CHANGE',
                        model_name=self.__class__.__name__,
                        record_id=self.pk,
                        user=getattr(self, '_current_user', None),
                        field_name='password',
                        old_value='[REDACTED]',
                        new_value='[REDACTED]',
                        description="User password changed",
                        metadata={'password_changed_at': timezone.now().isoformat()}
                    )
            except self.__class__.DoesNotExist:
                pass
        
        return super().save(*args, **kwargs)


class User(AbstractUser, UserAuditMixin):
    USER_TYPE_CHOICES = (
        ('payer', 'Payer'),
        ('admin', 'Admin'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    user_id = models.CharField(max_length=30, unique=True, null=True, blank=False)
    stripe_customer_id = models.CharField(max_length=64, blank=True, null=True)
    
    def is_admin(self):
        return self.user_type == 'admin'

class Student(models.Model, StudentAuditMixin):
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

class StudentPayer(models.Model, AuditMixin):
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

class Payment(models.Model, PaymentAuditMixin):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made', null=True, blank=True, help_text='The payer who made this payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, null=True, blank=True, help_text='Method used for payment (e.g., cash, check, credit card machine, other)')
    notes = models.TextField(blank=True, null=True, help_text='Admin notes about this payment')
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
    student_names = models.TextField(blank=True, help_text="Enter the names of all students you are responsible for")

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

class PaymentBreakdown(models.Model, AuditMixin):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payment_breakdowns')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    date_incurred = models.DateField(
        help_text="The date when this bill was incurred (defaults to creation date)"
    )
    late_date = models.DateField(
        null=True, 
        blank=True,
        help_text="The date when this bill becomes late (defaults to last day of current month)"
    )
    is_paid = models.BooleanField(default=False)
    show_in_payment_history = models.BooleanField(
        default=False, 
        help_text="If checked and bill is paid, this will appear in the payer's payment history"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - ${self.amount}"

    @property
    def is_overdue(self):
        """Check if the bill is overdue based on late_date"""
        if not self.late_date or self.is_paid:
            return False
        from django.utils import timezone
        # Ensure late_date is a date object
        if isinstance(self.late_date, str):
            try:
                from datetime import datetime
                late_date = datetime.strptime(self.late_date, '%Y-%m-%d').date()
            except ValueError:
                return False
        else:
            late_date = self.late_date
        return late_date < timezone.now().date()

    @property
    def days_overdue(self):
        """Calculate how many days overdue the bill is"""
        if not self.is_overdue:
            return 0
        from django.utils import timezone
        # Ensure late_date is a date object
        if isinstance(self.late_date, str):
            try:
                from datetime import datetime
                late_date = datetime.strptime(self.late_date, '%Y-%m-%d').date()
            except ValueError:
                return 0
        else:
            late_date = self.late_date
        return (timezone.now().date() - late_date).days

    @property
    def remaining_amount(self):
        """Calculate the remaining amount to be paid on this bill"""
        from decimal import Decimal
        # Sum all payments made towards this bill
        total_paid = self.payment_items.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or Decimal('0.00')
        
        # Calculate remaining amount
        remaining = self.amount - total_paid
        
        # Ensure remaining amount is not negative
        return max(remaining, Decimal('0.00'))

    @property
    def is_fully_paid(self):
        """Check if the bill is fully paid"""
        return self.remaining_amount <= Decimal('0.00')

    @property
    def payment_status(self):
        """Get the payment status of the bill"""
        if self.is_fully_paid:
            return 'Paid'
        elif self.remaining_amount < self.amount:
            return 'Partially Paid'
        else:
            return 'Unpaid'

    def save(self, *args, **kwargs):
        # Ensure date_incurred is always set
        if not self.date_incurred:
            from datetime import datetime
            self.date_incurred = datetime.now().date()
        
        # Set default late_date if not provided
        if not self.late_date:
            from datetime import datetime
            import calendar
            # Prefer due_date, then date_incurred, then today
            ref_date = self.due_date or self.date_incurred or datetime.now().date()
            
            # Ensure ref_date is a date object, not a string
            if isinstance(ref_date, str):
                try:
                    ref_date = datetime.strptime(ref_date, '%Y-%m-%d').date()
                except ValueError:
                    ref_date = datetime.now().date()
            
            last_day_of_month = calendar.monthrange(ref_date.year, ref_date.month)[1]
            self.late_date = datetime(ref_date.year, ref_date.month, last_day_of_month).date()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-is_paid', 'due_date', 'created_at']

class PaymentItem(models.Model, AuditMixin):
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

class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    def is_expired(self):
        # Token expires after 24 hours
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at < timezone.now() - timedelta(hours=24)

class PasswordHistory(models.Model):
    """
    Model to track password history and prevent password reuse.
    Stores hashed passwords to prevent users from reusing recent passwords.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=255)  # Store the hashed password
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Password histories"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Password history for {self.user.email} at {self.created_at}"
    
    @classmethod
    def store_password(cls, user, password):
        """
        Store a password hash in the user's password history.
        """
        from django.contrib.auth.hashers import make_password
        password_hash = make_password(password)
        cls.objects.create(user=user, password_hash=password_hash)
        
        # Keep only the last 5 passwords (delete older ones)
        recent_passwords = cls.objects.filter(user=user).order_by('-created_at')[:5]
        cls.objects.filter(user=user).exclude(id__in=recent_passwords.values_list('id', flat=True)).delete()
    
    @classmethod
    def is_password_reused(cls, user, password):
        """
        Check if the password has been used recently by this user.
        Returns True if the password is found in recent history.
        """
        from django.contrib.auth.hashers import check_password
        
        # Check against the last 5 passwords
        recent_passwords = cls.objects.filter(user=user).order_by('-created_at')[:5]
        
        for password_record in recent_passwords:
            if check_password(password, password_record.password_hash):
                return True
        
        return False

class AuditLog(models.Model):
    """
    Comprehensive audit log for tracking changes to student and payer data.
    """
    ACTION_CHOICES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('ACCESS_DENIED', 'Access Denied'),
        ('DATA_EXPORT', 'Data Export'),
        ('BULK_UPDATE', 'Bulk Update'),
    )
    
    MODEL_CHOICES = (
        ('Student', 'Student'),
        ('User', 'User'),
        ('StudentPayer', 'StudentPayer'),
        ('Payment', 'Payment'),
        ('PaymentBreakdown', 'PaymentBreakdown'),
        ('BankAccount', 'BankAccount'),
        ('Card', 'Card'),
        ('AccountRequest', 'AccountRequest'),
    )
    
    # Basic audit information
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50, choices=MODEL_CHOICES)
    record_id = models.IntegerField(help_text="ID of the affected record")
    
    # User information
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Change details
    field_name = models.CharField(max_length=100, blank=True, help_text="Name of the changed field")
    old_value = models.TextField(blank=True, help_text="Previous value (truncated if too long)")
    new_value = models.TextField(blank=True, help_text="New value (truncated if too long)")
    
    # Additional context
    description = models.TextField(blank=True, help_text="Human-readable description of the change")
    metadata = get_json_field(default=dict, blank=True, help_text="Additional context data")
    
    # Security and compliance
    session_id = models.CharField(max_length=100, blank=True)
    request_id = models.CharField(max_length=100, blank=True, help_text="Unique request identifier")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['model_name']),
            models.Index(fields=['user']),
            models.Index(fields=['record_id']),
        ]
    
    def __str__(self):
        return f"{self.action} on {self.model_name} #{self.record_id} by {self.user} at {self.timestamp}"
    
    @classmethod
    def log_change(cls, action, model_name, record_id, user=None, field_name=None, 
                   old_value=None, new_value=None, description=None, metadata=None,
                   user_ip=None, user_agent=None, session_id=None, request_id=None):
        """
        Log a change to the audit system.
        """
        # Truncate values if they're too long
        if old_value and len(str(old_value)) > 1000:
            old_value = str(old_value)[:997] + "..."
        if new_value and len(str(new_value)) > 1000:
            new_value = str(new_value)[:997] + "..."
        
        return cls.objects.create(
            action=action,
            model_name=model_name,
            record_id=record_id,
            user=user,
            field_name=field_name or "",
            old_value=old_value or "",
            new_value=new_value or "",
            description=description or "",
            metadata=metadata or {},
            user_ip=user_ip,
            user_agent=user_agent or "",
            session_id=session_id or "",
            request_id=request_id or "",
        )

    def get_metadata(self):
        if isinstance(self.metadata, dict):
            return self.metadata
        try:
            return json.loads(self.metadata)
        except Exception:
            return {}

    def set_metadata(self, value):
        if isinstance(self.metadata, dict):
            self.metadata = value
        else:
            self.metadata = json.dumps(value)

class DataVersion(models.Model):
    """
    Version control for critical data records.
    """
    model_name = models.CharField(max_length=50)
    record_id = models.IntegerField()
    version_number = models.PositiveIntegerField()
    data_snapshot = get_json_field(help_text="Complete snapshot of the record at this version")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('model_name', 'record_id', 'version_number')
        ordering = ['-version_number']
        indexes = [
            models.Index(fields=['model_name', 'record_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.model_name} #{self.record_id} v{self.version_number}"
    
    @classmethod
    def create_version(cls, model_name, record_id, data_snapshot, user=None):
        """
        Create a new version of a record.
        """
        # Get the next version number
        latest_version = cls.objects.filter(
            model_name=model_name, 
            record_id=record_id
        ).aggregate(models.Max('version_number'))['version_number__max'] or 0
        
        return cls.objects.create(
            model_name=model_name,
            record_id=record_id,
            version_number=latest_version + 1,
            data_snapshot=data_snapshot,
            created_by=user
        )

    def get_data_snapshot(self):
        if isinstance(self.data_snapshot, dict):
            return self.data_snapshot
        try:
            return json.loads(self.data_snapshot)
        except Exception:
            return {}

    def set_data_snapshot(self, value):
        if isinstance(self.data_snapshot, dict):
            self.data_snapshot = value
        else:
            self.data_snapshot = json.dumps(value)

class SystemHealth(models.Model):
    """
    System health monitoring and metrics.
    """
    timestamp = models.DateTimeField(auto_now_add=True)
    component = models.CharField(max_length=100, help_text="System component being monitored")
    status = models.CharField(max_length=20, choices=[
        ('HEALTHY', 'Healthy'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
        ('UNKNOWN', 'Unknown'),
    ])
    message = models.TextField(blank=True)
    metrics = get_json_field(default=dict, blank=True, help_text="Performance metrics")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['component']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.component}: {self.status} at {self.timestamp}"

    def get_metrics(self):
        if isinstance(self.metrics, dict):
            return self.metrics
        try:
            return json.loads(self.metrics)
        except Exception:
            return {}

    def set_metrics(self, value):
        if isinstance(self.metrics, dict):
            self.metrics = value
        else:
            self.metrics = json.dumps(value)

class SecurityEvent(models.Model):
    """
    Security-related events and alerts.
    """
    SEVERITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )
    
    EVENT_TYPE_CHOICES = (
        ('LOGIN_FAILURE', 'Login Failure'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
        ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity'),
        ('DATA_BREACH', 'Data Breach'),
        ('SYSTEM_COMPROMISE', 'System Compromise'),
        ('RATE_LIMIT_EXCEEDED', 'Rate Limit Exceeded'),
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = get_json_field(default=dict, blank=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_events')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['resolved']),
        ]
    
    def __str__(self):
        return f"{self.event_type} ({self.severity}) at {self.timestamp}"
    
    def resolve(self, resolved_by=None):
        """Mark the security event as resolved."""
        from django.utils import timezone
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.save()

    def get_metadata(self):
        if isinstance(self.metadata, dict):
            return self.metadata
        try:
            return json.loads(self.metadata)
        except Exception:
            return {}

    def set_metadata(self, value):
        if isinstance(self.metadata, dict):
            self.metadata = value
        else:
            self.metadata = json.dumps(value)
