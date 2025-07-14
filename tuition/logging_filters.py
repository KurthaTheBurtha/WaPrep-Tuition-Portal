import logging
from django.conf import settings


class AuditFilter(logging.Filter):
    """
    Custom filter for audit logging that adds context information.
    """
    
    def filter(self, record):
        # Add default values for audit log format
        if not hasattr(record, 'user'):
            record.user = 'anonymous'
        if not hasattr(record, 'ip'):
            record.ip = 'unknown'
        if not hasattr(record, 'action'):
            record.action = 'unknown'
        if not hasattr(record, 'model'):
            record.model = 'unknown'
        if not hasattr(record, 'record_id'):
            record.record_id = 'unknown'
        return True


class SecurityFilter(logging.Filter):
    """
    Custom filter for security logging that adds context information.
    """
    
    def filter(self, record):
        # Add default values for security log format
        if not hasattr(record, 'user'):
            record.user = 'anonymous'
        if not hasattr(record, 'ip'):
            record.ip = 'unknown'
        if not hasattr(record, 'event_type'):
            record.event_type = 'unknown'
        return True


class SensitiveDataFilter(logging.Filter):
    """
    Filter that removes sensitive data from log messages.
    """
    
    def __init__(self, name=''):
        super().__init__(name)
        self.sensitive_fields = getattr(settings, 'AUDIT_LOG_SENSITIVE_FIELDS', [])
    
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # Replace sensitive data with placeholders
            for field in self.sensitive_fields:
                record.msg = record.msg.replace(field, '[REDACTED]')
        
        if hasattr(record, 'args') and isinstance(record.args, dict):
            # Filter sensitive data from log arguments
            for field in self.sensitive_fields:
                if field in record.args:
                    record.args[field] = '[REDACTED]'
        
        return True 