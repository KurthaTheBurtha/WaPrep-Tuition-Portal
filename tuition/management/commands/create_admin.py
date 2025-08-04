from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Create default admin user with email admin@waprep.org'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Default admin credentials
        email = "admin@waprep.org"
        password = "Admin123!@#"
        first_name = "Admin"
        last_name = "User"

        try:
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Admin user with email {email} already exists!'
                    )
                )
                return

            # Create the admin user
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
                    f'User Type: Admin\n'
                    f'Django admin access: Enabled\n'
                    f'Status: Active'
                )
            )

        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Database integrity error: {str(e)}\n'
                    f'This may indicate the user already exists or there\'s a constraint violation.'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            ) 