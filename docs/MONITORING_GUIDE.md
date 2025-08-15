# WAPrep Tuition Portal - Monitoring and Logging System

## Overview

This document describes the comprehensive monitoring and logging system implemented for the WAPrep Tuition Portal. The system provides:

- **Database Change Tracking**: Automatic logging of all changes to student and payer data
- **Application-Level Logging**: Comprehensive logging with different levels and formats
- **Version Control**: Data versioning for critical records
- **Real-Time Monitoring**: System health checks and performance monitoring
- **Security Monitoring**: Detection and logging of security events
- **Compliance Reporting**: Audit reports for regulatory compliance

## Architecture

### Core Components

1. **Audit Models** (`tuition/models.py`)
   - `AuditLog`: Tracks all data changes
   - `DataVersion`: Stores version snapshots of records
   - `SystemHealth`: Monitors system performance
   - `SecurityEvent`: Logs security-related events

2. **Middleware** (`tuition/audit_middleware.py`)
   - `AuditMiddleware`: Captures request information
   - `SecurityMiddleware`: Monitors for security threats

3. **Model Mixins** (`tuition/model_mixins.py`)
   - `AuditMixin`: Automatic change tracking for models
   - Specialized mixins for different model types

4. **Utility Functions** (`tuition/utils.py`)
   - Logging functions
   - Data integrity checks
   - Cleanup utilities

5. **Management Commands**
   - `audit_report`: Generate compliance reports
   - `system_monitor`: Monitor system health
   - `cleanup_logs`: Maintain log retention

## Database Schema

### AuditLog Table

```sql
CREATE TABLE tuition_auditlog (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    action VARCHAR(20) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    user_id INTEGER,
    user_ip VARCHAR(45),
    user_agent TEXT,
    field_name VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    description TEXT,
    metadata JSON,
    session_id VARCHAR(100),
    request_id VARCHAR(100)
);
```

### DataVersion Table

```sql
CREATE TABLE tuition_dataversion (
    id INTEGER PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    data_snapshot JSON NOT NULL,
    created_at DATETIME NOT NULL,
    created_by_id INTEGER,
    UNIQUE(model_name, record_id, version_number)
);
```

### SystemHealth Table

```sql
CREATE TABLE tuition_systemhealth (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    component VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    metrics JSON
);
```

### SecurityEvent Table

```sql
CREATE TABLE tuition_securityevent (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    user_id INTEGER,
    user_ip VARCHAR(45),
    user_agent TEXT,
    metadata JSON,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at DATETIME,
    resolved_by_id INTEGER
);
```

## Configuration

### Settings Configuration

Add to `settings.py`:

```python
# LOGGING CONFIGURATION
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'audit': {
            'format': '{asctime} | {levelname} | {user} | {ip} | {action} | {model} | {record_id} | {message}',
            'style': '{',
        },
        'security': {
            'format': '{asctime} | SECURITY | {levelname} | {user} | {ip} | {event_type} | {message}',
            'style': '{',
        },
    },
    'handlers': {
        'audit_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'audit',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 10,
            'formatter': 'security',
        },
    },
    'loggers': {
        'tuition.audit': {
            'handlers': ['audit_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'tuition.security': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# AUDIT SETTINGS
AUDIT_LOG_ENABLED = True
AUDIT_LOG_SENSITIVE_FIELDS = [
    'password', 'password_hash', 'stripe_customer_id', 'stripe_payment_method_id',
    'provider_token', 'routing_number', 'account_number', 'last4'
]
AUDIT_LOG_MAX_VALUE_LENGTH = 1000
AUDIT_LOG_RETENTION_DAYS = 365

# SECURITY SETTINGS
SECURITY_LOG_ENABLED = True
SECURITY_LOG_FAILED_LOGIN_ATTEMPTS = 5
SECURITY_LOG_SUSPICIOUS_ACTIVITY_THRESHOLD = 10
SECURITY_LOG_RATE_LIMIT_PER_MINUTE = 100

# MONITORING SETTINGS
MONITORING_ENABLED = True
MONITORING_HEALTH_CHECK_INTERVAL = 300  # 5 minutes
MONITORING_PERFORMANCE_THRESHOLD = 2.0  # seconds
```

### Middleware Configuration

Add to `MIDDLEWARE` in `settings.py`:

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'tuition.audit_middleware.AuditMiddleware',
    'tuition.audit_middleware.SecurityMiddleware',
]
```

## Usage

### Automatic Change Tracking

The system automatically tracks changes to models that inherit from audit mixins:

```python
# Models automatically inherit audit functionality
class Student(models.Model, StudentAuditMixin):
    # ... model fields ...

class Payment(models.Model, PaymentAuditMixin):
    # ... model fields ...

class User(AbstractUser, UserAuditMixin):
    # ... model fields ...
```

### Manual Audit Logging

```python
from tuition.utils import log_audit_event, log_security_event

# Log a custom audit event
log_audit_event(
    action='CUSTOM_ACTION',
    model_name='Student',
    record_id=student.id,
    user=request.user,
    description='Custom action performed',
    request=request
)

# Log a security event
log_security_event(
    event_type='SUSPICIOUS_ACTIVITY',
    severity='MEDIUM',
    description='Unusual activity detected',
    user=request.user,
    user_ip=get_client_ip(request)
)
```

### System Health Monitoring

```python
from tuition.utils import log_system_health

# Log system health
log_system_health(
    component='database',
    status='HEALTHY',
    message='Database connection OK',
    metrics={'query_time': 0.5, 'connections': 10}
)
```

## Management Commands

### Generate Audit Reports

```bash
# Generate summary report
python manage.py audit_report --type summary --days 30

# Generate detailed report
python manage.py audit_report --type detailed --days 7 --format csv --output report.csv

# Generate security report
python manage.py audit_report --type security --days 7 --format json
```

### System Monitoring

```bash
# Run health checks
python manage.py system_monitor --check all

# Monitor specific component
python manage.py system_monitor --check database --threshold 90

# Continuous monitoring
python manage.py system_monitor --continuous --interval 300
```

### Log Cleanup

```bash
# Preview what would be cleaned up
python manage.py cleanup_logs --dry-run

# Clean up old logs
python manage.py cleanup_logs --force

# Clean up specific types
python manage.py cleanup_logs --type audit --days 180
```

## API Endpoints

### Health Check

```
GET /health/
```

Returns system health status:

```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "checks": {
        "database": {
            "status": "healthy",
            "message": "Database connection OK"
        },
        "memory": {
            "status": "healthy",
            "message": "Memory usage: 45.2%",
            "usage_percent": 45.2
        },
        "disk": {
            "status": "healthy",
            "message": "Disk usage: 67.8%",
            "usage_percent": 67.8
        }
    }
}
```

### Audit Summary

```
GET /monitoring/audit-summary/?days=30
```

Returns audit activity summary (admin only):

```json
{
    "audit_summary": [
        {
            "action": "UPDATE",
            "model_name": "Student",
            "count": 45
        }
    ],
    "security_summary": [
        {
            "event_type": "LOGIN_FAILURE",
            "severity": "HIGH",
            "count": 3
        }
    ],
    "user_activity": [
        {
            "user__username": "admin",
            "action_count": 156
        }
    ],
    "period_days": 30
}
```

### Security Events

```
GET /monitoring/security-events/?days=7
```

Returns recent security events (admin only):

```json
{
    "events": [
        {
            "id": 1,
            "timestamp": "2024-01-15T10:30:00Z",
            "event_type": "LOGIN_FAILURE",
            "severity": "HIGH",
            "description": "Multiple failed login attempts",
            "user": null,
            "user_ip": "192.168.1.100",
            "resolved": false,
            "metadata": {"failed_attempts": 5}
        }
    ],
    "total_count": 15,
    "unresolved_count": 3,
    "period_days": 7
}
```

## Security Features

### Rate Limiting

The system automatically tracks request frequency and logs rate limit violations:

- Default limit: 100 requests per minute per IP
- Configurable via `SECURITY_LOG_RATE_LIMIT_PER_MINUTE`

### Failed Login Detection

- Tracks failed login attempts per IP
- Default threshold: 5 failed attempts in 15 minutes
- Configurable via `SECURITY_LOG_FAILED_LOGIN_ATTEMPTS`

### Suspicious Activity Detection

- Monitors for scanning attempts (404 responses to admin paths)
- Tracks unauthorized access attempts (403 responses)
- Logs unusual patterns in user activity

### Data Protection

- Sensitive fields are automatically redacted in logs
- Configurable via `AUDIT_LOG_SENSITIVE_FIELDS`
- Password changes are tracked but values are redacted

## Compliance Features

### GDPR Compliance

- Data retention policies are configurable
- Right to be forgotten: audit logs can be cleaned up
- Data export capabilities through audit reports

### HIPAA Compliance

- All access to student data is logged
- Audit trails for data modifications
- Secure logging with sensitive data redaction

### Financial Compliance

- Payment changes are tracked with full audit trail
- Balance modifications are logged with before/after values
- Payment method changes are monitored

## Monitoring Dashboard

### Key Metrics

1. **System Health**
   - Database connectivity
   - Memory and disk usage
   - CPU utilization
   - Response times

2. **Audit Activity**
   - Changes per model type
   - User activity levels
   - Data modification patterns

3. **Security Events**
   - Failed login attempts
   - Unauthorized access
   - Suspicious activity
   - Rate limit violations

4. **Performance Metrics**
   - Query response times
   - Log file sizes
   - System resource usage

### Alerting

The system can be configured to send alerts for:

- Critical system health issues
- High security event rates
- Performance degradation
- Data integrity issues

## Maintenance

### Log Rotation

- Audit logs: 10MB max, 10 backup files
- Security logs: 10MB max, 10 backup files
- General logs: 10MB max, 5 backup files

### Retention Policies

- Audit logs: 1 year (configurable)
- Security events: 2 years
- System health: 30 days
- Data versions: 90 days

### Cleanup Schedule

Recommended cleanup schedule:

```bash
# Daily: System health monitoring
0 */6 * * * python manage.py system_monitor --check all

# Weekly: Log cleanup
0 2 * * 0 python manage.py cleanup_logs --force

# Monthly: Audit report generation
0 2 1 * * python manage.py audit_report --type summary --days 30 --output monthly_report.txt
```

## Troubleshooting

### Common Issues

1. **High Log Volume**
   - Check for excessive audit logging
   - Review security event thresholds
   - Consider adjusting retention policies

2. **Performance Impact**
   - Monitor database query performance
   - Check log file sizes
   - Review middleware overhead

3. **Missing Logs**
   - Verify logging configuration
   - Check file permissions
   - Ensure log directory exists

### Debug Commands

```bash
# Check log file sizes
ls -lh logs/

# View recent audit logs
tail -f logs/audit.log

# Check system health
python manage.py system_monitor --check all

# Generate debug report
python manage.py audit_report --type detailed --days 1
```

## Best Practices

1. **Regular Monitoring**
   - Set up automated health checks
   - Review security events daily
   - Monitor log file growth

2. **Data Protection**
   - Regularly review sensitive field lists
   - Test data redaction
   - Verify audit trail completeness

3. **Performance Optimization**
   - Index audit tables appropriately
   - Clean up old logs regularly
   - Monitor query performance

4. **Security Hardening**
   - Review security event thresholds
   - Monitor for unusual patterns
   - Keep retention policies updated

## Support

For issues with the monitoring system:

1. Check the logs in the `logs/` directory
2. Run health checks: `python manage.py system_monitor`
3. Generate debug reports: `python manage.py audit_report --type detailed`
4. Review system configuration in `settings.py`

## Future Enhancements

1. **Real-time Dashboard**
   - Web-based monitoring interface
   - Real-time alerts and notifications
   - Interactive charts and graphs

2. **Advanced Analytics**
   - Machine learning for anomaly detection
   - Predictive maintenance alerts
   - User behavior analysis

3. **Integration**
   - External monitoring systems (ELK, Splunk)
   - SIEM integration
   - Cloud monitoring services

4. **Compliance Automation**
   - Automated compliance reports
   - Regulatory requirement tracking
   - Audit trail validation 