import re
from typing import Tuple, List
import logging
import hashlib
import json
from django.utils import timezone
from django.conf import settings
from django.http import HttpRequest
from .models import AuditLog, DataVersion, SystemHealth, SecurityEvent
from django.db import models


logger = logging.getLogger('tuition.audit')


# Common weak passwords to block
COMMON_PASSWORDS = {
    'password', 'password123', '123456', '123456789', 'qwerty', 'abc123',
    'password1', 'admin', 'letmein', 'welcome', 'monkey', 'dragon',
    'master', 'hello', 'freedom', 'whatever', 'qwerty123', 'trustno1',
    'jordan', 'harley', 'ranger', 'iwantu', 'jennifer', 'hunter',
    'buster', 'soccer', 'baseball', 'tiger', 'charlie', 'andrew',
    'michelle', 'love', 'sunshine', 'jessica', 'asshole', '696969',
    'killer', 'mustang', 'shadow', 'merlin', 'diamond', 'nascar',
    'jackson', 'cameron', '654321', 'computer', 'amanda', 'wizard',
    'xxxxxxxx', 'money', 'phoenix', 'mickey', 'bailey', 'knight',
    'iceman', 'tigers', 'purple', 'andrea', 'horny', 'dakota',
    'aaaaaa', 'player', 'sunshine', 'morgan', 'starwars', 'boomer',
    'cowboys', 'edward', 'charles', 'girls', 'coffee', 'bulldog',
    'ncc1701', 'rabbit', 'peanut', 'johnson', 'chester', 'london',
    'midnight', 'blue', 'fishing', '000000', 'hannah', 'slayer',
    '111111', 'rachel', 'test', 'bitch', 'orange', 'michelle',
    'helpme', 'fuckme', 'tucker', 'secret', 'god', 'zxcvbnm',
    'mercedes', 'beer', 'jackson', 'cowboy', 'silver', 'johnson',
    'thomas', 'hunter', 'michelle', 'charlie', 'andrew', 'matthew',
    'access', 'yankees', '987654321', 'dallas', 'austin', 'thunder',
    'taylor', 'matrix', 'mobilemail', 'mom', 'monitor', 'monitoring',
    'montana', 'moon', 'moscow', 'mother', 'movie', 'mozilla',
    'music', 'mustang', 'password', 'pa$$w0rd', 'p@ssw0rd', 'p@$$w0rd'
}

def validate_password(password: str, user=None) -> Tuple[bool, str]:
    """
    Validate password strength and return (is_valid, message).
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one number
    - At least one special character (!@#$%^&*)
    - Not a common password
    - No consecutive repeating characters (e.g., 'aaa')
    - No keyboard patterns (e.g., 'qwerty', '123456')
    - Not recently used by the same user (if user is provided)
    """
    if not password:
        return False, "Password is required"
    
    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check maximum length (reasonable limit)
    if len(password) > 128:
        return False, "Password is too long (maximum 128 characters)"
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for number
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    # Check for special character
    if not re.search(r'[!@#$%^&*]', password):
        return False, "Password must contain at least one special character (!@#$%^&*)"
    
    # Check for common passwords
    if password.lower() in COMMON_PASSWORDS:
        return False, "This password is too common. Please choose a more unique password"
    
    # Check for consecutive repeating characters (more than 2)
    if re.search(r'(.)\1{2,}', password):
        return False, "Password cannot contain more than 2 consecutive identical characters"
    
    # Check for keyboard patterns
    keyboard_patterns = [
        'qwerty', 'asdfgh', 'zxcvbn', '123456', '654321',
        'abcdef', 'ghijkl', 'mnopqr', 'stuvwx', 'yzabcd'
    ]
    password_lower = password.lower()
    for pattern in keyboard_patterns:
        if pattern in password_lower:
            return False, "Password cannot contain keyboard patterns"
    
    # Check for personal information patterns (basic check)
    personal_patterns = [
        r'\b(admin|root|user|test|guest|demo)\b',
        r'\b(password|pass|pwd|secret)\b',
        r'\b(123|321|000|111|222|333|444|555|666|777|888|999)\b'
    ]
    for pattern in personal_patterns:
        if re.search(pattern, password_lower):
            return False, "Password contains common insecure patterns"
    
    # Check if password has been used recently by this user
    if user:
        try:
            from .models import PasswordHistory
            if PasswordHistory.is_password_reused(user, password):
                return False, "You cannot reuse any of your last 5 passwords. Please choose a different password."
        except ImportError:
            # If PasswordHistory model is not available (e.g., during migrations), skip this check
            pass
    
    return True, "Password meets all security requirements"

def get_password_strength(password: str) -> Tuple[str, int]:
    """
    Calculate password strength and return (strength_label, score).
    
    Returns:
    - strength_label: 'Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'
    - score: 0-100
    """
    if not password:
        return "Very Weak", 0
    
    score = 0
    
    # Length contribution (up to 25 points)
    if len(password) >= 8:
        score += 10
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 5
    
    # Character variety contribution (up to 40 points)
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'\d', password):
        score += 10
    if re.search(r'[!@#$%^&*]', password):
        score += 10
    
    # Complexity bonus (up to 20 points)
    unique_chars = len(set(password))
    if unique_chars >= 8:
        score += 10
    if unique_chars >= 12:
        score += 10
    
    # Penalties
    if password.lower() in COMMON_PASSWORDS:
        score -= 30
    if re.search(r'(.)\1{2,}', password):
        score -= 15
    if len(password) < 8:
        score -= 20
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
    # Determine strength label
    if score < 20:
        return "Very Weak", score
    elif score < 40:
        return "Weak", score
    elif score < 60:
        return "Fair", score
    elif score < 80:
        return "Good", score
    elif score < 90:
        return "Strong", score
    else:
        return "Very Strong", score

def generate_strong_password() -> str:
    """
    Generate a strong password that meets all requirements.
    """
    import random
    import string
    
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"
    
    # Ensure at least one of each required character type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Fill the rest with random characters
    all_chars = lowercase + uppercase + digits + special
    for _ in range(4):  # Total length will be 8
        password.append(random.choice(all_chars))
    
    # Shuffle the password
    random.shuffle(password)
    
    return ''.join(password)

def clear_messages(request):
    """
    Clear all Django messages from the request.
    Useful for preventing message persistence across redirects.
    """
    from django.contrib import messages
    storage = messages.get_messages(request)
    storage.used = True 


def get_client_ip(request: HttpRequest) -> str:
    """
    Get the client's IP address from the request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_audit_event(action: str, model_name: str, record_id: int, user=None, 
                   field_name=None, old_value=None, new_value=None, 
                   description=None, metadata=None, request=None):
    """
    Log an audit event with comprehensive information.
    """
    if not getattr(settings, 'AUDIT_LOG_ENABLED', True):
        return None
    
    # Get request information if available
    user_ip = None
    user_agent = None
    session_id = None
    request_id = None
    
    if request:
        user_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session_id = request.session.session_key if hasattr(request, 'session') else None
        request_id = getattr(request, 'request_id', None)
    
    # Filter sensitive data
    if field_name in getattr(settings, 'AUDIT_LOG_SENSITIVE_FIELDS', []):
        old_value = '[REDACTED]'
        new_value = '[REDACTED]'
    
    # Truncate values if too long
    max_length = getattr(settings, 'AUDIT_LOG_MAX_VALUE_LENGTH', 1000)
    if old_value and len(str(old_value)) > max_length:
        old_value = str(old_value)[:max_length-3] + '...'
    if new_value and len(str(new_value)) > max_length:
        new_value = str(new_value)[:max_length-3] + '...'
    
    # Create audit log entry
    audit_log = AuditLog.log_change(
        action=action,
        model_name=model_name,
        record_id=record_id,
        user=user,
        field_name=field_name or '',
        old_value=old_value or '',
        new_value=new_value or '',
        description=description or '',
        metadata=metadata or {},
        user_ip=user_ip,
        user_agent=user_agent,
        session_id=session_id,
        request_id=request_id,
    )
    
    # Log to file system as well
    logger.info(
        f"{action} on {model_name} #{record_id}",
        extra={
            'user': user.username if user else 'anonymous',
            'ip': user_ip or 'unknown',
            'action': action,
            'model': model_name,
            'record_id': record_id,
        }
    )
    
    return audit_log


def create_data_version(model_name: str, record_id: int, data_snapshot: dict, user=None):
    """
    Create a version snapshot of a record.
    """
    return DataVersion.create_version(
        model_name=model_name,
        record_id=record_id,
        data_snapshot=data_snapshot,
        user=user
    )


def log_security_event(event_type: str, severity: str, description: str, 
                      user=None, user_ip=None, metadata=None):
    """
    Log a security event.
    """
    if not getattr(settings, 'SECURITY_LOG_ENABLED', True):
        return None
    
    security_logger = logging.getLogger('tuition.security')
    
    # Create security event
    security_event = SecurityEvent.objects.create(
        event_type=event_type,
        severity=severity,
        description=description,
        user=user,
        user_ip=user_ip,
        metadata=metadata or {}
    )
    
    # Log to file system
    security_logger.warning(
        description,
        extra={
            'user': user.username if user else 'anonymous',
            'ip': user_ip or 'unknown',
            'event_type': event_type,
        }
    )
    
    return security_event


def log_system_health(component: str, status: str, message: str = '', metrics: dict = None):
    """
    Log system health information.
    """
    if not getattr(settings, 'MONITORING_ENABLED', True):
        return None
    
    monitoring_logger = logging.getLogger('tuition.monitoring')
    
    # Create system health record
    health_record = SystemHealth.objects.create(
        component=component,
        status=status,
        message=message,
        metrics=metrics or {}
    )
    
    # Log to file system
    monitoring_logger.info(
        f"{component}: {status} - {message}",
        extra={'metrics': metrics or {}}
    )
    
    return health_record


def calculate_data_integrity_hash(data: dict) -> str:
    """
    Calculate a hash for data integrity checking.
    """
    # Sort the data to ensure consistent hashing
    sorted_data = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(sorted_data.encode()).hexdigest()


def check_data_integrity(model_instance, fields_to_check=None):
    """
    Check data integrity for a model instance.
    """
    if fields_to_check is None:
        fields_to_check = [field.name for field in model_instance._meta.fields 
                          if not field.name.startswith('_')]
    
    data = {}
    for field_name in fields_to_check:
        if hasattr(model_instance, field_name):
            data[field_name] = getattr(model_instance, field_name)
    
    return calculate_data_integrity_hash(data)


def get_model_changes(old_instance, new_instance, fields_to_track=None):
    """
    Get the changes between two model instances.
    """
    if fields_to_track is None:
        fields_to_track = [field.name for field in new_instance._meta.fields 
                          if not field.name.startswith('_')]
    
    changes = {}
    for field_name in fields_to_track:
        if hasattr(old_instance, field_name) and hasattr(new_instance, field_name):
            old_value = getattr(old_instance, field_name)
            new_value = getattr(new_instance, field_name)
            
            if old_value != new_value:
                changes[field_name] = {
                    'old': old_value,
                    'new': new_value
                }
    
    return changes


def cleanup_old_audit_logs():
    """
    Clean up old audit logs based on retention policy.
    """
    retention_days = getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 365)
    cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)
    
    # Delete old audit logs
    deleted_count = AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]
    
    # Delete old security events (keep for 2 years)
    security_cutoff = timezone.now() - timezone.timedelta(days=730)
    security_deleted = SecurityEvent.objects.filter(timestamp__lt=security_cutoff).delete()[0]
    
    # Delete old system health records (keep for 30 days)
    health_cutoff = timezone.now() - timezone.timedelta(days=30)
    health_deleted = SystemHealth.objects.filter(timestamp__lt=health_cutoff).delete()[0]
    
    logger.info(
        f"Cleaned up old logs: {deleted_count} audit logs, {security_deleted} security events, {health_deleted} health records"
    )
    
    return {
        'audit_logs_deleted': deleted_count,
        'security_events_deleted': security_deleted,
        'health_records_deleted': health_deleted
    }


def get_audit_summary(days=30):
    """
    Get a summary of audit activity for the specified number of days.
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    # Get audit log summary
    audit_summary = AuditLog.objects.filter(
        timestamp__gte=cutoff_date
    ).values('action', 'model_name').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    # Get security events summary
    security_summary = SecurityEvent.objects.filter(
        timestamp__gte=cutoff_date
    ).values('event_type', 'severity').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    # Get user activity summary
    user_activity = AuditLog.objects.filter(
        timestamp__gte=cutoff_date,
        user__isnull=False
    ).values('user__username').annotate(
        action_count=models.Count('id')
    ).order_by('-action_count')[:10]
    
    return {
        'audit_summary': list(audit_summary),
        'security_summary': list(security_summary),
        'user_activity': list(user_activity),
        'period_days': days
    } 