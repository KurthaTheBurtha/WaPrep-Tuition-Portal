import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://gateway.stage.bill.com/connect/v3"
DEV_KEY = os.getenv("BILL_DEV_KEY")
USERNAME = os.getenv("BILL_USERNAME")
PASSWORD = os.getenv("BILL_PASSWORD")
ORG_ID = os.getenv("BILL_ORG_ID")

def get_session_id():
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

def create_vendor(session_id, vendor_data):
    url = f"{API_URL}/vendors"
    headers = {
        "Content-Type": "application/json",
        "devKey": DEV_KEY,
        "sessionId": session_id
    }
    response = requests.post(url, json=vendor_data, headers=headers)
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)
    response.raise_for_status()
    return response.json()

def create_bank_account(session_id, vendor_id, bank_data):
    url = f"{API_URL}/bank-accounts"
    headers = {
        "Content-Type": "application/json",
        "X-Bill-Com-SessionId": session_id,
        "X-Bill-Com-DevKey": DEV_KEY
    }
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

def create_bill(session_id, vendor_id, bill_data):
    url = f"{API_URL}/bills"
    headers = {
        "Content-Type": "application/json",
        "X-Bill-Com-SessionId": session_id,
        "X-Bill-Com-DevKey": DEV_KEY
    }
    payload = {
        "vendorId": vendor_id,
        "amount": bill_data["amount"],
        "description": bill_data.get("description", "Payment"),
        "invoiceNumber": bill_data.get("invoiceNumber", "INV-001")
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def pay_bill(session_id, bill_id):
    url = f"{API_URL}/payments"
    headers = {
        "Content-Type": "application/json",
        "X-Bill-Com-SessionId": session_id,
        "X-Bill-Com-DevKey": DEV_KEY
    }
    payload = {
        "billId": bill_id,
        "paymentType": "ACH"
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()