from django.contrib import admin
from .models import (
    User, Student, StudentPayer, Payment, PaymentReceipt, PaymentReminder,
    PaymentPlan, PaymentInstallment, AccountRequest, Vendor, PasswordReset, PasswordHistory, PaymentBreakdown
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'user_type', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'user_id')
    ordering = ('last_name', 'first_name')
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('username', 'first_name', 'last_name', 'email', 'user_id')
        }),
        ('Account Information', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
    )

class StudentPayerInline(admin.TabularInline):
    model = StudentPayer
    extra = 1

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'grade', 'status', 'current_balance', 'due_date')
    search_fields = ('first_name', 'last_name', 'student_id')
    list_filter = ('status', 'grade', 'due_date')
    ordering = ('last_name',)
    filter_horizontal = ('payers',)
    inlines = [StudentPayerInline] 

@admin.register(StudentPayer)
class StudentPayerAdmin(admin.ModelAdmin):
    list_display = ('student', 'payer', 'relationship')
    list_filter = ('relationship',)
    search_fields = ('student__first_name', 'payer__username')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'payment_date', 'status', 'receipt_number')
    list_filter = ('status',)
    search_fields = ('student__first_name', 'receipt_number')

@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ('payment', 'generated_at')

@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display = ('payment', 'reminder_date', 'sent', 'sent_at')

@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = ('student', 'total_amount', 'number_of_installments', 'status')

@admin.register(PaymentInstallment)
class PaymentInstallmentAdmin(admin.ModelAdmin):
    list_display = ('payment_plan', 'amount', 'due_date', 'status')

@admin.register(AccountRequest)
class AccountRequestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'child_first_name', 'email', 'submitted_at')

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'bill_vendor_id')

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'used', 'is_expired')
    list_filter = ('used', 'created_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at',)
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

@admin.register(PasswordHistory)
class PasswordHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'password_hash')
    
    def has_add_permission(self, request):
        # Prevent manual addition of password history records
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent editing of password history records
        return False

@admin.register(PaymentBreakdown)
class PaymentBreakdownAdmin(admin.ModelAdmin):
    list_display = ('student', 'description', 'amount', 'due_date', 'is_paid', 'show_in_payment_history', 'created_at')
    list_filter = ('is_paid', 'show_in_payment_history', 'due_date', 'created_at')
    search_fields = ('student__first_name', 'student__last_name', 'description')
    list_editable = ('is_paid', 'show_in_payment_history')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-due_date', '-created_at')
    
    fieldsets = (
        ('Bill Information', {
            'fields': ('student', 'description', 'amount', 'due_date')
        }),
        ('Status', {
            'fields': ('is_paid', 'show_in_payment_history')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
