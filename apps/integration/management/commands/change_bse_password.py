import re
from django.core.management.base import BaseCommand, CommandError
from apps.integration.bse_client import BSEStarMFClient
from django.conf import settings

class Command(BaseCommand):
    help = 'Changes the BSE API password using the BSE MFAPI (Flag 04).'

    def add_arguments(self, parser):
        parser.add_argument('new_password', type=str, help='The new password to set. Min 6, Max 14 chars, alphanumeric with one special character.')

    def validate_password(self, password):
        if len(password) < 6:
            raise CommandError("Password must be at least 6 characters long.")
        if len(password) > 14:
            raise CommandError("Password must be a maximum of 14 characters long.")

        # Check alphanumeric + at least one special character
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            raise CommandError("Password must contain both letters and numbers (alphanumeric).")

        if not re.search(r'[^A-Za-z0-9]', password):
            raise CommandError("Password must contain at least one special character.")

    def handle(self, *args, **options):
        new_password = options['new_password']
        self.validate_password(new_password)

        self.stdout.write(self.style.WARNING('Initiating BSE StarMF password change...'))

        client = BSEStarMFClient()
        result = client.change_password(new_password)

        if result.get('status') == 'success':
            self.stdout.write(self.style.SUCCESS('Successfully changed BSE StarMF password.'))
            self.stdout.write(self.style.SUCCESS(f'Remarks: {result.get("remarks")}'))
            self.stdout.write(self.style.WARNING(
                "\nIMPORTANT: Please update the 'BSE_PASSWORD' environment variable in your .env file "
                f"or deployment configuration to '{new_password}' immediately, or future API calls will fail."
            ))
        else:
            self.stdout.write(self.style.ERROR(f'Failed to change password.'))
            self.stdout.write(self.style.ERROR(f'Status: {result.get("status")}'))
            self.stdout.write(self.style.ERROR(f'Remarks: {result.get("remarks")}'))
