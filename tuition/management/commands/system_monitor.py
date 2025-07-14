import psutil
import os
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.db import connection
from tuition.utils import log_system_health
from tuition.models import AuditLog, SecurityEvent, SystemHealth


class Command(BaseCommand):
    help = 'Monitor system health and performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            choices=['all', 'database', 'disk', 'memory', 'cpu', 'logs'],
            default='all',
            help='Type of health check to perform (default: all)'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=80.0,
            help='Warning threshold percentage (default: 80.0)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuous monitoring'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,
            help='Monitoring interval in seconds (default: 300)'
        )

    def handle(self, *args, **options):
        check_type = options['check']
        threshold = options['threshold']
        continuous = options['continuous']
        interval = options['interval']

        if continuous:
            self.stdout.write(f"Starting continuous monitoring (interval: {interval}s)...")
            try:
                while True:
                    self._run_health_checks(check_type, threshold)
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write("Monitoring stopped by user.")
        else:
            self._run_health_checks(check_type, threshold)

    def _run_health_checks(self, check_type, threshold):
        """Run the specified health checks."""
        timestamp = timezone.now()
        self.stdout.write(f"Running health checks at {timestamp}...")

        if check_type in ['all', 'database']:
            self._check_database_health(threshold)

        if check_type in ['all', 'disk']:
            self._check_disk_health(threshold)

        if check_type in ['all', 'memory']:
            self._check_memory_health(threshold)

        if check_type in ['all', 'cpu']:
            self._check_cpu_health(threshold)

        if check_type in ['all', 'logs']:
            self._check_log_health(threshold)

        self.stdout.write("Health checks completed.")

    def _check_database_health(self, threshold):
        """Check database connection and performance."""
        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            # Check database size (if PostgreSQL)
            db_size = None
            if 'postgresql' in settings.DATABASES['default']['ENGINE']:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                               pg_database_size(current_database()) as size_bytes
                    """)
                    result = cursor.fetchone()
                    db_size = result[0] if result else None

            # Check slow queries (simplified)
            with connection.cursor() as cursor:
                start_time = time.time()
                cursor.execute("SELECT COUNT(*) FROM tuition_auditlog")
                query_time = time.time() - start_time

            status = 'HEALTHY'
            message = f"Database connection OK. Query time: {query_time:.3f}s"
            if db_size:
                message += f" Database size: {db_size}"

            if query_time > getattr(settings, 'MONITORING_PERFORMANCE_THRESHOLD', 2.0):
                status = 'WARNING'
                message += " - Slow query detected"

            metrics = {
                'query_time': query_time,
                'database_size': db_size,
                'connection_status': 'OK'
            }

            log_system_health('database', status, message, metrics)
            self.stdout.write(f"Database: {status} - {message}")

        except Exception as e:
            status = 'CRITICAL'
            message = f"Database connection failed: {str(e)}"
            log_system_health('database', status, message, {'error': str(e)})
            self.stdout.write(f"Database: {status} - {message}")

    def _check_disk_health(self, threshold):
        """Check disk usage."""
        try:
            # Get disk usage for the current directory
            disk_usage = psutil.disk_usage('.')
            usage_percent = (disk_usage.used / disk_usage.total) * 100

            status = 'HEALTHY'
            message = f"Disk usage: {usage_percent:.1f}% ({disk_usage.used // (1024**3)}GB / {disk_usage.total // (1024**3)}GB)"

            if usage_percent > threshold:
                status = 'WARNING'
                message += " - High disk usage detected"

            if usage_percent > 95:
                status = 'CRITICAL'
                message += " - Critical disk usage"

            metrics = {
                'usage_percent': usage_percent,
                'used_gb': disk_usage.used // (1024**3),
                'total_gb': disk_usage.total // (1024**3),
                'free_gb': disk_usage.free // (1024**3)
            }

            log_system_health('disk', status, message, metrics)
            self.stdout.write(f"Disk: {status} - {message}")

        except Exception as e:
            status = 'CRITICAL'
            message = f"Disk check failed: {str(e)}"
            log_system_health('disk', status, message, {'error': str(e)})
            self.stdout.write(f"Disk: {status} - {message}")

    def _check_memory_health(self, threshold):
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent

            status = 'HEALTHY'
            message = f"Memory usage: {usage_percent:.1f}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"

            if usage_percent > threshold:
                status = 'WARNING'
                message += " - High memory usage detected"

            if usage_percent > 95:
                status = 'CRITICAL'
                message += " - Critical memory usage"

            metrics = {
                'usage_percent': usage_percent,
                'used_gb': memory.used // (1024**3),
                'total_gb': memory.total // (1024**3),
                'available_gb': memory.available // (1024**3)
            }

            log_system_health('memory', status, message, metrics)
            self.stdout.write(f"Memory: {status} - {message}")

        except Exception as e:
            status = 'CRITICAL'
            message = f"Memory check failed: {str(e)}"
            log_system_health('memory', status, message, {'error': str(e)})
            self.stdout.write(f"Memory: {status} - {message}")

    def _check_cpu_health(self, threshold):
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            status = 'HEALTHY'
            message = f"CPU usage: {cpu_percent:.1f}% ({cpu_count} cores)"

            if cpu_percent > threshold:
                status = 'WARNING'
                message += " - High CPU usage detected"

            if cpu_percent > 95:
                status = 'CRITICAL'
                message += " - Critical CPU usage"

            metrics = {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }

            log_system_health('cpu', status, message, metrics)
            self.stdout.write(f"CPU: {status} - {message}")

        except Exception as e:
            status = 'CRITICAL'
            message = f"CPU check failed: {str(e)}"
            log_system_health('cpu', status, message, {'error': str(e)})
            self.stdout.write(f"CPU: {status} - {message}")

    def _check_log_health(self, threshold):
        """Check log file health and growth."""
        try:
            log_dir = settings.BASE_DIR / 'logs'
            if not log_dir.exists():
                log_system_health('logs', 'WARNING', 'Log directory does not exist')
                self.stdout.write("Logs: WARNING - Log directory does not exist")
                return

            total_size = 0
            log_files = []
            
            for log_file in log_dir.glob('*.log'):
                file_size = log_file.stat().st_size
                total_size += file_size
                log_files.append({
                    'name': log_file.name,
                    'size_mb': file_size / (1024 * 1024)
                })

            total_size_mb = total_size / (1024 * 1024)
            
            # Check for large log files
            large_files = [f for f in log_files if f['size_mb'] > 100]  # 100MB threshold
            
            status = 'HEALTHY'
            message = f"Log files total size: {total_size_mb:.1f}MB ({len(log_files)} files)"

            if large_files:
                status = 'WARNING'
                message += f" - {len(large_files)} large log files detected"

            if total_size_mb > 1000:  # 1GB threshold
                status = 'CRITICAL'
                message += " - Total log size exceeds 1GB"

            metrics = {
                'total_size_mb': total_size_mb,
                'file_count': len(log_files),
                'large_files': len(large_files),
                'log_files': log_files
            }

            log_system_health('logs', status, message, metrics)
            self.stdout.write(f"Logs: {status} - {message}")

        except Exception as e:
            status = 'CRITICAL'
            message = f"Log check failed: {str(e)}"
            log_system_health('logs', status, message, {'error': str(e)})
            self.stdout.write(f"Logs: {status} - {message}")

    def _check_audit_log_health(self):
        """Check audit log system health."""
        try:
            # Check recent audit log activity
            recent_logs = AuditLog.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()

            # Check for any errors in recent logs
            recent_errors = AuditLog.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=1),
                action='ERROR'
            ).count()

            # Check security events
            recent_security_events = SecurityEvent.objects.filter(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()

            status = 'HEALTHY'
            message = f"Audit system: {recent_logs} logs, {recent_security_events} security events in last hour"

            if recent_errors > 0:
                status = 'WARNING'
                message += f" - {recent_errors} errors detected"

            if recent_logs == 0:
                status = 'WARNING'
                message += " - No recent audit activity"

            metrics = {
                'recent_logs': recent_logs,
                'recent_errors': recent_errors,
                'recent_security_events': recent_security_events
            }

            log_system_health('audit_system', status, message, metrics)
            self.stdout.write(f"Audit System: {status} - {message}")

        except Exception as e:
            status = 'CRITICAL'
            message = f"Audit system check failed: {str(e)}"
            log_system_health('audit_system', status, message, {'error': str(e)})
            self.stdout.write(f"Audit System: {status} - {message}") 