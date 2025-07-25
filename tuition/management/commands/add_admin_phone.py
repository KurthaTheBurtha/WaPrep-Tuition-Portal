from django.core.management.base import BaseCommand
from tuition.models import User


class Command(BaseCommand):
    help = 'Add phone number to admin user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email of admin user to add phone number to',
        )
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Phone number to add (with country code)',
        )
        parser.add_argument(
            '--method',
            type=str,
            choices=['totp', 'sms'],
            default='sms',
            help='2FA method preference (default: sms)',
        )

    def handle(self, *args, **options):
        email = options['email']
        phone = options['phone']
        method = options['method']

        try:
            user = User.objects.get(email=email, user_type='admin')
            
            # Update phone number and 2FA method
            user.phone_number = phone
            user.two_factor_method = method
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Phone number {phone} added to admin user {email}'
                )
            )
            self.stdout.write(f'   2FA method set to: {method.upper()}')
            
            # Show current 2FA status
            self.stdout.write(f'   2FA enabled: {user.two_factor_enabled}')
            self.stdout.write(f'   2FA setup complete: {user.two_factor_setup_complete}')
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Admin user with email {email} not found.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            ) 