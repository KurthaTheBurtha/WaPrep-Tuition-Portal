from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from tuition.utils import get_audit_summary
from tuition.models import AuditLog, SecurityEvent, SystemHealth
import json
from django.db import models


class Command(BaseCommand):
    help = 'Generate audit reports for monitoring and compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to include in the report (default: 30)'
        )
        parser.add_argument(
            '--format',
            choices=['json', 'text', 'csv'],
            default='text',
            help='Output format (default: text)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (optional)'
        )
        parser.add_argument(
            '--type',
            choices=['summary', 'detailed', 'security', 'health'],
            default='summary',
            help='Report type (default: summary)'
        )

    def handle(self, *args, **options):
        days = options['days']
        output_format = options['format']
        output_file = options['output']
        report_type = options['type']

        self.stdout.write(f"Generating {report_type} audit report for the last {days} days...")

        if report_type == 'summary':
            report_data = self._generate_summary_report(days)
        elif report_type == 'detailed':
            report_data = self._generate_detailed_report(days)
        elif report_type == 'security':
            report_data = self._generate_security_report(days)
        elif report_type == 'health':
            report_data = self._generate_health_report(days)

        # Format and output the report
        if output_format == 'json':
            output = json.dumps(report_data, indent=2, default=str)
        elif output_format == 'csv':
            output = self._format_as_csv(report_data, report_type)
        else:  # text
            output = self._format_as_text(report_data, report_type)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            self.stdout.write(f"Report saved to {output_file}")
        else:
            self.stdout.write(output)

    def _generate_summary_report(self, days):
        """Generate a summary report of audit activity."""
        summary = get_audit_summary(days)
        
        # Add additional statistics
        cutoff_date = timezone.now() - timedelta(days=days)
        
        total_audit_logs = AuditLog.objects.filter(timestamp__gte=cutoff_date).count()
        total_security_events = SecurityEvent.objects.filter(timestamp__gte=cutoff_date).count()
        total_health_records = SystemHealth.objects.filter(timestamp__gte=cutoff_date).count()
        
        # Get top users by activity
        top_users = AuditLog.objects.filter(
            timestamp__gte=cutoff_date,
            user__isnull=False
        ).values('user__username').annotate(
            action_count=models.Count('id')
        ).order_by('-action_count')[:5]
        
        return {
            'report_type': 'summary',
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'statistics': {
                'total_audit_logs': total_audit_logs,
                'total_security_events': total_security_events,
                'total_health_records': total_health_records,
            },
            'audit_summary': summary['audit_summary'],
            'security_summary': summary['security_summary'],
            'top_users': list(top_users),
        }

    def _generate_detailed_report(self, days):
        """Generate a detailed report with all audit logs."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        audit_logs = AuditLog.objects.filter(
            timestamp__gte=cutoff_date
        ).select_related('user').order_by('-timestamp')
        
        detailed_logs = []
        for log in audit_logs:
            detailed_logs.append({
                'timestamp': log.timestamp.isoformat(),
                'action': log.action,
                'model_name': log.model_name,
                'record_id': log.record_id,
                'user': log.user.username if log.user else 'anonymous',
                'user_ip': log.user_ip,
                'field_name': log.field_name,
                'old_value': log.old_value,
                'new_value': log.new_value,
                'description': log.description,
            })
        
        return {
            'report_type': 'detailed',
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'total_records': len(detailed_logs),
            'audit_logs': detailed_logs,
        }

    def _generate_security_report(self, days):
        """Generate a security-focused report."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        security_events = SecurityEvent.objects.filter(
            timestamp__gte=cutoff_date
        ).select_related('user').order_by('-timestamp')
        
        # Group by severity
        severity_counts = {}
        event_details = []
        
        for event in security_events:
            severity = event.severity
            if severity not in severity_counts:
                severity_counts[severity] = 0
            severity_counts[severity] += 1
            
            event_details.append({
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'severity': event.severity,
                'description': event.description,
                'user': event.user.username if event.user else 'anonymous',
                'user_ip': event.user_ip,
                'resolved': event.resolved,
                'metadata': event.metadata,
            })
        
        return {
            'report_type': 'security',
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'total_events': len(event_details),
            'severity_breakdown': severity_counts,
            'unresolved_events': len([e for e in event_details if not e['resolved']]),
            'security_events': event_details,
        }

    def _generate_health_report(self, days):
        """Generate a system health report."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        health_records = SystemHealth.objects.filter(
            timestamp__gte=cutoff_date
        ).order_by('-timestamp')
        
        # Group by component and status
        component_status = {}
        health_details = []
        
        for record in health_records:
            component = record.component
            if component not in component_status:
                component_status[component] = {}
            
            status = record.status
            if status not in component_status[component]:
                component_status[component][status] = 0
            component_status[component][status] += 1
            
            health_details.append({
                'timestamp': record.timestamp.isoformat(),
                'component': record.component,
                'status': record.status,
                'message': record.message,
                'metrics': record.metrics,
            })
        
        return {
            'report_type': 'health',
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'total_records': len(health_details),
            'component_status': component_status,
            'health_records': health_details,
        }

    def _format_as_text(self, data, report_type):
        """Format report data as human-readable text."""
        output = []
        output.append("=" * 80)
        output.append(f"AUDIT REPORT - {report_type.upper()}")
        output.append("=" * 80)
        output.append(f"Generated: {data['generated_at']}")
        output.append(f"Period: Last {data['period_days']} days")
        output.append("")
        
        if report_type == 'summary':
            output.append("STATISTICS:")
            output.append(f"  Total Audit Logs: {data['statistics']['total_audit_logs']}")
            output.append(f"  Total Security Events: {data['statistics']['total_security_events']}")
            output.append(f"  Total Health Records: {data['statistics']['total_health_records']}")
            output.append("")
            
            output.append("TOP AUDIT ACTIONS:")
            for item in data['audit_summary'][:5]:
                output.append(f"  {item['action']} on {item['model_name']}: {item['count']} times")
            output.append("")
            
            output.append("SECURITY EVENTS:")
            for item in data['security_summary'][:5]:
                output.append(f"  {item['event_type']} ({item['severity']}): {item['count']} times")
            output.append("")
            
            output.append("TOP USERS BY ACTIVITY:")
            for item in data['top_users']:
                output.append(f"  {item['user__username']}: {item['action_count']} actions")
        
        elif report_type == 'detailed':
            output.append(f"TOTAL RECORDS: {data['total_records']}")
            output.append("")
            output.append("DETAILED AUDIT LOGS:")
            for log in data['audit_logs'][:20]:  # Show first 20
                output.append(f"  {log['timestamp']} | {log['action']} | {log['model_name']} #{log['record_id']} | {log['user']}")
                if log['field_name']:
                    output.append(f"    Field: {log['field_name']} | Old: {log['old_value']} | New: {log['new_value']}")
                output.append("")
        
        elif report_type == 'security':
            output.append(f"TOTAL EVENTS: {data['total_events']}")
            output.append(f"UNRESOLVED EVENTS: {data['unresolved_events']}")
            output.append("")
            output.append("SEVERITY BREAKDOWN:")
            for severity, count in data['severity_breakdown'].items():
                output.append(f"  {severity}: {count}")
            output.append("")
            output.append("SECURITY EVENTS:")
            for event in data['security_events'][:10]:  # Show first 10
                output.append(f"  {event['timestamp']} | {event['event_type']} | {event['severity']} | {event['user_ip']}")
                output.append(f"    {event['description']}")
                output.append("")
        
        elif report_type == 'health':
            output.append(f"TOTAL RECORDS: {data['total_records']}")
            output.append("")
            output.append("COMPONENT STATUS:")
            for component, statuses in data['component_status'].items():
                output.append(f"  {component}:")
                for status, count in statuses.items():
                    output.append(f"    {status}: {count}")
            output.append("")
            output.append("RECENT HEALTH RECORDS:")
            for record in data['health_records'][:10]:  # Show first 10
                output.append(f"  {record['timestamp']} | {record['component']} | {record['status']}")
                if record['message']:
                    output.append(f"    {record['message']}")
                output.append("")
        
        return "\n".join(output)

    def _format_as_csv(self, data, report_type):
        """Format report data as CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        if report_type == 'summary':
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Audit Logs', data['statistics']['total_audit_logs']])
            writer.writerow(['Total Security Events', data['statistics']['total_security_events']])
            writer.writerow(['Total Health Records', data['statistics']['total_health_records']])
            writer.writerow([])
            writer.writerow(['Action', 'Model', 'Count'])
            for item in data['audit_summary']:
                writer.writerow([item['action'], item['model_name'], item['count']])
        
        elif report_type == 'detailed':
            writer.writerow(['Timestamp', 'Action', 'Model', 'Record ID', 'User', 'Field', 'Old Value', 'New Value'])
            for log in data['audit_logs']:
                writer.writerow([
                    log['timestamp'], log['action'], log['model_name'], log['record_id'],
                    log['user'], log['field_name'], log['old_value'], log['new_value']
                ])
        
        elif report_type == 'security':
            writer.writerow(['Timestamp', 'Event Type', 'Severity', 'User', 'IP', 'Description', 'Resolved'])
            for event in data['security_events']:
                writer.writerow([
                    event['timestamp'], event['event_type'], event['severity'],
                    event['user'], event['user_ip'], event['description'], event['resolved']
                ])
        
        elif report_type == 'health':
            writer.writerow(['Timestamp', 'Component', 'Status', 'Message'])
            for record in data['health_records']:
                writer.writerow([
                    record['timestamp'], record['component'], record['status'], record['message']
                ])
        
        return output.getvalue() 