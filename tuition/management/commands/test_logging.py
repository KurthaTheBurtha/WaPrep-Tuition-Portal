from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from tuition.models import AuditLog, SecurityEvent, SystemHealth, Student, Payment
from tuition.utils import log_audit_event, log_security_event, log_system_health
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the logging system to ensure all components are working'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Run full test including data modifications'
        )

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Logging System...")
        self.stdout.write("=" * 50)
        
        # Test 1: Basic audit logging
        self.test_audit_logging()
        
        # Test 2: Security event logging
        self.test_security_logging()
        
        # Test 3: System health logging
        self.test_health_logging()
        
        # Test 4: Database logging (if full test)
        if options['full']:
            self.test_database_logging()
        
        # Test 5: Verify logs were created
        self.verify_logs()
        
        self.stdout.write(self.style.SUCCESS("\n✅ Logging system test completed!"))

    def test_audit_logging(self):
        """Test audit logging functionality."""
        self.stdout.write("\n📝 Testing Audit Logging...")
        
        # Test basic audit event
        log_audit_event(
            action='CREATE',
            model_name='TestModel',
            record_id=999,
            user=None,
            description='Test audit event from management command',
            metadata={'test': True, 'source': 'management_command'},
            request=None
        )
        
        self.stdout.write("   ✅ Basic audit event logged")
        
        # Test audit event with field changes
        log_audit_event(
            action='UPDATE',
            model_name='TestModel',
            record_id=999,
            user=None,
            field_name='test_field',
            old_value='old_value',
            new_value='new_value',
            description='Test field update audit event',
            metadata={'test': True, 'field_change': True},
            request=None
        )
        
        self.stdout.write("   ✅ Field change audit event logged")

    def test_security_logging(self):
        """Test security event logging."""
        self.stdout.write("\n🔒 Testing Security Event Logging...")
        
        # Test different security event types
        security_events = [
            ('LOGIN_FAILURE', 'MEDIUM', 'Test login failure event'),
            ('SUSPICIOUS_ACTIVITY', 'HIGH', 'Test suspicious activity detection'),
            ('RATE_LIMIT_EXCEEDED', 'LOW', 'Test rate limit exceeded event'),
        ]
        
        for event_type, severity, description in security_events:
            log_security_event(
                event_type=event_type,
                severity=severity,
                description=description,
                user=None,
                metadata={'test': True, 'event_type': event_type}
            )
            self.stdout.write(f"   ✅ {event_type} security event logged")

    def test_health_logging(self):
        """Test system health logging."""
        self.stdout.write("\n💚 Testing System Health Logging...")
        
        # Test different health statuses
        health_checks = [
            ('Database', 'HEALTHY', 'Database connection test successful'),
            ('Payment Gateway', 'WARNING', 'Payment gateway response time increased'),
            ('Email Service', 'CRITICAL', 'Email service unavailable'),
        ]
        
        for component, status, message in health_checks:
            log_system_health(
                component=component,
                status=status,
                message=message,
                metrics={'response_time': random.randint(100, 5000)}
            )
            self.stdout.write(f"   ✅ {component} health check logged ({status})")

    def test_database_logging(self):
        """Test database-level logging with actual model changes."""
        self.stdout.write("\n🗄️ Testing Database Logging...")
        
        try:
            # Get or create a test user
            test_user, created = User.objects.get_or_create(
                username='test_logging_user',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User',
                    'user_type': 'admin'
                }
            )
            
            if created:
                self.stdout.write("   ✅ Test user created with logging")
            else:
                self.stdout.write("   ✅ Test user found")
            
            # Test student creation with logging
            with transaction.atomic():
                # Set current user for audit logging
                Student.set_current_user(test_user)
                
                test_student, created = Student.objects.get_or_create(
                    student_id='TEST001',
                    defaults={
                        'first_name': 'Test',
                        'last_name': 'Student',
                        'date_of_birth': timezone.now().date(),
                        'grade': '5th',
                        'status': 'active'
                    }
                )
                
                if created:
                    self.stdout.write("   ✅ Test student created with logging")
                else:
                    # Update student to trigger logging
                    test_student.notes = f"Updated at {timezone.now()}"
                    test_student.save()
                    self.stdout.write("   ✅ Test student updated with logging")
            
            # Clean up test data
            test_student.delete()
            test_user.delete()
            
        except Exception as e:
            self.stdout.write(f"   ⚠️ Database logging test failed: {e}")

    def verify_logs(self):
        """Verify that logs were actually created."""
        self.stdout.write("\n🔍 Verifying Logs...")
        
        # Check audit logs
        recent_audit_logs = AuditLog.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        self.stdout.write(f"   📝 Recent audit logs: {recent_audit_logs}")
        
        # Check security events
        recent_security_events = SecurityEvent.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        self.stdout.write(f"   🔒 Recent security events: {recent_security_events}")
        
        # Check system health
        recent_health_checks = SystemHealth.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        self.stdout.write(f"   💚 Recent health checks: {recent_health_checks}")
        
        # Show sample of recent logs
        self.stdout.write("\n📋 Sample Recent Logs:")
        recent_logs = AuditLog.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).order_by('-timestamp')[:3]
        
        for log in recent_logs:
            self.stdout.write(f"   {log.timestamp.strftime('%H:%M:%S')} | {log.action} | {log.model_name} | {log.description}")
        
        if recent_audit_logs > 0 and recent_security_events > 0 and recent_health_checks > 0:
            self.stdout.write(self.style.SUCCESS("   ✅ All logging components are working!"))
        else:
            self.stdout.write(self.style.WARNING("   ⚠️ Some logging components may not be working properly")) 