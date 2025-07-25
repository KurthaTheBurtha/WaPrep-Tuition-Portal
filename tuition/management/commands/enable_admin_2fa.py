from django.core.management.base import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex
from tuition.models import User


class Command(BaseCommand):
    help = 'Enable 2FA for admin users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email of specific admin user to enable 2FA for',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Enable 2FA for all admin users',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        email = options['email']
        all_admins = options['all']

        if email:
            # Enable 2FA for specific user
            try:
                user = User.objects.get(email=email, user_type='admin')
                self.enable_2fa_for_user(user, dry_run)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Admin user with email {email} not found.')
                )
        elif all_admins:
            # Enable 2FA for all admin users
            admin_users = User.objects.filter(user_type='admin')
            if not admin_users.exists():
                self.stdout.write(
                    self.style.WARNING('No admin users found.')
                )
                return

            self.stdout.write(f'Found {admin_users.count()} admin user(s).')
            for user in admin_users:
                self.enable_2fa_for_user(user, dry_run)
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify either --email <email> or --all to enable 2FA.'
                )
            )

    def enable_2fa_for_user(self, user, dry_run):
        """Enable 2FA for a specific user"""
        if dry_run:
            self.stdout.write(
                f'[DRY RUN] Would enable 2FA for {user.email} ({user.get_full_name()})'
            )
            return

        # Check if user already has 2FA enabled
        if user.two_factor_enabled:
            self.stdout.write(
                self.style.WARNING(
                    f'2FA already enabled for {user.email}'
                )
            )
            return

        # Handle different 2FA methods
        if user.two_factor_method == 'sms':
            # For SMS 2FA, we don't need a TOTP device
            if not user.phone_number:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ SMS 2FA requires a phone number for {user.email}'
                    )
                )
                return
            
            # Enable 2FA on user
            user.two_factor_enabled = True
            user.two_factor_setup_complete = True
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ SMS 2FA enabled for {user.email} ({user.get_full_name()})'
                )
            )
            self.stdout.write(f'   Phone number: {user.phone_number}')
            self.stdout.write(f'   2FA method: SMS')
            self.stdout.write('')
        else:
            # Create TOTP device for TOTP method
            device = TOTPDevice.objects.create(
                user=user,
                name='default',
                confirmed=True,
                key=random_hex()
            )

            # Enable 2FA on user
            user.two_factor_enabled = True
            user.two_factor_setup_complete = True
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ TOTP 2FA enabled for {user.email} ({user.get_full_name()})'
                )
            )
            self.stdout.write(f'   Secret key: {device.key}')
            self.stdout.write(f'   Config URL: {device.config_url}')
            self.stdout.write('') 