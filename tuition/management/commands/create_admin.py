from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tuition.models import User
import secrets
import string

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a new admin user'

    def add_arguments(self, parser):
        parser.add_argument('--first_name', type=str, required=True, help='First name')
        parser.add_argument('--last_name', type=str, required=True, help='Last name')
        parser.add_argument('--email', type=str, required=True, help='Email address')
        parser.add_argument('--password', type=str, help='Custom password (optional)')

    def handle(self, *args, **options):
        first_name = options['first_name']
        last_name = options['last_name']
        email = options['email']
        password = options.get('password')

        # Generate password if not provided
        if not password:
            password = self.generate_strong_password()

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email {email} already exists!')
            )
            return

        # Create the user
        try:
            user = User.objects.create_user(
                username=email,  # Use email as username for admin
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                user_type='admin',
                user_id=email,  # Use email as user_id for admin
                is_active=True,
                is_staff=True,
                is_superuser=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created admin user:\n'
                    f'Name: {first_name} {last_name}\n'
                    f'Email: {email}\n'
                    f'Password: {password}\n'
                    f'User Type: Admin\n'
                    f'Can access Django admin: Yes'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {str(e)}')
            )

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