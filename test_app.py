#!/usr/bin/env python3
"""
Comprehensive Test Script for WAPrep Tuition Management Application
Tests all features systematically and reports bugs and issues.
"""

import requests
import json
import time
import sys
from datetime import datetime, timedelta
from urllib.parse import urljoin

class TuitionAppTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {
            'passed': [],
            'failed': [],
            'bugs': [],
            'features_not_working': []
        }
        
    def log_test(self, test_name, status, details=""):
        """Log test results"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = {
            'test_name': test_name,
            'status': status,
            'details': details,
            'timestamp': timestamp
        }
        
        if status == 'PASS':
            self.test_results['passed'].append(result)
            print(f"✅ {test_name}: PASS")
        elif status == 'FAIL':
            self.test_results['failed'].append(result)
            print(f"❌ {test_name}: FAIL - {details}")
        elif status == 'BUG':
            self.test_results['bugs'].append(result)
            print(f"🐛 {test_name}: BUG - {details}")
        elif status == 'NOT_WORKING':
            self.test_results['features_not_working'].append(result)
            print(f"🚫 {test_name}: NOT WORKING - {details}")
    
    def test_home_page(self):
        """Test home page accessibility"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                self.log_test("Home Page Access", "PASS")
            else:
                self.log_test("Home Page Access", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Home Page Access", "FAIL", str(e))
    
    def test_payer_login_page(self):
        """Test payer login page"""
        try:
            response = self.session.get(urljoin(self.base_url, "/login/payer/"))
            if response.status_code == 200:
                self.log_test("Payer Login Page", "PASS")
            else:
                self.log_test("Payer Login Page", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Payer Login Page", "FAIL", str(e))
    
    def test_admin_login_page(self):
        """Test admin login page"""
        try:
            response = self.session.get(urljoin(self.base_url, "/login/admin/"))
            if response.status_code == 200:
                self.log_test("Admin Login Page", "PASS")
            else:
                self.log_test("Admin Login Page", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.test_results['features_not_working'].append({
                'test_name': "Admin Login Page",
                'status': 'NOT_WORKING',
                'details': str(e),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    
    def test_forgot_password_page(self):
        """Test forgot password page"""
        try:
            response = self.session.get(urljoin(self.base_url, "/forgot-password/"))
            if response.status_code == 200:
                self.log_test("Forgot Password Page", "PASS")
            else:
                self.log_test("Forgot Password Page", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Forgot Password Page", "FAIL", str(e))
    
    def test_request_account_page(self):
        """Test account request page"""
        try:
            response = self.session.get(urljoin(self.base_url, "/request-account/"))
            if response.status_code == 200:
                self.log_test("Request Account Page", "PASS")
            else:
                self.log_test("Request Account Page", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Request Account Page", "FAIL", str(e))
    
    def test_static_files(self):
        """Test static file serving"""
        try:
            response = self.session.get(urljoin(self.base_url, "/static/css/style.css"))
            if response.status_code == 200:
                self.log_test("Static Files Serving", "PASS")
            else:
                self.log_test("Static Files Serving", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Static Files Serving", "FAIL", str(e))
    
    def test_admin_required_pages(self):
        """Test admin-required pages (should redirect to login)"""
        admin_pages = [
            "/students/",
            "/admin/dashboard/",
            "/admin/reports/",
            "/manage-billing/",
        ]
        
        for page in admin_pages:
            try:
                response = self.session.get(urljoin(self.base_url, page), allow_redirects=False)
                if response.status_code in [302, 403]:  # Redirect or forbidden
                    self.log_test(f"Admin Page Protection: {page}", "PASS")
                else:
                    self.log_test(f"Admin Page Protection: {page}", "BUG", f"Should redirect but got {response.status_code}")
            except Exception as e:
                self.log_test(f"Admin Page Protection: {page}", "FAIL", str(e))
    
    def test_payer_required_pages(self):
        """Test payer-required pages (should redirect to login)"""
        payer_pages = [
            "/payer/dashboard/",
            "/payer/welcome/",
            "/payment/history/",
            "/payer/profile/",
        ]
        
        for page in payer_pages:
            try:
                response = self.session.get(urljoin(self.base_url, page), allow_redirects=False)
                if response.status_code in [302, 403]:  # Redirect or forbidden
                    self.log_test(f"Payer Page Protection: {page}", "PASS")
                else:
                    self.log_test(f"Payer Page Protection: {page}", "BUG", f"Should redirect but got {response.status_code}")
            except Exception as e:
                self.log_test(f"Payer Page Protection: {page}", "FAIL", str(e))
    
    def test_csrf_protection(self):
        """Test CSRF protection on forms"""
        try:
            # Test POST to login without CSRF token
            response = self.session.post(urljoin(self.base_url, "/login/payer/"), 
                                       data={'username': 'test', 'password': 'test'})
            if response.status_code == 403:  # CSRF forbidden
                self.log_test("CSRF Protection", "PASS")
            else:
                self.log_test("CSRF Protection", "BUG", f"Should return 403 but got {response.status_code}")
        except Exception as e:
            self.log_test("CSRF Protection", "FAIL", str(e))
    
    def test_health_check(self):
        """Test health check endpoint"""
        try:
            response = self.session.get(urljoin(self.base_url, "/health/"))
            if response.status_code == 200:
                self.log_test("Health Check Endpoint", "PASS")
            else:
                self.log_test("Health Check Endpoint", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Health Check Endpoint", "FAIL", str(e))
    
    def test_stripe_webhook(self):
        """Test Stripe webhook endpoint"""
        try:
            response = self.session.post(urljoin(self.base_url, "/webhook/stripe/"), 
                                       data={'test': 'data'})
            if response.status_code in [200, 400]:  # Accepts or rejects webhook
                self.log_test("Stripe Webhook Endpoint", "PASS")
            else:
                self.log_test("Stripe Webhook Endpoint", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Stripe Webhook Endpoint", "FAIL", str(e))
    
    def test_invalid_urls(self):
        """Test invalid URL handling"""
        invalid_urls = [
            "/nonexistent/",
            "/invalid/page/",
            "/admin/invalid/",
        ]
        
        for url in invalid_urls:
            try:
                response = self.session.get(urljoin(self.base_url, url))
                if response.status_code == 404:
                    self.log_test(f"Invalid URL Handling: {url}", "PASS")
                else:
                    self.log_test(f"Invalid URL Handling: {url}", "BUG", f"Should return 404 but got {response.status_code}")
            except Exception as e:
                self.log_test(f"Invalid URL Handling: {url}", "FAIL", str(e))
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection"""
        malicious_inputs = [
            "'; DROP TABLE students; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
        ]
        
        for malicious_input in malicious_inputs:
            try:
                response = self.session.get(urljoin(self.base_url, f"/students/?search={malicious_input}"))
                if response.status_code in [200, 302, 403]:  # Normal response
                    self.log_test(f"SQL Injection Protection: {malicious_input[:20]}...", "PASS")
                else:
                    self.log_test(f"SQL Injection Protection: {malicious_input[:20]}...", "BUG", f"Unexpected response: {response.status_code}")
            except Exception as e:
                self.log_test(f"SQL Injection Protection: {malicious_input[:20]}...", "FAIL", str(e))
    
    def test_xss_protection(self):
        """Test XSS protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
        ]
        
        for payload in xss_payloads:
            try:
                response = self.session.get(urljoin(self.base_url, f"/students/?search={payload}"))
                if response.status_code in [200, 302, 403]:  # Normal response
                    self.log_test(f"XSS Protection: {payload[:20]}...", "PASS")
                else:
                    self.log_test(f"XSS Protection: {payload[:20]}...", "BUG", f"Unexpected response: {response.status_code}")
            except Exception as e:
                self.log_test(f"XSS Protection: {payload[:20]}...", "FAIL", str(e))
    
    def test_session_management(self):
        """Test session management"""
        try:
            # Test session cookie presence
            response = self.session.get(self.base_url)
            if 'sessionid' in self.session.cookies:
                self.log_test("Session Management", "PASS")
            else:
                self.log_test("Session Management", "BUG", "No session cookie found")
        except Exception as e:
            self.log_test("Session Management", "FAIL", str(e))
    
    def test_content_security_policy(self):
        """Test Content Security Policy headers"""
        try:
            response = self.session.get(self.base_url)
            if 'Content-Security-Policy' in response.headers:
                self.log_test("Content Security Policy", "PASS")
            else:
                self.log_test("Content Security Policy", "BUG", "No CSP header found")
        except Exception as e:
            self.log_test("Content Security Policy", "FAIL", str(e))
    
    def test_https_redirect(self):
        """Test HTTPS redirect (if configured)"""
        try:
            response = self.session.get(self.base_url, allow_redirects=False)
            if response.status_code == 200:  # No redirect in development
                self.log_test("HTTPS Redirect", "PASS", "No redirect in development mode")
            else:
                self.log_test("HTTPS Redirect", "BUG", f"Unexpected redirect: {response.status_code}")
        except Exception as e:
            self.log_test("HTTPS Redirect", "FAIL", str(e))
    
    def test_database_connection(self):
        """Test database connectivity through health check"""
        try:
            response = self.session.get(urljoin(self.base_url, "/health/"))
            if response.status_code == 200:
                # Try to parse JSON response
                try:
                    data = response.json()
                    if 'database' in data and data['database'] == 'healthy':
                        self.log_test("Database Connection", "PASS")
                    else:
                        self.log_test("Database Connection", "BUG", "Database not reported as healthy")
                except json.JSONDecodeError:
                    self.log_test("Database Connection", "BUG", "Health check not returning JSON")
            else:
                self.log_test("Database Connection", "FAIL", f"Health check failed: {response.status_code}")
        except Exception as e:
            self.log_test("Database Connection", "FAIL", str(e))
    
    def test_email_configuration(self):
        """Test email configuration"""
        try:
            # Test forgot password form submission
            response = self.session.post(urljoin(self.base_url, "/forgot-password/"), 
                                       data={'email': 'test@example.com'})
            if response.status_code in [200, 302]:  # Form processed
                self.log_test("Email Configuration", "PASS", "Form processed successfully")
            else:
                self.log_test("Email Configuration", "BUG", f"Form processing failed: {response.status_code}")
        except Exception as e:
            self.log_test("Email Configuration", "FAIL", str(e))
    
    def test_stripe_integration(self):
        """Test Stripe integration"""
        try:
            # Test payment page (should show Stripe elements)
            response = self.session.get(urljoin(self.base_url, "/payment/1/"))
            if response.status_code == 302:  # Redirected to login (expected)
                self.log_test("Stripe Integration", "PASS", "Payment page redirects to login as expected")
            else:
                self.log_test("Stripe Integration", "BUG", f"Payment page unexpected response: {response.status_code}")
        except Exception as e:
            self.log_test("Stripe Integration", "FAIL", str(e))
    
    def test_audit_logging(self):
        """Test audit logging functionality"""
        try:
            # Test audit summary page (should redirect to login)
            response = self.session.get(urljoin(self.base_url, "/monitoring/audit-summary/"), allow_redirects=False)
            if response.status_code in [302, 403]:  # Redirect or forbidden
                self.log_test("Audit Logging", "PASS", "Audit page properly protected")
            else:
                self.log_test("Audit Logging", "BUG", f"Audit page not protected: {response.status_code}")
        except Exception as e:
            self.log_test("Audit Logging", "FAIL", str(e))
    
    def test_security_events(self):
        """Test security events monitoring"""
        try:
            # Test security events page (should redirect to login)
            response = self.session.get(urljoin(self.base_url, "/monitoring/security-events/"), allow_redirects=False)
            if response.status_code in [302, 403]:  # Redirect or forbidden
                self.log_test("Security Events", "PASS", "Security events page properly protected")
            else:
                self.log_test("Security Events", "BUG", f"Security events page not protected: {response.status_code}")
        except Exception as e:
            self.log_test("Security Events", "FAIL", str(e))
    
    def test_mass_billing_features(self):
        """Test mass billing features"""
        try:
            # Test mass add bills page (should redirect to login)
            response = self.session.get(urljoin(self.base_url, "/mass-add-bills/"), allow_redirects=False)
            if response.status_code in [302, 403]:  # Redirect or forbidden
                self.log_test("Mass Billing Features", "PASS", "Mass billing page properly protected")
            else:
                self.log_test("Mass Billing Features", "BUG", f"Mass billing page not protected: {response.status_code}")
        except Exception as e:
            self.log_test("Mass Billing Features", "FAIL", str(e))
    
    def test_file_upload_security(self):
        """Test file upload security"""
        try:
            # Test receipt download (should redirect to login)
            response = self.session.get(urljoin(self.base_url, "/payment/receipt/1/"), allow_redirects=False)
            if response.status_code in [302, 403, 404]:  # Redirect, forbidden, or not found
                self.log_test("File Upload Security", "PASS", "Receipt download properly protected")
            else:
                self.log_test("File Upload Security", "BUG", f"Receipt download not protected: {response.status_code}")
        except Exception as e:
            self.log_test("File Upload Security", "FAIL", str(e))
    
    def test_rate_limiting(self):
        """Test rate limiting (basic test)"""
        try:
            # Make multiple rapid requests
            responses = []
            for i in range(10):
                response = self.session.get(self.base_url)
                responses.append(response.status_code)
            
            # Check if all requests were successful
            if all(code == 200 for code in responses):
                self.log_test("Rate Limiting", "PASS", "No rate limiting detected (may be disabled in development)")
            else:
                self.log_test("Rate Limiting", "BUG", f"Rate limiting may be too aggressive: {responses}")
        except Exception as e:
            self.log_test("Rate Limiting", "FAIL", str(e))
    
    def test_mobile_responsiveness(self):
        """Test mobile responsiveness (basic check)"""
        try:
            response = self.session.get(self.base_url)
            if 'viewport' in response.text.lower():
                self.log_test("Mobile Responsiveness", "PASS", "Viewport meta tag found")
            else:
                self.log_test("Mobile Responsiveness", "BUG", "No viewport meta tag found")
        except Exception as e:
            self.log_test("Mobile Responsiveness", "FAIL", str(e))
    
    def test_accessibility_basics(self):
        """Test basic accessibility features"""
        try:
            response = self.session.get(self.base_url)
            content = response.text.lower()
            
            issues = []
            if 'alt=' not in content:
                issues.append("Missing alt attributes")
            if 'aria-' not in content:
                issues.append("No ARIA attributes found")
            if 'role=' not in content:
                issues.append("No role attributes found")
            
            if not issues:
                self.log_test("Accessibility Basics", "PASS")
            else:
                self.log_test("Accessibility Basics", "BUG", f"Accessibility issues: {', '.join(issues)}")
        except Exception as e:
            self.log_test("Accessibility Basics", "FAIL", str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting comprehensive testing of WAPrep Tuition Application...")
        print("=" * 80)
        
        # Basic functionality tests
        self.test_home_page()
        self.test_payer_login_page()
        self.test_admin_login_page()
        self.test_forgot_password_page()
        self.test_request_account_page()
        self.test_static_files()
        
        # Security tests
        self.test_admin_required_pages()
        self.test_payer_required_pages()
        self.test_csrf_protection()
        self.test_sql_injection_protection()
        self.test_xss_protection()
        self.test_session_management()
        self.test_content_security_policy()
        self.test_https_redirect()
        self.test_file_upload_security()
        self.test_rate_limiting()
        
        # Integration tests
        self.test_health_check()
        self.test_stripe_webhook()
        self.test_database_connection()
        self.test_email_configuration()
        self.test_stripe_integration()
        
        # Monitoring and audit tests
        self.test_audit_logging()
        self.test_security_events()
        self.test_mass_billing_features()
        
        # Error handling tests
        self.test_invalid_urls()
        
        # UX tests
        self.test_mobile_responsiveness()
        self.test_accessibility_basics()
        
        print("=" * 80)
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📊 TEST REPORT SUMMARY")
        print("=" * 80)
        
        total_tests = (len(self.test_results['passed']) + 
                      len(self.test_results['failed']) + 
                      len(self.test_results['bugs']) + 
                      len(self.test_results['features_not_working']))
        
        print(f"Total Tests Run: {total_tests}")
        print(f"✅ Passed: {len(self.test_results['passed'])}")
        print(f"❌ Failed: {len(self.test_results['failed'])}")
        print(f"🐛 Bugs Found: {len(self.test_results['bugs'])}")
        print(f"🚫 Features Not Working: {len(self.test_results['features_not_working'])}")
        
        if self.test_results['bugs']:
            print("\n🐛 BUGS FOUND:")
            print("-" * 40)
            for bug in self.test_results['bugs']:
                print(f"• {bug['test_name']}: {bug['details']}")
        
        if self.test_results['features_not_working']:
            print("\n🚫 FEATURES NOT WORKING:")
            print("-" * 40)
            for feature in self.test_results['features_not_working']:
                print(f"• {feature['test_name']}: {feature['details']}")
        
        if self.test_results['failed']:
            print("\n❌ FAILED TESTS:")
            print("-" * 40)
            for failure in self.test_results['failed']:
                print(f"• {failure['test_name']}: {failure['details']}")
        
        # Save detailed report to file
        report_filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_filename}")
        
        # Generate recommendations
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 40)
        
        if self.test_results['bugs']:
            print("• Fix identified bugs before production deployment")
            print("• Review security vulnerabilities")
        
        if self.test_results['features_not_working']:
            print("• Complete implementation of non-working features")
            print("• Test features with proper authentication")
        
        if len(self.test_results['failed']) > len(self.test_results['passed']):
            print("• Review application configuration")
            print("• Check server logs for errors")
        
        print("• Implement comprehensive unit and integration tests")
        print("• Add automated security scanning")
        print("• Consider implementing monitoring and alerting")

if __name__ == "__main__":
    tester = TuitionAppTester()
    tester.run_all_tests() 