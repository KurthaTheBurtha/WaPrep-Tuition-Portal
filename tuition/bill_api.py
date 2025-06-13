import requests
import os
from dotenv import load_dotenv
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# BILL API Configuration
API_URL = "https://gateway.stage.bill.com/connect/v3"  # Change to production URL when ready
DEV_KEY = os.getenv("BILL_DEV_KEY")
USERNAME = os.getenv("BILL_USERNAME")
PASSWORD = os.getenv("BILL_PASSWORD")
ORG_ID = os.getenv("BILL_ORG_ID")

class BillAPIError(Exception):
    """Custom exception for BILL API errors"""
    pass

def get_session_id():
    """Get a session ID from BILL API"""
    try:
        url = f"{API_URL}/login"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "username": USERNAME,
            "password": PASSWORD,
            "organizationId": ORG_ID,
            "devKey": DEV_KEY
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()["sessionId"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get BILL session ID: {str(e)}")
        raise BillAPIError(f"Failed to authenticate with BILL: {str(e)}")

def create_vendor(session_id, vendor_data):
    """Create a vendor in BILL"""
    try:
        url = f"{API_URL}/vendors"
        headers = {
            "Content-Type": "application/json",
            "devKey": DEV_KEY,
            "sessionId": session_id
        }
        
        # Ensure required fields are present
        required_fields = ["name", "email"]
        for field in required_fields:
            if field not in vendor_data:
                raise BillAPIError(f"Missing required field: {field}")
        
        response = requests.post(url, json=vendor_data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create vendor in BILL: {str(e)}")
        raise BillAPIError(f"Failed to create vendor: {str(e)}")

def create_bank_account(session_id, vendor_id, bank_data):
    """Create a bank account in BILL"""
    try:
        url = f"{API_URL}/bank-accounts"
        headers = {
            "Content-Type": "application/json",
            "devKey": DEV_KEY,
            "sessionId": session_id
        }
        
        # Validate bank data
        required_fields = ["bankAccountNumber", "routingNumber", "accountType", "bankAccountName"]
        for field in required_fields:
            if field not in bank_data:
                raise BillAPIError(f"Missing required field: {field}")
        
        payload = {
            "entity": "vendor",
            "entityId": vendor_id,
            "bankAccountNumber": bank_data["bankAccountNumber"],
            "routingNumber": bank_data["routingNumber"],
            "accountType": bank_data["accountType"],
            "bankAccountName": bank_data["bankAccountName"]
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create bank account in BILL: {str(e)}")
        raise BillAPIError(f"Failed to create bank account: {str(e)}")

def create_bill(session_id, vendor_id, bill_data):
    """Create a bill in BILL"""
    try:
        url = f"{API_URL}/bills"
        headers = {
            "Content-Type": "application/json",
            "devKey": DEV_KEY,
            "sessionId": session_id
        }
        
        # Validate bill data
        if "amount" not in bill_data:
            raise BillAPIError("Missing required field: amount")
        
        payload = {
            "vendorId": vendor_id,
            "amount": str(bill_data["amount"]),
            "description": bill_data.get("description", "Payment"),
            "invoiceNumber": bill_data.get("invoiceNumber", "INV-001"),
            "dueDate": bill_data.get("dueDate"),
            "lineItems": bill_data.get("lineItems", [])
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create bill in BILL: {str(e)}")
        raise BillAPIError(f"Failed to create bill: {str(e)}")

def pay_bill(session_id, bill_id):
    """Process a payment for a bill in BILL"""
    try:
        url = f"{API_URL}/payments"
        headers = {
            "Content-Type": "application/json",
            "devKey": DEV_KEY,
            "sessionId": session_id
        }
        
        payload = {
            "billId": bill_id,
            "paymentType": "ACH",
            "processDate": "TODAY"  # Process immediately
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to process payment in BILL: {str(e)}")
        raise BillAPIError(f"Failed to process payment: {str(e)}")

def get_payment_status(session_id, payment_id):
    """Get the status of a payment in BILL"""
    try:
        url = f"{API_URL}/payments/{payment_id}"
        headers = {
            "Content-Type": "application/json",
            "devKey": DEV_KEY,
            "sessionId": session_id
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get payment status from BILL: {str(e)}")
        raise BillAPIError(f"Failed to get payment status: {str(e)}")

def get_bill_details(session_id, bill_id):
    """Get details of a bill in BILL"""
    try:
        url = f"{API_URL}/bills/{bill_id}"
        headers = {
            "Content-Type": "application/json",
            "devKey": DEV_KEY,
            "sessionId": session_id
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get bill details from BILL: {str(e)}")
        raise BillAPIError(f"Failed to get bill details: {str(e)}")