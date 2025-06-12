import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://gateway.stage.bill.com/connect/v3"
USERNAME = os.getenv("BILL_USERNAME")
PASSWORD = os.getenv("BILL_PASSWORD")
ORG_ID = os.getenv("BILL_ORG_ID")
DEV_KEY = os.getenv("BILL_DEV_KEY")

def get_session_id():
    url = f"{API_URL}/login"
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "organizationId": ORG_ID,
        "devKey": DEV_KEY
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["sessionId"]

def create_vendor(session_id):
    url = f"{API_URL}/vendors"
    headers = {
        "Content-Type": "application/json",
        "devKey": DEV_KEY,
        "sessionId": session_id
    }
    print("Headers:", headers)

    vendor_data = {
        "name": "Test",
        "accountType": "PERSON",
        "email": "test.vendor@example.com",
        "phone": "1112223333",
        "companyName": "Test Vendor Inc.",
        "address": {
            "line1": "123 Main St",
            "city": "Seattle",
            "zipOrPostalCode": "98101",
            "country": "US"
        },
        "paymentInformation": {
            "payeeName": "tester",
            "nameOnAccount": "test",
            "accountNumber": "192736912637",
            "routingNumber": "18723612798"
        }
    }

    response = requests.post(url, json=vendor_data, headers=headers)
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)
    response.raise_for_status()
    return response.json()

def send_payment(session_id, payment_data):
    url = "https://gateway.stage.bill.com/connect/v3/payments"
    headers = {
        "Content-Type": "application/json",
        "devKey": DEV_KEY,
        "sessionId": session_id
    }
    response = requests.post(url, json=payment_data, headers=headers)
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    session_id = get_session_id()
    vendor = create_vendor(session_id)
    vendor_id = vendor['id']
    payment_data = {
        "vendorId": vendor_id,
        "description": "Inv #20251201",
        "processDate": "2025-12-01",
        "fundingAccount": {
            "type": "BANK_ACCOUNT",
            "id": "{bank_account_id}"
        },
        "amount": 228.99,
        "processingOptions": {
            "createBill": True,
            "requestPayFaster": True,
            "requestCheckDeliveryType": "RTP_DELIVERY"
        }
    }
    
    payment = send_payment(session_id, payment_data)
    print(f"Payment created: {payment}")
