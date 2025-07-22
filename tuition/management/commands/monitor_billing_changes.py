from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Q, Sum
from datetime import datetime, timedelta
from tuition.models import AuditLog, Payment, PaymentBreakdown, PaymentItem, Student
from decimal import Decimal


class Command(BaseCommand):
    help = 'Monitor all billing and payment changes in detail'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)'
        )
        parser.add_argument(
            '--student',
            type=str,
            help='Filter by specific student name'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by specific user who made changes'
        )
        parser.add_argument(
            '--action',
            type=str,
            choices=['summary', 'bills', 'payments', 'allocations', 'detailed'],
            default='summary',
            help='Type of analysis to perform'
        )

    def handle(self, *args, **options):
        days = options['days']
        student_filter = options['student']
        user_filter = options['user']
        action = options['action']
        
        start_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"\n💰 Billing & Payment Change Monitor - Last {days} days")
        self.stdout.write("=" * 70)
        
        if action == 'summary':
            self.show_billing_summary(start_date, student_filter, user_filter)
        elif action == 'bills':
            self.show_bill_changes(start_date, student_filter, user_filter)
        elif action == 'payments':
            self.show_payment_changes(start_date, student_filter, user_filter)
        elif action == 'allocations':
            self.show_payment_allocations(start_date, student_filter, user_filter)
        elif action == 'detailed':
            self.show_detailed_changes(start_date, student_filter, user_filter)

    def show_billing_summary(self, start_date, student_filter, user_filter):
        """Show overall billing and payment summary."""
        self.stdout.write("\n📊 BILLING & PAYMENT SUMMARY")
        self.stdout.write("-" * 40)
        
        # Bill changes
        bill_query = AuditLog.objects.filter(
            timestamp__gte=start_date,
            model_name='PaymentBreakdown'
        )
        if user_filter:
            bill_query = bill_query.filter(user__username__icontains=user_filter)
        
        bill_actions = bill_query.values('action').annotate(count=Count('action')).order_by('-count')
        total_bills = bill_query.count()
        
        self.stdout.write(f"📝 Bill Changes: {total_bills:,}")
        for action in bill_actions:
            self.stdout.write(f"   {action['action']}: {action['count']:,}")
        
        # Payment changes
        payment_query = AuditLog.objects.filter(
            timestamp__gte=start_date,
            model_name='Payment'
        )
        if user_filter:
            payment_query = payment_query.filter(user__username__icontains=user_filter)
        
        payment_actions = payment_query.values('action').annotate(count=Count('action')).order_by('-count')
        total_payments = payment_query.count()
        
        self.stdout.write(f"\n💳 Payment Changes: {total_payments:,}")
        for action in payment_actions:
            self.stdout.write(f"   {action['action']}: {action['count']:,}")
        
        # Payment allocations
        allocation_query = AuditLog.objects.filter(
            timestamp__gte=start_date,
            model_name='PaymentItem'
        )
        if user_filter:
            allocation_query = allocation_query.filter(user__username__icontains=user_filter)
        
        total_allocations = allocation_query.count()
        self.stdout.write(f"\n🔗 Payment Allocations: {total_allocations:,}")
        
        # Financial summary
        payments = Payment.objects.filter(payment_date__gte=start_date)
        if student_filter:
            payments = payments.filter(student__first_name__icontains=student_filter)
        
        total_amount = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        payment_count = payments.count()
        
        self.stdout.write(f"\n💰 Financial Summary:")
        self.stdout.write(f"   Total Payments: {payment_count:,}")
        self.stdout.write(f"   Total Amount: ${total_amount:,.2f}")
        if payment_count > 0:
            self.stdout.write(f"   Average Payment: ${total_amount/payment_count:,.2f}")

    def show_bill_changes(self, start_date, student_filter, user_filter):
        """Show detailed bill changes."""
        self.stdout.write("\n📋 BILL CHANGES DETAIL")
        self.stdout.write("-" * 40)
        
        bill_query = AuditLog.objects.filter(
            timestamp__gte=start_date,
            model_name='PaymentBreakdown'
        ).order_by('-timestamp')
        
        if user_filter:
            bill_query = bill_query.filter(user__username__icontains=user_filter)
        
        # Get recent bill changes
        recent_bills = bill_query[:20]
        
        for log in recent_bills:
            try:
                bill = PaymentBreakdown.objects.get(id=log.record_id)
                student_name = f"{bill.student.first_name} {bill.student.last_name}"
                
                if student_filter and student_filter.lower() not in student_name.lower():
                    continue
                
                user = log.user.username if log.user else 'System'
                self.stdout.write(f"\n🕒 {log.timestamp.strftime('%Y-%m-%d %H:%M')}")
                self.stdout.write(f"   Action: {log.action}")
                self.stdout.write(f"   Student: {student_name}")
                self.stdout.write(f"   Bill: {bill.description}")
                self.stdout.write(f"   Amount: ${bill.amount}")
                self.stdout.write(f"   User: {user}")
                
                if log.field_name:
                    self.stdout.write(f"   Field: {log.field_name}")
                    self.stdout.write(f"   Old: {log.old_value}")
                    self.stdout.write(f"   New: {log.new_value}")
                
                if log.description:
                    self.stdout.write(f"   Description: {log.description}")
                    
            except PaymentBreakdown.DoesNotExist:
                self.stdout.write(f"\n❌ Bill #{log.record_id} (deleted)")
                self.stdout.write(f"   Action: {log.action}")
                self.stdout.write(f"   User: {log.user.username if log.user else 'System'}")

    def show_payment_changes(self, start_date, student_filter, user_filter):
        """Show detailed payment changes."""
        self.stdout.write("\n💳 PAYMENT CHANGES DETAIL")
        self.stdout.write("-" * 40)
        
        payment_query = AuditLog.objects.filter(
            timestamp__gte=start_date,
            model_name='Payment'
        ).order_by('-timestamp')
        
        if user_filter:
            payment_query = payment_query.filter(user__username__icontains=user_filter)
        
        # Get recent payment changes
        recent_payments = payment_query[:20]
        
        for log in recent_payments:
            try:
                payment = Payment.objects.get(id=log.record_id)
                student_name = f"{payment.student.first_name} {payment.student.last_name}"
                
                if student_filter and student_filter.lower() not in student_name.lower():
                    continue
                
                user = log.user.username if log.user else 'System'
                self.stdout.write(f"\n🕒 {log.timestamp.strftime('%Y-%m-%d %H:%M')}")
                self.stdout.write(f"   Action: {log.action}")
                self.stdout.write(f"   Student: {student_name}")
                self.stdout.write(f"   Amount: ${payment.amount}")
                self.stdout.write(f"   Status: {payment.status}")
                self.stdout.write(f"   Method: {payment.payment_method}")
                self.stdout.write(f"   User: {user}")
                
                if log.field_name:
                    self.stdout.write(f"   Field: {log.field_name}")
                    self.stdout.write(f"   Old: {log.old_value}")
                    self.stdout.write(f"   New: {log.new_value}")
                
                if log.description:
                    self.stdout.write(f"   Description: {log.description}")
                    
            except Payment.DoesNotExist:
                self.stdout.write(f"\n❌ Payment #{log.record_id} (deleted)")
                self.stdout.write(f"   Action: {log.action}")
                self.stdout.write(f"   User: {log.user.username if log.user else 'System'}")

    def show_payment_allocations(self, start_date, student_filter, user_filter):
        """Show payment allocation details."""
        self.stdout.write("\n🔗 PAYMENT ALLOCATIONS DETAIL")
        self.stdout.write("-" * 40)
        
        allocation_query = AuditLog.objects.filter(
            timestamp__gte=start_date,
            model_name='PaymentItem'
        ).order_by('-timestamp')
        
        if user_filter:
            allocation_query = allocation_query.filter(user__username__icontains=user_filter)
        
        # Get recent allocations
        recent_allocations = allocation_query[:20]
        
        for log in recent_allocations:
            try:
                payment_item = PaymentItem.objects.get(id=log.record_id)
                student_name = f"{payment_item.payment.student.first_name} {payment_item.payment.student.last_name}"
                
                if student_filter and student_filter.lower() not in student_name.lower():
                    continue
                
                user = log.user.username if log.user else 'System'
                self.stdout.write(f"\n🕒 {log.timestamp.strftime('%Y-%m-%d %H:%M')}")
                self.stdout.write(f"   Action: {log.action}")
                self.stdout.write(f"   Student: {student_name}")
                self.stdout.write(f"   Payment: ${payment_item.payment.amount} ({payment_item.payment.status})")
                self.stdout.write(f"   Bill: {payment_item.breakdown_item.description}")
                self.stdout.write(f"   Allocated: ${payment_item.amount_paid}")
                self.stdout.write(f"   User: {user}")
                
                if log.description:
                    self.stdout.write(f"   Description: {log.description}")
                    
            except PaymentItem.DoesNotExist:
                self.stdout.write(f"\n❌ Payment Item #{log.record_id} (deleted)")
                self.stdout.write(f"   Action: {log.action}")
                self.stdout.write(f"   User: {log.user.username if log.user else 'System'}")

    def show_detailed_changes(self, start_date, student_filter, user_filter):
        """Show all changes in chronological order."""
        self.stdout.write("\n📋 ALL CHANGES CHRONOLOGICAL")
        self.stdout.write("-" * 40)
        
        # Get all relevant changes
        changes_query = AuditLog.objects.filter(
            timestamp__gte=start_date,
            model_name__in=['PaymentBreakdown', 'Payment', 'PaymentItem', 'Student']
        ).order_by('-timestamp')
        
        if user_filter:
            changes_query = changes_query.filter(user__username__icontains=user_filter)
        
        # Get recent changes
        recent_changes = changes_query[:30]
        
        for log in recent_changes:
            user = log.user.username if log.user else 'System'
            
            # Try to get student name if possible
            student_name = "Unknown"
            try:
                if log.model_name == 'PaymentBreakdown':
                    bill = PaymentBreakdown.objects.get(id=log.record_id)
                    student_name = f"{bill.student.first_name} {bill.student.last_name}"
                elif log.model_name == 'Payment':
                    payment = Payment.objects.get(id=log.record_id)
                    student_name = f"{payment.student.first_name} {payment.student.last_name}"
                elif log.model_name == 'PaymentItem':
                    payment_item = PaymentItem.objects.get(id=log.record_id)
                    student_name = f"{payment_item.payment.student.first_name} {payment_item.payment.student.last_name}"
                elif log.model_name == 'Student':
                    student = Student.objects.get(id=log.record_id)
                    student_name = f"{student.first_name} {student.last_name}"
            except:
                student_name = "Unknown/Deleted"
            
            if student_filter and student_filter.lower() not in student_name.lower():
                continue
            
            self.stdout.write(f"\n🕒 {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"   {log.action} | {log.model_name} | {student_name}")
            self.stdout.write(f"   User: {user}")
            
            if log.field_name:
                self.stdout.write(f"   Field: {log.field_name} | {log.old_value} → {log.new_value}")
            
            if log.description:
                self.stdout.write(f"   Description: {log.description}") 