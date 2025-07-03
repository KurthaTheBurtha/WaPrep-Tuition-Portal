from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser for the staging server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='admin@waprep.org',
            help='Email for the superuser (default: admin@waprep.org)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='WAPrep2024!',
            help='Password for the superuser (default: WAPrep2024!)'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Admin',
            help='First name for the superuser (default: Admin)'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='User',
            help='Last name for the superuser (default: User)'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']

        try:
            # Check if superuser already exists
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                if user.is_superuser:
                    self.stdout.write(
                        self.style.WARNING(f'Superuser with email {email} already exists.')
                    )
                    return
                else:
                    # Make existing user a superuser
                    user.is_superuser = True
                    user.is_staff = True
                    user.user_type = 'admin'
                    user.set_password(password)
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Existing user {email} has been promoted to superuser.')
                    )
                    return

            # Create new superuser
            user = User.objects.create_superuser(
                username=email,  # Use email as username
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type='admin',
                user_id='ADMIN01'  # Simple admin ID
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser created successfully!\n'
                    f'Email: {email}\n'
                    f'Password: {password}\n'
                    f'User ID: {user.user_id}'
                )
            )

        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Unexpected error: {e}')
            ) 