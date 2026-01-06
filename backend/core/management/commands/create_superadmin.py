"""
Management command to create a superadmin user.

Usage:
    python manage.py create_superadmin
"""

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from core.models import User
import getpass


class Command(BaseCommand):
    help = 'Create a superadmin user with platform access'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address for the superadmin',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the superadmin',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Run without prompting for input',
        )

    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')
        noinput = options.get('noinput', False)

        # Interactive mode if no email provided
        if not email and not noinput:
            email = input('Email address: ').strip()
        
        if not email:
            self.stdout.write(self.style.ERROR('Email is required'))
            return

        # Validate email format
        if '@' not in email:
            self.stdout.write(self.style.ERROR('Invalid email format'))
            return

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'User with email {email} already exists')
            )
            return

        # Interactive mode for password if not provided
        if not password and not noinput:
            password = getpass.getpass('Password: ')
            password_confirm = getpass.getpass('Password (again): ')
            
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match'))
                return
        
        if not password:
            self.stdout.write(self.style.ERROR('Password is required'))
            return

        # Validate password length
        if len(password) < 8:
            self.stdout.write(
                self.style.ERROR('Password must be at least 8 characters long')
            )
            return

        try:
            # Create superadmin user
            user = User.objects.create_user(
                email=email,
                password=password,
            )
            
            # Set superadmin role and no church association
            user.role = User.Role.SUPERADMIN
            user.church = None
            user.is_staff = True  # Allow Django admin access
            user.is_active = True
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created superadmin: {email}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '\nSuperadmin Details:'
                )
            )
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Role: {user.role}')
            self.stdout.write(f'  Church: None (Platform access)')
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  Store credentials securely!'
                )
            )

        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'Database error: {e}')
            )
        except ValidationError as e:
            self.stdout.write(
                self.style.ERROR(f'Validation error: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Unexpected error: {e}')
            )
