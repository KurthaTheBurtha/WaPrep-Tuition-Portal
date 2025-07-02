from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tuition.models import User
import secrets
import string

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a new payer user'

    def add_arguments(self, parser):
        parser.add_argument('--first_name', type=str, required=True, help='First name')
        parser.add_argument('--last_name', type=str, required=True, help='Last name')
        parser.add_argument('--email', type=str, required=True, help='Email address')
        parser.add_argument('--user_id', type=str, help='Custom user ID (optional)')
        parser.add_argument('--password', type=str, help='Custom password (optional)')

    def handle(self, *args, **options):
        first_name = options['first_name']
        last_name = options['last_name']
        email = options['email']
        user_id = options.get('user_id')
        password = options.get('password')

        # Generate user ID if not provided
        if not user_id:
            user_id = self.generate_unique_user_id(first_name, last_name)

        # Generate password if not provided
        if not password:
            password = self.generate_strong_password()

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email {email} already exists!')
            )
            return

        if User.objects.filter(user_id=user_id).exists():
            self.stdout.write(
                self.style.ERROR(f'User with ID {user_id} already exists!')
            )
            return

        # Create the user
        try:
            user = User.objects.create_user(
                username=user_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                user_type='payer',
                user_id=user_id,
                is_active=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created payer user:\n'
                    f'Name: {first_name} {last_name}\n'
                    f'Email: {email}\n'
                    f'User ID: {user_id}\n'
                    f'Password: {password}\n'
                    f'User Type: Payer'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {str(e)}')
            )

    def generate_unique_user_id(self, first_name, last_name):
        """Generate a unique 8-character user ID"""
        letters = string.ascii_letters
        digits = string.digits
        special_chars = "!@#$%^&*"
        all_chars = letters + digits + special_chars
        
        max_attempts = 1000
        attempts = 0
        
        while attempts < max_attempts:
            user_id = ''.join(secrets.choice(all_chars) for _ in range(8))
            
            # Ensure it contains at least one letter, one number, and one special character
            has_letter = any(c in letters for c in user_id)
            has_digit = any(c in digits for c in user_id)
            has_special = any(c in special_chars for c in user_id)
            
            if has_letter and has_digit and has_special:
                if not User.objects.filter(user_id=user_id).exists():
                    return user_id
            
            attempts += 1
        
        # Fallback
        while True:
            user_id = 'P' + ''.join(secrets.choice(string.ascii_uppercase + string.digits + "!@#$%^&*") for _ in range(7))
            if not User.objects.filter(user_id=user_id).exists():
                return user_id

    def generate_strong_password(self):
        """Generate a strong password"""
        letters = string.ascii_letters
        digits = string.digits
        special_chars = "!@#$%^&*"
        
        # Ensure at least one of each type
        password = [
            secrets.choice(letters),
            secrets.choice(digits),
            secrets.choice(special_chars)
        ]
        
        # Fill the rest randomly
        all_chars = letters + digits + special_chars
        password.extend(secrets.choice(all_chars) for _ in range(13))  # Total 16 chars
        
        # Shuffle the password
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return ''.join(password_list) 