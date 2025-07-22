from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from tuition.models import AuditLog, SecurityEvent, SystemHealth, User, Student, Payment
import json


class Command(BaseCommand):
    help = 'Monitor and analyze logging system performance and activity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)'
        )
        parser.add_argument(
            '--action',
            type=str,
            choices=['summary', 'audit', 'security', 'health', 'users', 'payments', 'cleanup'],
            default='summary',
            help='Type of analysis to perform'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by specific user'
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Filter by specific model'
        )

    def handle(self, *args, **options):
        days = options['days']
        action = options['action']
        user_filter = options['user']
        model_filter = options['model']
        
        start_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"\n🔍 Logging System Monitor - Last {days} days")
        self.stdout.write("=" * 60)
        
        if action == 'summary':
            self.show_summary(start_date, user_filter, model_filter)
        elif action == 'audit':
            self.show_audit_analysis(start_date, user_filter, model_filter)
        elif action == 'security':
            self.show_security_analysis(start_date, user_filter)
        elif action == 'health':
            self.show_health_analysis(start_date)
        elif action == 'users':
            self.show_user_activity(start_date, user_filter)
        elif action == 'payments':
            self.show_payment_activity(start_date, user_filter)
        elif action == 'cleanup':
            self.cleanup_old_logs(days)

    def show_summary(self, start_date, user_filter, model_filter):
        """Show overall logging system summary."""
        self.stdout.write("\n📊 SYSTEM SUMMARY")
        self.stdout.write("-" * 30)
        
        # Audit log summary
        audit_query = AuditLog.objects.filter(timestamp__gte=start_date)
        if user_filter:
            audit_query = audit_query.filter(user__username__icontains=user_filter)
        if model_filter:
            audit_query = audit_query.filter(model_name__icontains=model_filter)
        
        audit_count = audit_query.count()
        audit_actions = audit_query.values('action').annotate(count=Count('action')).order_by('-count')
        
        self.stdout.write(f"📝 Audit Logs: {audit_count:,}")
        for action in audit_actions[:5]:
            self.stdout.write(f"   {action['action']}: {action['count']:,}")
        
        # Security events summary
        security_query = SecurityEvent.objects.filter(timestamp__gte=start_date)
        if user_filter:
            security_query = security_query.filter(user__username__icontains=user_filter)
        
        security_count = security_query.count()
        security_severity = security_query.values('severity').annotate(count=Count('severity')).order_by('-count')
        
        self.stdout.write(f"\n🔒 Security Events: {security_count:,}")
        for severity in security_severity:
            self.stdout.write(f"   {severity['severity']}: {severity['count']:,}")
        
        # System health summary
        health_count = SystemHealth.objects.filter(timestamp__gte=start_date).count()
        health_status = SystemHealth.objects.filter(timestamp__gte=start_date).values('status').annotate(count=Count('status')).order_by('-count')
        
        self.stdout.write(f"\n💚 System Health Checks: {health_count:,}")
        for status in health_status:
            self.stdout.write(f"   {status['status']}: {status['count']:,}")

    def show_audit_analysis(self, start_date, user_filter, model_filter):
        """Show detailed audit log analysis."""
        self.stdout.write("\n📋 AUDIT LOG ANALYSIS")
        self.stdout.write("-" * 30)
        
        audit_query = AuditLog.objects.filter(timestamp__gte=start_date)
        if user_filter:
            audit_query = audit_query.filter(user__username__icontains=user_filter)
        if model_filter:
            audit_query = audit_query.filter(model_name__icontains=model_filter)
        
        # Most active users
        active_users = audit_query.values('user__username').annotate(count=Count('id')).order_by('-count')[:10]
        self.stdout.write("\n👥 Most Active Users:")
        for user in active_users:
            username = user['user__username'] or 'Anonymous'
            self.stdout.write(f"   {username}: {user['count']:,} actions")
        
        # Most changed models
        active_models = audit_query.values('model_name').annotate(count=Count('id')).order_by('-count')[:10]
        self.stdout.write("\n📊 Most Changed Models:")
        for model in active_models:
            self.stdout.write(f"   {model['model_name']}: {model['count']:,} changes")
        
        # Recent changes
        recent_changes = audit_query.order_by('-timestamp')[:10]
        self.stdout.write("\n🕒 Recent Changes:")
        for change in recent_changes:
            user = change.user.username if change.user else 'Anonymous'
            self.stdout.write(f"   {change.timestamp.strftime('%Y-%m-%d %H:%M')} | {user} | {change.action} | {change.model_name} | {change.description}")

    def show_security_analysis(self, start_date, user_filter):
        """Show security events analysis."""
        self.stdout.write("\n🔒 SECURITY ANALYSIS")
        self.stdout.write("-" * 30)
        
        security_query = SecurityEvent.objects.filter(timestamp__gte=start_date)
        if user_filter:
            security_query = security_query.filter(user__username__icontains=user_filter)
        
        # Security events by type
        event_types = security_query.values('event_type').annotate(count=Count('id')).order_by('-count')
        self.stdout.write("\n🚨 Security Events by Type:")
        for event_type in event_types:
            self.stdout.write(f"   {event_type['event_type']}: {event_type['count']:,}")
        
        # High severity events
        high_severity = security_query.filter(severity__in=['HIGH', 'CRITICAL']).order_by('-timestamp')[:10]
        self.stdout.write("\n⚠️ High Severity Events:")
        for event in high_severity:
            user = event.user.username if event.user else 'Anonymous'
            self.stdout.write(f"   {event.timestamp.strftime('%Y-%m-%d %H:%M')} | {event.severity} | {user} | {event.event_type} | {event.description}")
        
        # Unresolved events
        unresolved = security_query.filter(resolved=False).count()
        self.stdout.write(f"\n❌ Unresolved Events: {unresolved:,}")

    def show_health_analysis(self, start_date):
        """Show system health analysis."""
        self.stdout.write("\n💚 SYSTEM HEALTH ANALYSIS")
        self.stdout.write("-" * 30)
        
        health_query = SystemHealth.objects.filter(timestamp__gte=start_date)
        
        # Health status over time
        health_status = health_query.values('status').annotate(count=Count('id')).order_by('-count')
        self.stdout.write("\n📈 Health Status Distribution:")
        for status in health_status:
            self.stdout.write(f"   {status['status']}: {status['count']:,}")
        
        # Components with issues
        critical_components = health_query.filter(status__in=['WARNING', 'CRITICAL']).values('component').annotate(count=Count('id')).order_by('-count')
        self.stdout.write("\n⚠️ Components with Issues:")
        for component in critical_components:
            self.stdout.write(f"   {component['component']}: {component['count']:,} issues")
        
        # Recent health checks
        recent_health = health_query.order_by('-timestamp')[:10]
        self.stdout.write("\n🕒 Recent Health Checks:")
        for health in recent_health:
            self.stdout.write(f"   {health.timestamp.strftime('%Y-%m-%d %H:%M')} | {health.component} | {health.status} | {health.message}")

    def show_user_activity(self, start_date, user_filter):
        """Show user activity analysis."""
        self.stdout.write("\n👤 USER ACTIVITY ANALYSIS")
        self.stdout.write("-" * 30)
        
        audit_query = AuditLog.objects.filter(timestamp__gte=start_date)
        if user_filter:
            audit_query = audit_query.filter(user__username__icontains=user_filter)
        
        # User login patterns
        login_events = audit_query.filter(action='LOGIN').values('user__username').annotate(count=Count('id')).order_by('-count')[:10]
        self.stdout.write("\n🔑 User Login Activity:")
        for login in login_events:
            username = login['user__username'] or 'Anonymous'
            self.stdout.write(f"   {username}: {login['count']:,} logins")
        
        # User data changes
        data_changes = audit_query.filter(action__in=['CREATE', 'UPDATE', 'DELETE']).values('user__username').annotate(count=Count('id')).order_by('-count')[:10]
        self.stdout.write("\n✏️ User Data Changes:")
        for change in data_changes:
            username = change['user__username'] or 'Anonymous'
            self.stdout.write(f"   {username}: {change['count']:,} changes")

    def show_payment_activity(self, start_date, user_filter):
        """Show payment-related activity."""
        self.stdout.write("\n💰 PAYMENT ACTIVITY ANALYSIS")
        self.stdout.write("-" * 30)
        
        audit_query = AuditLog.objects.filter(timestamp__gte=start_date, model_name='Payment')
        if user_filter:
            audit_query = audit_query.filter(user__username__icontains=user_filter)
        
        # Payment events
        payment_events = audit_query.values('action').annotate(count=Count('id')).order_by('-count')
        self.stdout.write("\n💳 Payment Events:")
        for event in payment_events:
            self.stdout.write(f"   {event['action']}: {event['count']:,}")
        
        # Payment amounts (from Payment model)
        payments = Payment.objects.filter(payment_date__gte=start_date)
        if user_filter:
            payments = payments.filter(payer__username__icontains=user_filter)
        
        total_amount = sum(payment.amount for payment in payments)
        payment_count = payments.count()
        
        self.stdout.write(f"\n📊 Payment Summary:")
        self.stdout.write(f"   Total Payments: {payment_count:,}")
        self.stdout.write(f"   Total Amount: ${total_amount:,.2f}")
        self.stdout.write(f"   Average Payment: ${total_amount/payment_count:,.2f}" if payment_count > 0 else "   Average Payment: $0.00")

    def cleanup_old_logs(self, days):
        """Clean up old audit logs."""
        self.stdout.write("\n🧹 CLEANUP OLD LOGS")
        self.stdout.write("-" * 30)
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Count records to be deleted
        audit_count = AuditLog.objects.filter(timestamp__lt=cutoff_date).count()
        security_count = SecurityEvent.objects.filter(timestamp__lt=cutoff_date).count()
        health_count = SystemHealth.objects.filter(timestamp__lt=cutoff_date).count()
        
        self.stdout.write(f"Records older than {days} days:")
        self.stdout.write(f"   Audit Logs: {audit_count:,}")
        self.stdout.write(f"   Security Events: {security_count:,}")
        self.stdout.write(f"   System Health: {health_count:,}")
        
        # Ask for confirmation
        response = input(f"\nDelete {audit_count + security_count + health_count:,} old records? (yes/no): ")
        if response.lower() == 'yes':
            AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()
            SecurityEvent.objects.filter(timestamp__lt=cutoff_date).delete()
            SystemHealth.objects.filter(timestamp__lt=cutoff_date).delete()
            self.stdout.write(self.style.SUCCESS("✅ Old logs cleaned up successfully!"))
        else:
            self.stdout.write("❌ Cleanup cancelled.") 