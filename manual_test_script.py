#!/usr/bin/env python3
"""
Manual Testing Script for WAPrep Tuition Management Application
Tests authenticated features and specific functionality.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

class ManualTester:
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
    
    def test_payer_login_flow(self):
        """Test payer login flow with invalid credentials"""
        try:
            # Test login with invalid credentials
            login_data = {
                'username': 'invalid_user',
                'password': 'invalid_password'
            }
            response = self.session.post(urljoin(self.base_url, "/login/payer/"), data=login_data)
            
            if response.status_code == 200:
                # Check if error message is displayed
                if 'Invalid User ID or password' in response.text:
                    self.log_test("Payer Login - Invalid Credentials", "PASS")
                else:
                    self.log_test("Payer Login - Invalid Credentials", "BUG", "No error message displayed")
            else:
                self.log_test("Payer Login - Invalid Credentials", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Payer Login - Invalid Credentials", "FAIL", str(e))
    
    def test_admin_login_flow(self):
        """Test admin login flow with invalid credentials"""
        try:
            # Test login with invalid credentials
            login_data = {
                'email': 'invalid@example.com',
                'password': 'invalid_password'
            }
            response = self.session.post(urljoin(self.base_url, "/login/admin/"), data=login_data)
            
            if response.status_code == 200:
                # Check if error message is displayed
                if 'Invalid email or password' in response.text:
                    self.log_test("Admin Login - Invalid Credentials", "PASS")
                else:
                    self.log_test("Admin Login - Invalid Credentials", "BUG", "No error message displayed")
            else:
                self.log_test("Admin Login - Invalid Credentials", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Admin Login - Invalid Credentials", "FAIL", str(e))
    
    def test_forgot_password_flow(self):
        """Test forgot password flow"""
        try:
            # Test forgot password form
            forgot_data = {
                'email': 'test@example.com'
            }
            response = self.session.post(urljoin(self.base_url, "/forgot-password/"), data=forgot_data)
            
            if response.status_code == 200:
                # Check if success message is displayed
                if 'Password reset link has been sent' in response.text or 'If an account with that email exists' in response.text:
                    self.log_test("Forgot Password Flow", "PASS")
                else:
                    self.log_test("Forgot Password Flow", "BUG", "No success message displayed")
            else:
                self.log_test("Forgot Password Flow", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Forgot Password Flow", "FAIL", str(e))
    
    def test_account_request_flow(self):
        """Test account request flow"""
        try:
            # Test account request form
            request_data = {
                'first_name': 'Test',
                'last_name': 'User',
                'child_first_name': 'Test',
                'child_last_name': 'Child',
                'email': 'test@example.com',
                'student_names': 'Test Child'
            }
            response = self.session.post(urljoin(self.base_url, "/request-account/"), data=request_data)
            
            if response.status_code == 200:
                # Check if success message is displayed
                if 'Your request has been submitted' in response.text:
                    self.log_test("Account Request Flow", "PASS")
                else:
                    self.log_test("Account Request Flow", "BUG", "No success message displayed")
            else:
                self.log_test("Account Request Flow", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Account Request Flow", "FAIL", str(e))
    
    def test_form_validation(self):
        """Test form validation"""
        try:
            # Test empty form submission
            empty_data = {}
            response = self.session.post(urljoin(self.base_url, "/request-account/"), data=empty_data)
            
            if response.status_code == 200:
                # Check if validation errors are displayed
                if 'This field is required' in response.text or 'error' in response.text.lower():
                    self.log_test("Form Validation", "PASS")
                else:
                    self.log_test("Form Validation", "BUG", "No validation errors displayed")
            else:
                self.log_test("Form Validation", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Form Validation", "FAIL", str(e))
    
    def test_static_file_serving(self):
        """Test static file serving"""
        static_files = [
            "/static/css/style.css",
            "/static/tuition/css/style.css",
        ]
        
        for file_path in static_files:
            try:
                response = self.session.get(urljoin(self.base_url, file_path))
                if response.status_code == 200:
                    self.log_test(f"Static File: {file_path}", "PASS")
                else:
                    self.log_test(f"Static File: {file_path}", "FAIL", f"Status code: {response.status_code}")
            except Exception as e:
                self.log_test(f"Static File: {file_path}", "FAIL", str(e))
    
    def test_template_rendering(self):
        """Test template rendering"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                # Check for common template elements
                if 'WAPrep' in response.text and 'Tuition' in response.text:
                    self.log_test("Template Rendering", "PASS")
                else:
                    self.log_test("Template Rendering", "BUG", "Missing expected content")
            else:
                self.log_test("Template Rendering", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Template Rendering", "FAIL", str(e))
    
    def test_navigation_links(self):
        """Test navigation links"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                # Check for navigation links
                if 'href="/login/payer/"' in response.text and 'href="/login/admin/"' in response.text:
                    self.log_test("Navigation Links", "PASS")
                else:
                    self.log_test("Navigation Links", "BUG", "Missing navigation links")
            else:
                self.log_test("Navigation Links", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Navigation Links", "FAIL", str(e))
    
    def test_error_pages(self):
        """Test error page handling"""
        try:
            # Test 404 page
            response = self.session.get(urljoin(self.base_url, "/nonexistent-page/"))
            if response.status_code == 404:
                self.log_test("404 Error Page", "PASS")
            else:
                self.log_test("404 Error Page", "BUG", f"Should return 404 but got {response.status_code}")
        except Exception as e:
            self.log_test("404 Error Page", "FAIL", str(e))
    
    def test_csrf_token_presence(self):
        """Test CSRF token presence in forms"""
        try:
            response = self.session.get(urljoin(self.base_url, "/login/payer/"))
            if response.status_code == 200:
                if 'csrfmiddlewaretoken' in response.text:
                    self.log_test("CSRF Token Presence", "PASS")
                else:
                    self.log_test("CSRF Token Presence", "BUG", "No CSRF token found in form")
            else:
                self.log_test("CSRF Token Presence", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("CSRF Token Presence", "FAIL", str(e))
    
    def test_form_methods(self):
        """Test form methods"""
        try:
            response = self.session.get(urljoin(self.base_url, "/login/payer/"))
            if response.status_code == 200:
                if 'method="post"' in response.text.lower():
                    self.log_test("Form Methods", "PASS")
                else:
                    self.log_test("Form Methods", "BUG", "Form not using POST method")
            else:
                self.log_test("Form Methods", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Form Methods", "FAIL", str(e))
    
    def test_input_validation(self):
        """Test input validation"""
        try:
            # Test with malicious input
            malicious_data = {
                'email': '<script>alert("xss")</script>',
                'first_name': 'Test<script>alert("xss")</script>',
            }
            response = self.session.post(urljoin(self.base_url, "/request-account/"), data=malicious_data)
            
            if response.status_code == 200:
                # Check if input is properly escaped
                if '<script>' not in response.text or '&lt;script&gt;' in response.text:
                    self.log_test("Input Validation", "PASS")
                else:
                    self.log_test("Input Validation", "BUG", "Input not properly escaped")
            else:
                self.log_test("Input Validation", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Input Validation", "FAIL", str(e))
    
    def test_session_cookies(self):
        """Test session cookie handling"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                # Check if session cookie is set
                if 'sessionid' in self.session.cookies:
                    self.log_test("Session Cookies", "PASS")
                else:
                    self.log_test("Session Cookies", "BUG", "No session cookie found")
            else:
                self.log_test("Session Cookies", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Session Cookies", "FAIL", str(e))
    
    def test_redirect_handling(self):
        """Test redirect handling"""
        try:
            # Test redirect to login
            response = self.session.get(urljoin(self.base_url, "/students/"), allow_redirects=False)
            if response.status_code == 302:
                # Check if redirect location is correct
                if 'login' in response.headers.get('Location', '').lower():
                    self.log_test("Redirect Handling", "PASS")
                else:
                    self.log_test("Redirect Handling", "BUG", "Incorrect redirect location")
            else:
                self.log_test("Redirect Handling", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Redirect Handling", "FAIL", str(e))
    
    def test_message_display(self):
        """Test message display system"""
        try:
            # Test forgot password to trigger a message
            response = self.session.post(urljoin(self.base_url, "/forgot-password/"), 
                                       data={'email': 'test@example.com'})
            
            if response.status_code == 200:
                # Check if Django messages are displayed
                if 'messages' in response.text or 'alert' in response.text.lower():
                    self.log_test("Message Display", "PASS")
                else:
                    self.log_test("Message Display", "BUG", "No message display found")
            else:
                self.log_test("Message Display", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Message Display", "FAIL", str(e))
    
    def test_database_operations(self):
        """Test database operations through forms"""
        try:
            # Test account request (should create database record)
            request_data = {
                'first_name': 'DBTest',
                'last_name': 'User',
                'child_first_name': 'DBTest',
                'child_last_name': 'Child',
                'email': 'dbtest@example.com',
                'student_names': 'DBTest Child'
            }
            response = self.session.post(urljoin(self.base_url, "/request-account/"), data=request_data)
            
            if response.status_code == 200:
                if 'Your request has been submitted' in response.text:
                    self.log_test("Database Operations", "PASS")
                else:
                    self.log_test("Database Operations", "BUG", "Database operation may have failed")
            else:
                self.log_test("Database Operations", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Database Operations", "FAIL", str(e))
    
    def test_email_functionality(self):
        """Test email functionality"""
        try:
            # Test forgot password (should trigger email)
            response = self.session.post(urljoin(self.base_url, "/forgot-password/"), 
                                       data={'email': 'test@example.com'})
            
            if response.status_code == 200:
                if 'Password reset link has been sent' in response.text:
                    self.log_test("Email Functionality", "PASS", "Email form processed successfully")
                else:
                    self.log_test("Email Functionality", "BUG", "Email form not processed correctly")
            else:
                self.log_test("Email Functionality", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Email Functionality", "FAIL", str(e))
    
    def test_stripe_integration_ui(self):
        """Test Stripe integration UI elements"""
        try:
            # Test payment page (should show Stripe elements)
            response = self.session.get(urljoin(self.base_url, "/payment/1/"))
            
            if response.status_code == 302:
                self.log_test("Stripe Integration UI", "PASS", "Payment page redirects to login as expected")
            elif response.status_code == 200:
                # Check for Stripe-related elements
                if 'stripe' in response.text.lower() or 'payment' in response.text.lower():
                    self.log_test("Stripe Integration UI", "PASS", "Payment page loads with Stripe elements")
                else:
                    self.log_test("Stripe Integration UI", "BUG", "Payment page missing Stripe elements")
            else:
                self.log_test("Stripe Integration UI", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Stripe Integration UI", "FAIL", str(e))
    
    def test_mobile_responsiveness_detailed(self):
        """Test mobile responsiveness in detail"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                content = response.text.lower()
                
                mobile_features = []
                if 'viewport' in content:
                    mobile_features.append("viewport meta tag")
                if 'media=' in content:
                    mobile_features.append("media queries")
                if 'responsive' in content:
                    mobile_features.append("responsive design")
                
                if mobile_features:
                    self.log_test("Mobile Responsiveness", "PASS", f"Found: {', '.join(mobile_features)}")
                else:
                    self.log_test("Mobile Responsiveness", "BUG", "No mobile responsiveness features found")
            else:
                self.log_test("Mobile Responsiveness", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Mobile Responsiveness", "FAIL", str(e))
    
    def test_accessibility_features(self):
        """Test accessibility features"""
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                content = response.text.lower()
                
                accessibility_features = []
                if 'alt=' in content:
                    accessibility_features.append("alt attributes")
                if 'aria-' in content:
                    accessibility_features.append("ARIA attributes")
                if 'role=' in content:
                    accessibility_features.append("role attributes")
                if 'label' in content:
                    accessibility_features.append("form labels")
                
                if accessibility_features:
                    self.log_test("Accessibility Features", "PASS", f"Found: {', '.join(accessibility_features)}")
                else:
                    self.log_test("Accessibility Features", "BUG", "No accessibility features found")
            else:
                self.log_test("Accessibility Features", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Accessibility Features", "FAIL", str(e))
    
    def test_performance_basics(self):
        """Test basic performance"""
        try:
            start_time = time.time()
            response = self.session.get(self.base_url)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response.status_code == 200:
                if response_time < 2.0:  # Less than 2 seconds
                    self.log_test("Performance Basics", "PASS", f"Response time: {response_time:.2f}s")
                else:
                    self.log_test("Performance Basics", "BUG", f"Slow response time: {response_time:.2f}s")
            else:
                self.log_test("Performance Basics", "FAIL", f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Performance Basics", "FAIL", str(e))
    
    def run_all_tests(self):
        """Run all manual tests"""
        print("🔧 Starting manual testing of WAPrep Tuition Application...")
        print("=" * 80)
        
        # Authentication and form tests
        self.test_payer_login_flow()
        self.test_admin_login_flow()
        self.test_forgot_password_flow()
        self.test_account_request_flow()
        self.test_form_validation()
        
        # UI and template tests
        self.test_static_file_serving()
        self.test_template_rendering()
        self.test_navigation_links()
        self.test_error_pages()
        
        # Security tests
        self.test_csrf_token_presence()
        self.test_form_methods()
        self.test_input_validation()
        self.test_session_cookies()
        self.test_redirect_handling()
        
        # Functionality tests
        self.test_message_display()
        self.test_database_operations()
        self.test_email_functionality()
        self.test_stripe_integration_ui()
        
        # UX tests
        self.test_mobile_responsiveness_detailed()
        self.test_accessibility_features()
        self.test_performance_basics()
        
        print("=" * 80)
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📊 MANUAL TEST REPORT SUMMARY")
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
        report_filename = f"manual_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_filename}")

if __name__ == "__main__":
    tester = ManualTester()
    tester.run_all_tests() 