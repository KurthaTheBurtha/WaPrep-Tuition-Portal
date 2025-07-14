import logging
import uuid
import json
from django.utils import timezone
from django.conf import settings
from .models import AuditLog, SecurityEvent
from .utils import get_client_ip


logger = logging.getLogger('tuition.audit')


class AuditMiddleware:
    """
    Middleware to automatically capture audit information from requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Generate unique request ID
        request.request_id = str(uuid.uuid4())
        
        # Add request start time
        request.start_time = timezone.now()
        
        # Get client information
        client_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Log request start
        if hasattr(request, 'user') and request.user.is_authenticated:
            logger.info(
                f"Request started: {request.method} {request.path}",
                extra={
                    'user': request.user.username,
                    'ip': client_ip,
                    'action': 'REQUEST_START',
                    'model': 'HTTP_REQUEST',
                    'record_id': request.request_id,
                    'user_agent': user_agent,
                }
            )
        
        # Process the request
        response = self.get_response(request)
        
        # Calculate request duration
        duration = (timezone.now() - request.start_time).total_seconds()
        
        # Log request completion
        if hasattr(request, 'user') and request.user.is_authenticated:
            logger.info(
                f"Request completed: {request.method} {request.path} - {response.status_code} ({duration:.2f}s)",
                extra={
                    'user': request.user.username,
                    'ip': client_ip,
                    'action': 'REQUEST_END',
                    'model': 'HTTP_REQUEST',
                    'record_id': request.request_id,
                    'duration': duration,
                    'status_code': response.status_code,
                }
            )
        
        return response


class SecurityMiddleware:
    """
    Middleware to monitor and log security-related events.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.failed_login_attempts = {}
        self.request_counts = {}
    
    def __call__(self, request):
        client_ip = get_client_ip(request)
        current_time = timezone.now()
        
        # Track request frequency for rate limiting
        self._track_request_frequency(client_ip, current_time)
        
        # Check for suspicious activity
        self._check_suspicious_activity(request, client_ip, current_time)
        
        response = self.get_response(request)
        
        # Log security events based on response
        self._log_security_events(request, response, client_ip)
        
        return response
    
    def _track_request_frequency(self, client_ip, current_time):
        """Track request frequency for rate limiting."""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # Remove requests older than 1 minute
        self.request_counts[client_ip] = [
            time for time in self.request_counts[client_ip]
            if (current_time - time).total_seconds() < 60
        ]
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
        
        # Check rate limit
        rate_limit = getattr(settings, 'SECURITY_LOG_RATE_LIMIT_PER_MINUTE', 100)
        if len(self.request_counts[client_ip]) > rate_limit:
            SecurityEvent.objects.create(
                event_type='RATE_LIMIT_EXCEEDED',
                severity='MEDIUM',
                description=f'Rate limit exceeded for IP {client_ip}',
                user_ip=client_ip,
                metadata={'request_count': len(self.request_counts[client_ip])}
            )
    
    def _check_suspicious_activity(self, request, client_ip, current_time):
        """Check for suspicious activity patterns."""
        # Check for failed login attempts
        if request.path.endswith('/login/') and request.method == 'POST':
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                if client_ip not in self.failed_login_attempts:
                    self.failed_login_attempts[client_ip] = []
                
                # Remove attempts older than 15 minutes
                self.failed_login_attempts[client_ip] = [
                    time for time in self.failed_login_attempts[client_ip]
                    if (current_time - time).total_seconds() < 900
                ]
                
                self.failed_login_attempts[client_ip].append(current_time)
                
                # Check threshold
                threshold = getattr(settings, 'SECURITY_LOG_FAILED_LOGIN_ATTEMPTS', 5)
                if len(self.failed_login_attempts[client_ip]) >= threshold:
                    SecurityEvent.objects.create(
                        event_type='LOGIN_FAILURE',
                        severity='HIGH',
                        description=f'Multiple failed login attempts from IP {client_ip}',
                        user_ip=client_ip,
                        metadata={'failed_attempts': len(self.failed_login_attempts[client_ip])}
                    )
    
    def _log_security_events(self, request, response, client_ip):
        """Log security events based on response status."""
        # Log 403 Forbidden responses
        if response.status_code == 403:
            SecurityEvent.objects.create(
                event_type='UNAUTHORIZED_ACCESS',
                severity='MEDIUM',
                description=f'Unauthorized access attempt to {request.path}',
                user=getattr(request, 'user', None),
                user_ip=client_ip,
                metadata={'path': request.path, 'method': request.method}
            )
        
        # Log 404 responses for potential scanning
        elif response.status_code == 404:
            # Check if this looks like a scanning attempt
            suspicious_paths = ['/admin', '/wp-admin', '/phpmyadmin', '/.env', '/config']
            if any(path in request.path for path in suspicious_paths):
                SecurityEvent.objects.create(
                    event_type='SUSPICIOUS_ACTIVITY',
                    severity='LOW',
                    description=f'Potential scanning attempt: {request.path}',
                    user_ip=client_ip,
                    metadata={'path': request.path, 'method': request.method}
                ) 