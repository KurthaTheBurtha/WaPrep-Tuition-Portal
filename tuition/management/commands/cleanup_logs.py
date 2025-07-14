from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from tuition.utils import cleanup_old_audit_logs
from tuition.models import AuditLog, SecurityEvent, SystemHealth, DataVersion
import os
import glob
from pathlib import Path


class Command(BaseCommand):
    help = 'Clean up old audit logs and maintain the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation'
        )
        parser.add_argument(
            '--type',
            choices=['all', 'audit', 'security', 'health', 'versions', 'files'],
            default='all',
            help='Type of cleanup to perform (default: all)'
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Override retention period in days'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        cleanup_type = options['type']
        days = options['days']

        if dry_run:
            self.stdout.write("DRY RUN MODE - No actual deletions will be performed")
            self.stdout.write("")

        if not force and not dry_run:
            self.stdout.write("This will permanently delete old audit logs and data.")
            confirm = input("Are you sure you want to continue? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write("Cleanup cancelled.")
                return

        self.stdout.write(f"Starting {cleanup_type} cleanup...")

        if cleanup_type in ['all', 'audit']:
            self._cleanup_audit_logs(dry_run, days)

        if cleanup_type in ['all', 'security']:
            self._cleanup_security_events(dry_run, days)

        if cleanup_type in ['all', 'health']:
            self._cleanup_health_records(dry_run, days)

        if cleanup_type in ['all', 'versions']:
            self._cleanup_data_versions(dry_run, days)

        if cleanup_type in ['all', 'files']:
            self._cleanup_log_files(dry_run)

        self.stdout.write("Cleanup completed.")

    def _cleanup_audit_logs(self, dry_run, days=None):
        """Clean up old audit logs."""
        retention_days = days or getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 365)
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)

        if dry_run:
            count = AuditLog.objects.filter(timestamp__lt=cutoff_date).count()
            self.stdout.write(f"Would delete {count} audit logs older than {retention_days} days")
        else:
            deleted_count = AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]
            self.stdout.write(f"Deleted {deleted_count} audit logs older than {retention_days} days")

    def _cleanup_security_events(self, dry_run, days=None):
        """Clean up old security events."""
        # Keep security events for 2 years by default
        retention_days = days or 730
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)

        if dry_run:
            count = SecurityEvent.objects.filter(timestamp__lt=cutoff_date).count()
            self.stdout.write(f"Would delete {count} security events older than {retention_days} days")
        else:
            deleted_count = SecurityEvent.objects.filter(timestamp__lt=cutoff_date).delete()[0]
            self.stdout.write(f"Deleted {deleted_count} security events older than {retention_days} days")

    def _cleanup_health_records(self, dry_run, days=None):
        """Clean up old system health records."""
        # Keep health records for 30 days by default
        retention_days = days or 30
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)

        if dry_run:
            count = SystemHealth.objects.filter(timestamp__lt=cutoff_date).count()
            self.stdout.write(f"Would delete {count} health records older than {retention_days} days")
        else:
            deleted_count = SystemHealth.objects.filter(timestamp__lt=cutoff_date).delete()[0]
            self.stdout.write(f"Deleted {deleted_count} health records older than {retention_days} days")

    def _cleanup_data_versions(self, dry_run, days=None):
        """Clean up old data versions."""
        # Keep data versions for 90 days by default
        retention_days = days or 90
        cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)

        if dry_run:
            count = DataVersion.objects.filter(created_at__lt=cutoff_date).count()
            self.stdout.write(f"Would delete {count} data versions older than {retention_days} days")
        else:
            deleted_count = DataVersion.objects.filter(created_at__lt=cutoff_date).delete()[0]
            self.stdout.write(f"Deleted {deleted_count} data versions older than {retention_days} days")

    def _cleanup_log_files(self, dry_run):
        """Clean up old log files."""
        log_dir = settings.BASE_DIR / 'logs'
        if not log_dir.exists():
            self.stdout.write("Log directory does not exist")
            return

        # Find old log files (older than 30 days)
        cutoff_time = timezone.now() - timezone.timedelta(days=30)
        old_files = []

        for log_file in log_dir.glob('*.log.*'):  # Rotated log files
            if log_file.stat().st_mtime < cutoff_time.timestamp():
                old_files.append(log_file)

        if dry_run:
            self.stdout.write(f"Would delete {len(old_files)} old log files")
            for file in old_files[:5]:  # Show first 5
                self.stdout.write(f"  {file.name}")
            if len(old_files) > 5:
                self.stdout.write(f"  ... and {len(old_files) - 5} more")
        else:
            deleted_count = 0
            for file in old_files:
                try:
                    file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.stdout.write(f"Error deleting {file.name}: {e}")
            self.stdout.write(f"Deleted {deleted_count} old log files")

    def _get_database_stats(self):
        """Get database statistics for reporting."""
        stats = {
            'audit_logs': AuditLog.objects.count(),
            'security_events': SecurityEvent.objects.count(),
            'health_records': SystemHealth.objects.count(),
            'data_versions': DataVersion.objects.count(),
        }

        # Get oldest records
        oldest_audit = AuditLog.objects.order_by('timestamp').first()
        oldest_security = SecurityEvent.objects.order_by('timestamp').first()
        oldest_health = SystemHealth.objects.order_by('timestamp').first()

        if oldest_audit:
            stats['oldest_audit'] = oldest_audit.timestamp
        if oldest_security:
            stats['oldest_security'] = oldest_security.timestamp
        if oldest_health:
            stats['oldest_health'] = oldest_health.timestamp

        return stats

    def _show_cleanup_summary(self):
        """Show a summary of what would be cleaned up."""
        self.stdout.write("CLEANUP SUMMARY:")
        self.stdout.write("=" * 50)

        # Database stats
        stats = self._get_database_stats()
        self.stdout.write(f"Current records in database:")
        self.stdout.write(f"  Audit logs: {stats['audit_logs']}")
        self.stdout.write(f"  Security events: {stats['security_events']}")
        self.stdout.write(f"  Health records: {stats['health_records']}")
        self.stdout.write(f"  Data versions: {stats['data_versions']}")

        # Retention periods
        self.stdout.write("")
        self.stdout.write("Retention periods:")
        self.stdout.write(f"  Audit logs: {getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 365)} days")
        self.stdout.write(f"  Security events: 730 days")
        self.stdout.write(f"  Health records: 30 days")
        self.stdout.write(f"  Data versions: 90 days")

        # Log file stats
        log_dir = settings.BASE_DIR / 'logs'
        if log_dir.exists():
            log_files = list(log_dir.glob('*.log*'))
            total_size = sum(f.stat().st_size for f in log_files)
            self.stdout.write("")
            self.stdout.write(f"Log files: {len(log_files)} files, {total_size / (1024*1024):.1f} MB total")

        self.stdout.write("=" * 50) 