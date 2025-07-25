import os
import random
from django.conf import settings
from django.core.cache import cache
from twilio.rest import Client
from twilio.base.exceptions import TwilioException


def mask_phone_number(phone_number):
    """Mask phone number to show only last 4 digits"""
    if not phone_number or len(phone_number) < 4:
        return phone_number
    
    # Remove any non-digit characters for consistent masking
    digits_only = ''.join(filter(str.isdigit, phone_number))
    
    if len(digits_only) <= 4:
        return phone_number
    
    # Show last 4 digits, mask the rest with asterisks
    masked = '*' * (len(digits_only) - 4) + digits_only[-4:]
    
    # If original had formatting, try to preserve it
    if phone_number.startswith('+'):
        return '+' + masked
    elif phone_number.startswith('1') and len(phone_number) > 10:
        return masked
    
    return masked


class SMS2FA:
    """SMS-based 2FA utility class"""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_FROM_NUMBER', None)
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
    
    def generate_code(self):
        """Generate a 6-digit verification code"""
        return str(random.randint(100000, 999999))
    
    def send_verification_code(self, phone_number, code):
        """Send verification code via SMS"""
        if not self.client or not self.from_number:
            # In development/testing, just log the code
            print("=" * 60)
            print(f"🔐 SMS 2FA VERIFICATION CODE")
            print(f"📱 Phone: {phone_number}")
            print(f"🔢 Code: {code}")
            print(f"⏰ Valid for 5 minutes")
            print("=" * 60)
            return True
        
        try:
            message = self.client.messages.create(
                body=f"WaPrep Tuition Portal: Your verification code is {code}. Valid for 5 minutes.",
                from_=self.from_number,
                to=phone_number
            )
            return message.sid is not None
        except TwilioException as e:
            print(f"Twilio error: {e}")
            return False
    
    def store_code(self, user_id, code, expires_in=300):
        """Store verification code in cache with expiration"""
        cache_key = f"sms_2fa_code_{user_id}"
        cache.set(cache_key, code, expires_in)
    
    def verify_code(self, user_id, code):
        """Verify the provided code against stored code"""
        cache_key = f"sms_2fa_code_{user_id}"
        stored_code = cache.get(cache_key)
        
        if stored_code and stored_code == code:
            # Remove the code from cache after successful verification
            cache.delete(cache_key)
            return True
        return False
    
    def is_configured(self):
        """Check if SMS service is properly configured"""
        return bool(self.account_sid and self.auth_token and self.from_number)


# Global instance
sms_2fa = SMS2FA() 