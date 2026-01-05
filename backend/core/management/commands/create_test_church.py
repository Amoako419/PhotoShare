"""
Django management command to create test data for development.

Creates a test church with a simple church code for testing the signup flow.
"""

from django.core.management.base import BaseCommand
from tenants.models import Church


class Command(BaseCommand):
    help = 'Create test church for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--church-code',
            type=str,
            default='TEST123',
            help='Church code to create (default: TEST123)'
        )
        parser.add_argument(
            '--church-name',
            type=str,
            default='Test Church',
            help='Church name (default: Test Church)'
        )

    def handle(self, *args, **options):
        church_code = options['church_code']
        church_name = options['church_name']
        
        # Check if church already exists
        if Church.objects.filter(church_code=church_code).exists():
            self.stdout.write(
                self.style.WARNING(f'Church with code "{church_code}" already exists')
            )
            return
        
        # Create the test church
        church = Church.objects.create(
            name=church_name,
            church_code=church_code
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created test church:\n'
                f'  Name: {church.name}\n'
                f'  Code: {church.church_code}\n'
                f'  ID: {church.id}'
            )
        )
        
        self.stdout.write('\nYou can now test the signup flow with church code: ' + church_code)