#!/usr/bin/env python3
"""
WaPrep Tuition Portal - Security Audit Script

This script performs comprehensive security audits on the application,
including endpoint security, authentication flows, and vulnerability scanning.
"""

import os
import sys
import subprocess
import json
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta
import django
from django.conf import settings
from django.core.management import execute_from_command_line

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuition.settings')
django.setup()

class SecurityAuditor:
    def __init__(self):
        self.project_root = project_root
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'vulnerabilities': [],
            'recommendations': []
        }
    
    def run_all_checks(self):
        """Run all security checks"""
        print("🔒 Starting Security Audit...")
        print("=" * 50)
        
        self.check_django_security()
        self.check_authentication_protection()
        self.check_http_methods()
        self.check_input_validation()
        self.check_rate_limiting()
        self.check_https_configuration()
        self.check_error_handling()
        self.check_password_policies()
        self.check_session_management()
        self.check_authorization()
        self.check_logging_monitoring()
        self.check_dependencies()
        self.check_environment_security()
        
        self.generate_report()
    
    def check_django_security(self):
        """Check Django security settings"""
        print("🔍 Checking Django Security Settings...")
        
        try:
            # Run Django security check
            result = subprocess.run([
                'python', 'manage.py', 'check', '--deploy'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                self.results['checks']['django_security'] = {
                    'status': 'PASS',
                    'message': 'Django security check passed'
                }
            else:
                self.results['checks']['django_security'] = {
                    'status': 'FAIL',
                    'message': result.stdout + result.stderr
                }
                self.results['vulnerabilities'].append({
                    'type': 'Django Security',
                    'severity': 'HIGH',
                    'description': 'Django security check failed'
                })
        except Exception as e:
            self.results['checks']['django_security'] = {
                'status': 'ERROR',
                'message': str(e)
            }
    
    def check_authentication_protection(self):
        """Check authentication protection on endpoints"""
        print("🔐 Checking Authentication Protection...")
        
        views_file = self.project_root / 'tuition' / 'views.py'
        if not views_file.exists():
            return
        
        with open(views_file, 'r') as f:
            content = f.read()
        
        # Check for @login_required decorators
        login_required_count = len(re.findall(r'@login_required', content))
        admin_required_count = len(re.findall(r'@admin_required', content))
        payer_required_count = len(re.findall(r'@payer_required', content))
        
        # Get all view functions
        view_functions = re.findall(r'def (\w+)\(request', content)
        
        # Check for potentially unprotected views
        unprotected_views = []
        for func in view_functions:
            if not any(decorator in content for decorator in [
                '@login_required', '@admin_required', '@payer_required'
            ]):
                unprotected_views.append(func)
        
        self.results['checks']['authentication_protection'] = {
            'status': 'INFO',
            'login_required_count': login_required_count,
            'admin_required_count': admin_required_count,
            'payer_required_count': payer_required_count,
            'unprotected_views': unprotected_views
        }
        
        if unprotected_views:
            self.results['recommendations'].append({
                'type': 'Authentication',
                'priority': 'HIGH',
                'description': f'Review unprotected views: {", ".join(unprotected_views)}'
            })
    
    def check_http_methods(self):
        """Check HTTP method restrictions"""
        print("🌐 Checking HTTP Method Restrictions...")
        
        views_file = self.project_root / 'tuition' / 'views.py'
        if not views_file.exists():
            return
        
        with open(views_file, 'r') as f:
            content = f.read()
        
        # Check for @require_POST decorators
        require_post_count = len(re.findall(r'@require_POST', content))
        require_http_methods_count = len(re.findall(r'@require_http_methods', content))
        
        self.results['checks']['http_methods'] = {
            'status': 'INFO',
            'require_post_count': require_post_count,
            'require_http_methods_count': require_http_methods_count
        }
        
        if require_post_count < 5:  # Expected minimum for sensitive operations
            self.results['recommendations'].append({
                'type': 'HTTP Methods',
                'priority': 'MEDIUM',
                'description': 'Consider adding @require_POST to sensitive operations'
            })
    
    def check_input_validation(self):
        """Check input validation"""
        print("✅ Checking Input Validation...")
        
        forms_file = self.project_root / 'tuition' / 'forms.py'
        if not forms_file.exists():
            return
        
        with open(forms_file, 'r') as f:
            content = f.read()
        
        # Check for form validation
        form_classes = re.findall(r'class (\w+)\(forms\.', content)
        
        self.results['checks']['input_validation'] = {
            'status': 'INFO',
            'form_classes': form_classes,
            'form_count': len(form_classes)
        }
        
        if len(form_classes) < 3:
            self.results['recommendations'].append({
                'type': 'Input Validation',
                'priority': 'MEDIUM',
                'description': 'Consider adding more form validation'
            })
    
    def check_rate_limiting(self):
        """Check rate limiting implementation"""
        print("🚦 Checking Rate Limiting...")
        
        middleware_file = self.project_root / 'tuition' / 'audit_middleware.py'
        if not middleware_file.exists():
            return
        
        with open(middleware_file, 'r') as f:
            content = f.read()
        
        # Check for rate limiting logic
        rate_limit_patterns = [
            'rate_limit',
            'request_counts',
            'SECURITY_LOG_RATE_LIMIT_PER_MINUTE'
        ]
        
        rate_limiting_found = any(pattern in content for pattern in rate_limit_patterns)
        
        self.results['checks']['rate_limiting'] = {
            'status': 'PASS' if rate_limiting_found else 'FAIL',
            'rate_limiting_implemented': rate_limiting_found
        }
        
        if not rate_limiting_found:
            self.results['vulnerabilities'].append({
                'type': 'Rate Limiting',
                'severity': 'MEDIUM',
                'description': 'Rate limiting not implemented'
            })
    
    def check_https_configuration(self):
        """Check HTTPS configuration"""
        print("🔒 Checking HTTPS Configuration...")
        
        settings_file = self.project_root / 'tuition' / 'settings_production.py'
        if not settings_file.exists():
            return
        
        with open(settings_file, 'r') as f:
            content = f.read()
        
        https_settings = {
            'SECURE_SSL_REDIRECT': 'SECURE_SSL_REDIRECT' in content,
            'SECURE_HSTS_SECONDS': 'SECURE_HSTS_SECONDS' in content,
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': 'SECURE_HSTS_INCLUDE_SUBDOMAINS' in content,
            'SECURE_HSTS_PRELOAD': 'SECURE_HSTS_PRELOAD' in content
        }
        
        all_https_enabled = all(https_settings.values())
        
        self.results['checks']['https_configuration'] = {
            'status': 'PASS' if all_https_enabled else 'FAIL',
            'settings': https_settings
        }
        
        if not all_https_enabled:
            self.results['vulnerabilities'].append({
                'type': 'HTTPS Configuration',
                'severity': 'HIGH',
                'description': 'HTTPS settings not fully configured'
            })
    
    def check_error_handling(self):
        """Check error handling"""
        print("⚠️ Checking Error Handling...")
        
        # Check DEBUG setting
        debug_enabled = getattr(settings, 'DEBUG', False)
        
        self.results['checks']['error_handling'] = {
            'status': 'FAIL' if debug_enabled else 'PASS',
            'debug_enabled': debug_enabled
        }
        
        if debug_enabled:
            self.results['vulnerabilities'].append({
                'type': 'Error Handling',
                'severity': 'HIGH',
                'description': 'DEBUG mode is enabled in production'
            })
    
    def check_password_policies(self):
        """Check password policies"""
        print("🔑 Checking Password Policies...")
        
        # Check password validators
        password_validators = getattr(settings, 'AUTH_PASSWORD_VALIDATORS', [])
        
        expected_validators = [
            'UserAttributeSimilarityValidator',
            'MinimumLengthValidator',
            'CommonPasswordValidator',
            'NumericPasswordValidator'
        ]
        
        validator_names = [validator['NAME'].split('.')[-1] for validator in password_validators]
        all_validators_present = all(name in validator_names for name in expected_validators)
        
        self.results['checks']['password_policies'] = {
            'status': 'PASS' if all_validators_present else 'FAIL',
            'validators_present': validator_names,
            'expected_validators': expected_validators
        }
        
        if not all_validators_present:
            self.results['vulnerabilities'].append({
                'type': 'Password Policy',
                'severity': 'MEDIUM',
                'description': 'Password validators not fully configured'
            })
    
    def check_session_management(self):
        """Check session management"""
        print("🕐 Checking Session Management...")
        
        session_settings = {
            'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', False),
            'SESSION_COOKIE_HTTPONLY': getattr(settings, 'SESSION_COOKIE_HTTPONLY', True),
            'SESSION_COOKIE_SAMESITE': getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax'),
            'SESSION_EXPIRE_AT_BROWSER_CLOSE': getattr(settings, 'SESSION_EXPIRE_AT_BROWSER_CLOSE', False)
        }
        
        secure_session = session_settings['SESSION_COOKIE_SECURE'] and session_settings['SESSION_COOKIE_HTTPONLY']
        
        self.results['checks']['session_management'] = {
            'status': 'PASS' if secure_session else 'FAIL',
            'settings': session_settings
        }
        
        if not secure_session:
            self.results['vulnerabilities'].append({
                'type': 'Session Management',
                'severity': 'MEDIUM',
                'description': 'Session security settings not fully configured'
            })
    
    def check_authorization(self):
        """Check authorization implementation"""
        print("🔐 Checking Authorization...")
        
        decorators_file = self.project_root / 'tuition' / 'decorators.py'
        if not decorators_file.exists():
            return
        
        with open(decorators_file, 'r') as f:
            content = f.read()
        
        # Check for authorization decorators
        admin_required = '@admin_required' in content
        payer_required = '@payer_required' in content
        
        self.results['checks']['authorization'] = {
            'status': 'PASS' if admin_required and payer_required else 'FAIL',
            'admin_required_decorator': admin_required,
            'payer_required_decorator': payer_required
        }
        
        if not (admin_required and payer_required):
            self.results['vulnerabilities'].append({
                'type': 'Authorization',
                'severity': 'HIGH',
                'description': 'Authorization decorators not fully implemented'
            })
    
    def check_logging_monitoring(self):
        """Check logging and monitoring"""
        print("📊 Checking Logging and Monitoring...")
        
        # Check for audit logging
        audit_enabled = getattr(settings, 'AUDIT_LOG_ENABLED', False)
        security_enabled = getattr(settings, 'SECURITY_LOG_ENABLED', False)
        
        self.results['checks']['logging_monitoring'] = {
            'status': 'PASS' if audit_enabled and security_enabled else 'FAIL',
            'audit_logging_enabled': audit_enabled,
            'security_logging_enabled': security_enabled
        }
        
        if not (audit_enabled and security_enabled):
            self.results['vulnerabilities'].append({
                'type': 'Logging and Monitoring',
                'severity': 'MEDIUM',
                'description': 'Audit or security logging not enabled'
            })
    
    def check_dependencies(self):
        """Check dependencies for vulnerabilities"""
        print("📦 Checking Dependencies...")
        
        try:
            # Try to run safety check
            result = subprocess.run([
                'safety', 'check', '--json'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                self.results['checks']['dependencies'] = {
                    'status': 'PASS' if not vulnerabilities else 'FAIL',
                    'vulnerabilities': vulnerabilities
                }
                
                if vulnerabilities:
                    self.results['vulnerabilities'].extend([
                        {
                            'type': 'Dependency',
                            'severity': 'HIGH',
                            'description': f'Vulnerable package: {vuln.get("package", "Unknown")}'
                        }
                        for vuln in vulnerabilities
                    ])
            else:
                self.results['checks']['dependencies'] = {
                    'status': 'ERROR',
                    'message': 'Safety check failed'
                }
        except Exception as e:
            self.results['checks']['dependencies'] = {
                'status': 'ERROR',
                'message': str(e)
            }
    
    def check_environment_security(self):
        """Check environment security"""
        print("🔧 Checking Environment Security...")
        
        # Check for .env file
        env_file = self.project_root / '.env'
        env_exists = env_file.exists()
        
        # Check for hardcoded secrets in settings
        settings_file = self.project_root / 'tuition' / 'settings.py'
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                content = f.read()
            
            # Look for potential hardcoded secrets
            hardcoded_patterns = [
                r'SECRET_KEY\s*=\s*[\'"][^\'"]+[\'"]',
                r'password\s*=\s*[\'"][^\'"]+[\'"]',
                r'api_key\s*=\s*[\'"][^\'"]+[\'"]'
            ]
            
            hardcoded_secrets = []
            for pattern in hardcoded_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    hardcoded_secrets.append(pattern)
        
        self.results['checks']['environment_security'] = {
            'status': 'PASS' if env_exists and not hardcoded_secrets else 'FAIL',
            'env_file_exists': env_exists,
            'hardcoded_secrets_found': bool(hardcoded_secrets)
        }
        
        if hardcoded_secrets:
            self.results['vulnerabilities'].append({
                'type': 'Environment Security',
                'severity': 'CRITICAL',
                'description': 'Hardcoded secrets found in settings'
            })
    
    def generate_report(self):
        """Generate security audit report"""
        print("\n" + "=" * 50)
        print("📋 SECURITY AUDIT REPORT")
        print("=" * 50)
        
        # Count results
        total_checks = len(self.results['checks'])
        passed_checks = sum(1 for check in self.results['checks'].values() if check.get('status') == 'PASS')
        failed_checks = sum(1 for check in self.results['checks'].values() if check.get('status') == 'FAIL')
        error_checks = sum(1 for check in self.results['checks'].values() if check.get('status') == 'ERROR')
        
        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {failed_checks}")
        print(f"⚠️ Errors: {error_checks}")
        print(f"🚨 Vulnerabilities Found: {len(self.results['vulnerabilities'])}")
        
        # Show vulnerabilities
        if self.results['vulnerabilities']:
            print("\n🚨 VULNERABILITIES:")
            for i, vuln in enumerate(self.results['vulnerabilities'], 1):
                print(f"{i}. [{vuln['severity']}] {vuln['type']}: {vuln['description']}")
        
        # Show recommendations
        if self.results['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.results['recommendations'], 1):
                print(f"{i}. [{rec['priority']}] {rec['type']}: {rec['description']}")
        
        # Save report
        report_file = self.project_root / 'security_audit_report.json'
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Summary
        if len(self.results['vulnerabilities']) == 0:
            print("\n🎉 Security audit completed successfully! No critical vulnerabilities found.")
        else:
            print(f"\n⚠️ Security audit completed. {len(self.results['vulnerabilities'])} vulnerabilities found.")
            print("Please review and address the identified issues.")

def main():
    """Main function"""
    auditor = SecurityAuditor()
    auditor.run_all_checks()

if __name__ == '__main__':
    main() 