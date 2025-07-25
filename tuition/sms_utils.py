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