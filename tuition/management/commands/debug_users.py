from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug user creation and authentication issues'

    def add_arguments(self, parser):
        parser.add_argument('--create-test-users', action='store_true', help='Create test users for debugging')
        parser.add_argument('--list-users', action='store_true', help='List all users and their status')
        parser.add_argument('--activate-user', type=str, help='Activate a user by email or user_id')
        parser.add_argument('--reset-password', type=str, help='Reset password for a user (email or user_id)')

    def handle(self, *args, **options):
        if options['create_test_users']:
            self.create_test_users()
        elif options['list_users']:
            self.list_users()
        elif options['activate_user']:
            self.activate_user(options['activate_user'])
        elif options['reset_password']:
            self.reset_password(options['reset_password'])
        else:
            self.stdout.write(self.style.ERROR('Please specify an action. Use --help for options.'))

    def create_test_users(self):
        """Create test users for debugging"""
        try:
            with transaction.atomic():
                # Create test payer
                payer_user = User.objects.create_user(
                    username='TEST001',
                    first_name='Test',
                    last_name='Payer',
                    email='testpayer@example.com',
                    password='Test123!@#',
                    user_type='payer',
                    user_id='TEST001',
                    is_active=True
                )
                
                # Create test admin
                admin_user = User.objects.create_user(
                    username='admin@test.com',
                    first_name='Test',
                    last_name='Admin',
                    email='admin@test.com',
                    password='Admin123!@#',
                    user_type='admin',
                    user_id='ADMIN001',
                    is_active=True,
                    is_staff=True,
                    is_superuser=True
                )
                
                self.stdout.write(self.style.SUCCESS('Test users created successfully!'))
                self.stdout.write(f'Payer: user_id=TEST001, email=testpayer@example.com, password=Test123!@#')
                self.stdout.write(f'Admin: email=admin@test.com, password=Admin123!@#')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating test users: {str(e)}'))

    def list_users(self):
        """List all users and their status"""
        users = User.objects.all()
        
        if not users:
            self.stdout.write(self.style.WARNING('No users found in database.'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Found {users.count()} users:'))
        self.stdout.write('-' * 80)
        
        for user in users:
            status = 'ACTIVE' if user.is_active else 'INACTIVE'
            user_type = user.user_type.upper()
            
            self.stdout.write(f'ID: {user.id} | {user_type} | {status}')
            self.stdout.write(f'  Username: {user.username}')
            self.stdout.write(f'  Email: {user.email}')
            self.stdout.write(f'  User ID: {user.user_id}')
            self.stdout.write(f'  Name: {user.first_name} {user.last_name}')
            self.stdout.write(f'  Staff: {user.is_staff} | Superuser: {user.is_superuser}')
            self.stdout.write('-' * 80)

    def activate_user(self, identifier):
        """Activate a user by email or user_id"""
        try:
            # Try to find user by email first, then by user_id
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(user_id=identifier)
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'User not found: {identifier}'))
                    return
            
            user.is_active = True
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'User activated: {user.email} ({user.user_id})'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error activating user: {str(e)}'))

    def reset_password(self, identifier):
        """Reset password for a user"""
        try:
            # Try to find user by email first, then by user_id
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(user_id=identifier)
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'User not found: {identifier}'))
                    return
            
            new_password = 'TempPass123!@#'
            user.set_password(new_password)
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'Password reset for: {user.email} ({user.user_id})'))
            self.stdout.write(f'New password: {new_password}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error resetting password: {str(e)}'))
