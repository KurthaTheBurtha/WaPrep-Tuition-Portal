import re
from typing import Tuple, List

# Common weak passwords to block
COMMON_PASSWORDS = {
    'password', 'password123', '123456', '123456789', 'qwerty', 'abc123',
    'password1', 'admin', 'letmein', 'welcome', 'monkey', 'dragon',
    'master', 'hello', 'freedom', 'whatever', 'qwerty123', 'trustno1',
    'jordan', 'harley', 'ranger', 'iwantu', 'jennifer', 'hunter',
    'buster', 'soccer', 'baseball', 'tiger', 'charlie', 'andrew',
    'michelle', 'love', 'sunshine', 'jessica', 'asshole', '696969',
    'killer', 'mustang', 'shadow', 'merlin', 'diamond', 'nascar',
    'jackson', 'cameron', '654321', 'computer', 'amanda', 'wizard',
    'xxxxxxxx', 'money', 'phoenix', 'mickey', 'bailey', 'knight',
    'iceman', 'tigers', 'purple', 'andrea', 'horny', 'dakota',
    'aaaaaa', 'player', 'sunshine', 'morgan', 'starwars', 'boomer',
    'cowboys', 'edward', 'charles', 'girls', 'coffee', 'bulldog',
    'ncc1701', 'rabbit', 'peanut', 'johnson', 'chester', 'london',
    'midnight', 'blue', 'fishing', '000000', 'hannah', 'slayer',
    '111111', 'rachel', 'test', 'bitch', 'orange', 'michelle',
    'helpme', 'fuckme', 'tucker', 'secret', 'god', 'zxcvbnm',
    'mercedes', 'beer', 'jackson', 'cowboy', 'silver', 'johnson',
    'thomas', 'hunter', 'michelle', 'charlie', 'andrew', 'matthew',
    'access', 'yankees', '987654321', 'dallas', 'austin', 'thunder',
    'taylor', 'matrix', 'mobilemail', 'mom', 'monitor', 'monitoring',
    'montana', 'moon', 'moscow', 'mother', 'movie', 'mozilla',
    'music', 'mustang', 'password', 'pa$$w0rd', 'p@ssw0rd', 'p@$$w0rd'
}

def validate_password(password: str, user=None) -> Tuple[bool, str]:
    """
    Validate password strength and return (is_valid, message).
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one number
    - At least one special character (!@#$%^&*)
    - Not a common password
    - No consecutive repeating characters (e.g., 'aaa')
    - No keyboard patterns (e.g., 'qwerty', '123456')
    - Not recently used by the same user (if user is provided)
    """
    if not password:
        return False, "Password is required"
    
    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check maximum length (reasonable limit)
    if len(password) > 128:
        return False, "Password is too long (maximum 128 characters)"
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for number
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    # Check for special character
    if not re.search(r'[!@#$%^&*]', password):
        return False, "Password must contain at least one special character (!@#$%^&*)"
    
    # Check for common passwords
    if password.lower() in COMMON_PASSWORDS:
        return False, "This password is too common. Please choose a more unique password"
    
    # Check for consecutive repeating characters (more than 2)
    if re.search(r'(.)\1{2,}', password):
        return False, "Password cannot contain more than 2 consecutive identical characters"
    
    # Check for keyboard patterns
    keyboard_patterns = [
        'qwerty', 'asdfgh', 'zxcvbn', '123456', '654321',
        'abcdef', 'ghijkl', 'mnopqr', 'stuvwx', 'yzabcd'
    ]
    password_lower = password.lower()
    for pattern in keyboard_patterns:
        if pattern in password_lower:
            return False, "Password cannot contain keyboard patterns"
    
    # Check for personal information patterns (basic check)
    personal_patterns = [
        r'\b(admin|root|user|test|guest|demo)\b',
        r'\b(password|pass|pwd|secret)\b',
        r'\b(123|321|000|111|222|333|444|555|666|777|888|999)\b'
    ]
    for pattern in personal_patterns:
        if re.search(pattern, password_lower):
            return False, "Password contains common insecure patterns"
    
    # Check if password has been used recently by this user
    if user:
        try:
            from .models import PasswordHistory
            if PasswordHistory.is_password_reused(user, password):
                return False, "You cannot reuse any of your last 5 passwords. Please choose a different password."
        except ImportError:
            # If PasswordHistory model is not available (e.g., during migrations), skip this check
            pass
    
    return True, "Password meets all security requirements"

def get_password_strength(password: str) -> Tuple[str, int]:
    """
    Calculate password strength and return (strength_label, score).
    
    Returns:
    - strength_label: 'Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'
    - score: 0-100
    """
    if not password:
        return "Very Weak", 0
    
    score = 0
    
    # Length contribution (up to 25 points)
    if len(password) >= 8:
        score += 10
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 5
    
    # Character variety contribution (up to 40 points)
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'\d', password):
        score += 10
    if re.search(r'[!@#$%^&*]', password):
        score += 10
    
    # Complexity bonus (up to 20 points)
    unique_chars = len(set(password))
    if unique_chars >= 8:
        score += 10
    if unique_chars >= 12:
        score += 10
    
    # Penalties
    if password.lower() in COMMON_PASSWORDS:
        score -= 30
    if re.search(r'(.)\1{2,}', password):
        score -= 15
    if len(password) < 8:
        score -= 20
    
    # Ensure score is within bounds
    score = max(0, min(100, score))
    
    # Determine strength label
    if score < 20:
        return "Very Weak", score
    elif score < 40:
        return "Weak", score
    elif score < 60:
        return "Fair", score
    elif score < 80:
        return "Good", score
    elif score < 90:
        return "Strong", score
    else:
        return "Very Strong", score

def generate_strong_password() -> str:
    """
    Generate a strong password that meets all requirements.
    """
    import random
    import string
    
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"
    
    # Ensure at least one of each required character type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Fill the rest with random characters
    all_chars = lowercase + uppercase + digits + special
    for _ in range(4):  # Total length will be 8
        password.append(random.choice(all_chars))
    
    # Shuffle the password
    random.shuffle(password)
    
    return ''.join(password)

def clear_messages(request):
    """
    Clear all Django messages from the request.
    Useful for preventing message persistence across redirects.
    """
    from django.contrib import messages
    storage = messages.get_messages(request)
    storage.used = True 