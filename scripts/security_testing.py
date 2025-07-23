#!/usr/bin/env python3
"""
WaPrep Tuition Portal - Security Testing Script

This script provides practical security tests for common vulnerabilities
including authentication bypass, injection attacks, and authorization testing.
"""

import requests
import json
import time
import random
import string
from urllib.parse import urljoin, urlparse
from datetime import datetime

class SecurityTester:
    def __init__(self, base_url, session=None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'vulnerabilities': [],
            'recommendations': []
        }
    
    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        print("🔐 Testing Authentication Bypass...")
        
        # Test accessing protected endpoints without authentication
        protected_endpoints = [
            '/payer/dashboard/',
            '/admin/dashboard/',
            '/students/',
            '/payment/history/',
            '/payer/profile/'
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = self.session.get(urljoin(self.base_url, endpoint))
                
                if response.status_code == 200:
                    self.results['vulnerabilities'].append({
                        'type': 'Authentication Bypass',
                        'severity': 'CRITICAL',
                        'description': f'Protected endpoint accessible without authentication: {endpoint}',
                        'status_code': response.status_code
                    })
                elif response.status_code == 302:
                    # Redirect to login - expected behavior
                    pass
                else:
                    self.results['tests'][f'auth_bypass_{endpoint}'] = {
                        'status': 'PASS',
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                self.results['tests'][f'auth_bypass_{endpoint}'] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
    
    def test_brute_force_protection(self):
        """Test brute force protection on login endpoints"""
        print("💥 Testing Brute Force Protection...")
        
        login_endpoints = [
            ('/login/payer/', {'username': 'test', 'password': 'wrong'}),
            ('/login/admin/', {'email': 'test@test.com', 'password': 'wrong'})
        ]
        
        for endpoint, data in login_endpoints:
            failed_attempts = 0
            blocked = False
            
            # Try multiple failed login attempts
            for i in range(10):
                try:
                    response = self.session.post(urljoin(self.base_url, endpoint), data=data)
                    
                    if response.status_code == 429:  # Too Many Requests
                        blocked = True
                        break
                    elif response.status_code == 403:  # Forbidden
                        blocked = True
                        break
                    else:
                        failed_attempts += 1
                        
                    time.sleep(0.1)  # Small delay between requests
                    
                except Exception as e:
                    print(f"Error testing {endpoint}: {e}")
                    break
            
            if not blocked and failed_attempts >= 5:
                self.results['vulnerabilities'].append({
                    'type': 'Brute Force Protection',
                    'severity': 'HIGH',
                    'description': f'No brute force protection detected on {endpoint}',
                    'failed_attempts': failed_attempts
                })
            else:
                self.results['tests'][f'brute_force_{endpoint}'] = {
                    'status': 'PASS',
                    'blocked': blocked,
                    'failed_attempts': failed_attempts
                }
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        print("💉 Testing SQL Injection...")
        
        # Common SQL injection payloads
        sql_payloads = [
            "' OR 1=1 --",
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "admin'/*",
            "' OR 1=1#",
            "' OR 1=1/*"
        ]
        
        # Test login endpoints
        login_endpoints = [
            ('/login/payer/', 'username'),
            ('/login/admin/', 'email')
        ]
        
        for endpoint, field in login_endpoints:
            for payload in sql_payloads:
                try:
                    data = {field: payload, 'password': 'test'}
                    response = self.session.post(urljoin(self.base_url, endpoint), data=data)
                    
                    # Check for SQL error messages
                    error_indicators = [
                        'sql', 'mysql', 'postgresql', 'sqlite', 'database',
                        'syntax error', 'mysql_fetch_array', 'ORA-', 'SQLSTATE'
                    ]
                    
                    response_text = response.text.lower()
                    if any(indicator in response_text for indicator in error_indicators):
                        self.results['vulnerabilities'].append({
                            'type': 'SQL Injection',
                            'severity': 'CRITICAL',
                            'description': f'SQL injection vulnerability detected on {endpoint}',
                            'payload': payload,
                            'response_length': len(response.text)
                        })
                        break
                        
                except Exception as e:
                    print(f"Error testing SQL injection on {endpoint}: {e}")
    
    def test_xss_vulnerabilities(self):
        """Test for XSS vulnerabilities"""
        print("🕷️ Testing XSS Vulnerabilities...")
        
        # XSS payloads
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert("XSS")>',
            'javascript:alert("XSS")',
            '<svg onload=alert("XSS")>',
            '"><script>alert("XSS")</script>',
            '"><img src=x onerror=alert("XSS")>'
        ]
        
        # Test form endpoints
        form_endpoints = [
            ('/request-account/', {
                'first_name': '<script>alert("XSS")</script>',
                'last_name': 'Test',
                'email': 'test@test.com',
                'student_names': 'Test Student'
            }),
            ('/payer/edit-profile/', {
                'first_name': '<script>alert("XSS")</script>',
                'last_name': 'Test',
                'email': 'test@test.com'
            })
        ]
        
        for endpoint, data in form_endpoints:
            for payload in xss_payloads:
                try:
                    # Modify data with XSS payload
                    test_data = data.copy()
                    test_data['first_name'] = payload
                    
                    response = self.session.post(urljoin(self.base_url, endpoint), data=test_data)
                    
                    # Check if payload is reflected in response
                    if payload in response.text:
                        self.results['vulnerabilities'].append({
                            'type': 'Cross-Site Scripting (XSS)',
                            'severity': 'HIGH',
                            'description': f'XSS vulnerability detected on {endpoint}',
                            'payload': payload,
                            'reflected': True
                        })
                        break
                        
                except Exception as e:
                    print(f"Error testing XSS on {endpoint}: {e}")
    
    def test_csrf_protection(self):
        """Test CSRF protection"""
        print("🛡️ Testing CSRF Protection...")
        
        # Test endpoints that should have CSRF protection
        csrf_endpoints = [
            '/payment/process/',
            '/students/delete/',
            '/students/update/',
            '/payer/edit-profile/'
        ]
        
        for endpoint in csrf_endpoints:
            try:
                # Try to make a POST request without CSRF token
                response = self.session.post(urljoin(self.base_url, endpoint), data={'test': 'data'})
                
                if response.status_code == 403:
                    # CSRF protection working
                    self.results['tests'][f'csrf_{endpoint}'] = {
                        'status': 'PASS',
                        'csrf_protected': True
                    }
                elif response.status_code == 200:
                    # No CSRF protection
                    self.results['vulnerabilities'].append({
                        'type': 'CSRF Protection',
                        'severity': 'HIGH',
                        'description': f'No CSRF protection detected on {endpoint}',
                        'status_code': response.status_code
                    })
                else:
                    self.results['tests'][f'csrf_{endpoint}'] = {
                        'status': 'INFO',
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                self.results['tests'][f'csrf_{endpoint}'] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
    
    def test_authorization_bypass(self):
        """Test authorization bypass vulnerabilities"""
        print("🔓 Testing Authorization Bypass...")
        
        # This would require authenticated sessions with different user types
        # For now, we'll test the concept
        
        admin_endpoints = [
            '/admin/dashboard/',
            '/admin/reports/',
            '/students/add/',
            '/students/delete/'
        ]
        
        # Test with no authentication (should be blocked)
        for endpoint in admin_endpoints:
            try:
                response = self.session.get(urljoin(self.base_url, endpoint))
                
                if response.status_code == 200:
                    self.results['vulnerabilities'].append({
                        'type': 'Authorization Bypass',
                        'severity': 'CRITICAL',
                        'description': f'Admin endpoint accessible without authentication: {endpoint}',
                        'status_code': response.status_code
                    })
                else:
                    self.results['tests'][f'authz_{endpoint}'] = {
                        'status': 'PASS',
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                self.results['tests'][f'authz_{endpoint}'] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
    
    def test_rate_limiting(self):
        """Test rate limiting implementation"""
        print("🚦 Testing Rate Limiting...")
        
        # Test endpoints that should have rate limiting
        rate_limit_endpoints = [
            '/login/payer/',
            '/login/admin/',
            '/forgot-password/',
            '/request-account/'
        ]
        
        for endpoint in rate_limit_endpoints:
            try:
                # Make multiple rapid requests
                responses = []
                for i in range(20):
                    response = self.session.get(urljoin(self.base_url, endpoint))
                    responses.append(response.status_code)
                    time.sleep(0.05)  # 50ms delay
                
                # Check if rate limiting kicked in
                if 429 in responses:  # Too Many Requests
                    self.results['tests'][f'rate_limit_{endpoint}'] = {
                        'status': 'PASS',
                        'rate_limited': True,
                        'blocked_at_request': responses.index(429) + 1
                    }
                else:
                    self.results['recommendations'].append({
                        'type': 'Rate Limiting',
                        'priority': 'MEDIUM',
                        'description': f'Consider implementing rate limiting on {endpoint}'
                    })
                    
            except Exception as e:
                self.results['tests'][f'rate_limit_{endpoint}'] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
    
    def test_information_disclosure(self):
        """Test for information disclosure"""
        print("📢 Testing Information Disclosure...")
        
        # Test for common information disclosure endpoints
        info_endpoints = [
            '/.env',
            '/config.php',
            '/wp-config.php',
            '/phpinfo.php',
            '/server-status',
            '/robots.txt',
            '/sitemap.xml',
            '/.git/config',
            '/.htaccess'
        ]
        
        for endpoint in info_endpoints:
            try:
                response = self.session.get(urljoin(self.base_url, endpoint))
                
                if response.status_code == 200:
                    # Check for sensitive information
                    sensitive_patterns = [
                        'password', 'secret', 'key', 'token', 'api_key',
                        'database', 'mysql', 'postgresql', 'sqlite'
                    ]
                    
                    response_text = response.text.lower()
                    if any(pattern in response_text for pattern in sensitive_patterns):
                        self.results['vulnerabilities'].append({
                            'type': 'Information Disclosure',
                            'severity': 'HIGH',
                            'description': f'Sensitive information disclosed at {endpoint}',
                            'status_code': response.status_code,
                            'response_length': len(response.text)
                        })
                    else:
                        self.results['tests'][f'info_disclosure_{endpoint}'] = {
                            'status': 'INFO',
                            'accessible': True,
                            'status_code': response.status_code
                        }
                        
            except Exception as e:
                self.results['tests'][f'info_disclosure_{endpoint}'] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🔒 Starting Security Testing...")
        print("=" * 50)
        
        self.test_authentication_bypass()
        self.test_brute_force_protection()
        self.test_sql_injection()
        self.test_xss_vulnerabilities()
        self.test_csrf_protection()
        self.test_authorization_bypass()
        self.test_rate_limiting()
        self.test_information_disclosure()
        
        self.generate_report()
    
    def generate_report(self):
        """Generate security testing report"""
        print("\n" + "=" * 50)
        print("📋 SECURITY TESTING REPORT")
        print("=" * 50)
        
        # Count results
        total_tests = len(self.results['tests'])
        passed_tests = sum(1 for test in self.results['tests'].values() if test.get('status') == 'PASS')
        failed_tests = sum(1 for test in self.results['tests'].values() if test.get('status') == 'FAIL')
        error_tests = sum(1 for test in self.results['tests'].values() if test.get('status') == 'ERROR')
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Errors: {error_tests}")
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
        report_file = f'security_testing_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Summary
        if len(self.results['vulnerabilities']) == 0:
            print("\n🎉 Security testing completed successfully! No vulnerabilities found.")
        else:
            print(f"\n⚠️ Security testing completed. {len(self.results['vulnerabilities'])} vulnerabilities found.")
            print("Please review and address the identified issues.")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Security Testing for WaPrep Tuition Portal')
    parser.add_argument('--url', required=True, help='Base URL of the application')
    parser.add_argument('--session', help='Session cookie for authenticated testing')
    
    args = parser.parse_args()
    
    # Create session with cookie if provided
    session = requests.Session()
    if args.session:
        session.cookies.set('sessionid', args.session)
    
    tester = SecurityTester(args.url, session)
    tester.run_all_tests()

if __name__ == '__main__':
    main() 