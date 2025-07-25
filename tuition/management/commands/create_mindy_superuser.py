from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser with specific credentials for Mindy'

    def handle(self, *args, **options):
        try:
            # Check if user already exists
            if User.objects.filter(email='mindy@waprep.org').exists():
                self.stdout.write(
                    self.style.WARNING('Superuser with email mindy@waprep.org already exists.')
                )
                return

            # Create the superuser with all required fields
            user = User.objects.create_user(
                username='mindy@waprep.org',
                email='mindy@waprep.org',
                password='Qol54170!',
                first_name='Mindy',
                last_name='Admin',
                user_type='admin',
                is_staff=True,
                is_superuser=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created superuser:\n'
                    f'Username: mindy@waprep.org\n'
                    f'Password: Qol54170!\n'
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