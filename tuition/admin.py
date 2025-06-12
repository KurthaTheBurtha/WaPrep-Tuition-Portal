from django.contrib import admin
from .models import (
    Student, Studentpayer, Payment, PaymentReceipt, PaymentReminder,
    PaymentPlan, PaymentInstallment, AccountRequest, Vendor
)

class StudentpayerInline(admin.TabularInline):
    model = Studentpayer
    extra = 1

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'grade', 'status', 'current_balance', 'due_date')
    search_fields = ('first_name', 'last_name', 'student_id')
    list_filter = ('status', 'grade', 'due_date')
    ordering = ('last_name',)
    filter_horizontal = ('payers',)
    inlines = [StudentpayerInline] 

@admin.register(Studentpayer)
class StudentpayerAdmin(admin.ModelAdmin):
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
