from django.core.management.base import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice
from tuition.models import User


class Command(BaseCommand):
    help = 'Reset 2FA for admin users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email of specific admin user to reset 2FA for',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reset 2FA for all admin users',
        )

    def handle(self, *args, **options):
        email = options['email']
        all_admins = options['all']

        if email:
            # Reset 2FA for specific user
            try:
                user = User.objects.get(email=email, user_type='admin')
                self.reset_2fa_for_user(user)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Admin user with email {email} not found.')
                )
        elif all_admins:
            # Reset 2FA for all admin users
            admin_users = User.objects.filter(user_type='admin')
            if not admin_users.exists():
                self.stdout.write(
                    self.style.WARNING('No admin users found.')
                )
                return

            self.stdout.write(f'Found {admin_users.count()} admin user(s).')
            for user in admin_users:
                self.reset_2fa_for_user(user)
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify either --email <email> or --all to reset 2FA.'
                )
            )

    def reset_2fa_for_user(self, user):
        """Reset 2FA for a specific user"""
        # Delete TOTP devices
        devices = TOTPDevice.objects.filter(user=user)
        device_count = devices.count()
        devices.delete()

        # Reset 2FA fields
        user.two_factor_enabled = False
        user.two_factor_setup_complete = False
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ 2FA reset for {user.email} ({user.get_full_name()})'
            )
        )
        self.stdout.write(f'   Deleted {device_count} TOTP device(s)')
        self.stdout.write(f'   2FA enabled: {user.two_factor_enabled}')
        self.stdout.write(f'   2FA setup complete: {user.two_factor_setup_complete}')
        self.stdout.write('') 