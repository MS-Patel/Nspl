from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from apps.core.utils.email import get_system_email_connection
from apps.administration.models import SystemConfiguration

User = get_user_model()

class Command(BaseCommand):
    help = 'Sends a scheduled maintenance email to all users.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--downtime',
            type=str,
            default='approximately 2 hours',
            help='Expected duration of the downtime (e.g. "2 hours")'
        )
        parser.add_argument(
            '--date',
            type=str,
            default='Tonight at 10:00 PM',
            help='When the maintenance will occur (e.g. "Tomorrow at 1:00 AM")'
        )
        parser.add_argument(
            '--reason',
            type=str,
            default='Routine system upgrades and database maintenance',
            help='Reason for the downtime'
        )
        parser.add_argument(
            '--test',
            type=str,
            help='Send only to this specific email address for testing',
            default=None
        )

    def handle(self, *args, **options):
        downtime = options['downtime']
        date = options['date']
        reason = options['reason']
        test_email = options['test']

        if test_email:
            # For testing purposes, send to a single email without creating user records
            emails = [test_email]
            self.stdout.write(f"Test mode activated. Will only send to: {test_email}")
        else:
            # Query all non-superusers that have a valid email address
            users = User.objects.filter(is_superuser=False).exclude(email__isnull=True).exclude(email__exact='')

            emails = list(users.values_list('email', flat=True))

            # Remove empty strings and duplicates, just in case
            emails = list(set([e for e in emails if e.strip()]))

            self.stdout.write(f"Found {len(emails)} users to notify.")

            if not emails:
                self.stdout.write(self.style.WARNING("No users found with valid email addresses. Exiting."))
                return

        context = {
            'downtime': downtime,
            'date': date,
            'reason': reason
        }

        subject = 'Scheduled Maintenance Notification - Buybestfin'

        # Render the HTML template
        html_message = render_to_string('emails/maintenance_notification.html', context)
        # Create a plain text version for email clients that don't support HTML
        plain_message = strip_tags(html_message)

        # Get the email connection
        connection = get_system_email_connection()
        config = SystemConfiguration.get_solo()
        from_email = config.default_from_email

        self.stdout.write("Preparing emails...")

        messages = []
        for email_address in emails:
            # Build an EmailMultiAlternatives object for each user
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[email_address]
            )
            msg.attach_alternative(html_message, "text/html")
            messages.append(msg)

        self.stdout.write("Sending emails...")

        try:
            # Send all messages through the single connection
            # fail_silently=False so we can catch exceptions if connection fails
            num_sent = connection.send_messages(messages)
            self.stdout.write(self.style.SUCCESS(f"Successfully sent {num_sent} maintenance notification emails."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send emails: {str(e)}"))
