#!/usr/bin/env python3
"""
Debug script to test the account request endpoint and identify 500 errors.
"""

import requests
import json

def test_account_request():
    """Test the account request endpoint to identify 500 errors."""
    url = "http://localhost:8000/request-account/"
    
    # Test GET request first
    print("Testing GET request to account request page...")
    try:
        response = requests.get(url)
        print(f"GET Status: {response.status_code}")
        if response.status_code == 200:
            print("GET request successful")
        else:
            print(f"GET request failed: {response.text[:200]}")
    except Exception as e:
        print(f"GET request error: {e}")
    
    # Test POST request
    print("\nTesting POST request to account request page...")
    data = {
        'first_name': 'Test',
        'last_name': 'User', 
        'email': 'test@example.com',
        'student_names': 'Test Student'
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"POST Status: {response.status_code}")
        if response.status_code == 200:
            print("POST request successful")
        elif response.status_code == 302:
            print("POST request redirected (expected)")
        else:
            print(f"POST request failed: {response.text[:500]}")
    except Exception as e:
        print(f"POST request error: {e}")

def test_forgot_password():
    """Test the forgot password endpoint."""
    url = "http://localhost:8000/forgot-password/"
    
    print("\nTesting forgot password endpoint...")
    data = {
        'email': 'test@example.com'
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Forgot Password Status: {response.status_code}")
        if response.status_code == 200:
            print("Forgot password request successful")
        elif response.status_code == 302:
            print("Forgot password request redirected (expected)")
        else:
            print(f"Forgot password request failed: {response.text[:500]}")
    except Exception as e:
        print(f"Forgot password request error: {e}")

if __name__ == "__main__":
    print("🔍 Debug Testing WAPrep Tuition Application...")
    print("=" * 60)
    
    test_account_request()
    test_forgot_password()
    
    print("\n" + "=" * 60)
    print("Debug testing completed.") 