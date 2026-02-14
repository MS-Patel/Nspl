import logging
from django.core.management.base import BaseCommand
from apps.reconciliation.utils.email_fetcher import RTAEmailFetcher
from apps.reconciliation.utils.parser_registry import get_parser_for_file
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches RTA transaction reports from email and imports them.'

    def handle(self, *args, **options):
        # Basic check to avoid error if settings not present
        if not getattr(settings, 'RTA_EMAIL_HOST', None) or not getattr(settings, 'RTA_EMAIL_USER', None):
             self.stdout.write(self.style.WARNING("RTA Email configuration missing. Skipping."))
             return

        self.stdout.write("Connecting to Email Server...")

        try:
            with RTAEmailFetcher() as fetcher:
                emails = fetcher.fetch_emails()

                if not emails:
                    self.stdout.write("No new relevant emails found.")
                    return

                self.stdout.write(f"Found {len(emails)} emails. Processing...")

                for email_id, file_paths in emails:
                    email_success = True
                    processed_count = 0

                    if not file_paths:
                        self.stdout.write(f"Email {email_id} had no valid attachments.")
                        continue

                    for file_path in file_paths:
                        try:
                            parser = get_parser_for_file(file_path)
                            if not parser:
                                # Not a recognized RTA file
                                self.stdout.write(f"Skipping unknown file: {file_path}")
                                continue

                            self.stdout.write(f"Processing file: {file_path}")
                            parser.parse()
                            self.stdout.write(self.style.SUCCESS(f"Successfully processed {file_path}"))
                            processed_count += 1

                        except Exception as e:
                            logger.exception(f"Failed to process file {file_path}: {e}")
                            self.stdout.write(self.style.ERROR(f"Failed to process file {file_path}: {e}"))
                            email_success = False

                    if email_success and processed_count > 0:
                        fetcher.archive_email(email_id)
                        self.stdout.write(f"Archived email {email_id}")
                    elif processed_count == 0:
                        self.stdout.write(self.style.WARNING(f"Email {email_id} contained no processable RTA files."))
                        # Optionally archive if we decided it's trash?
                        # For now, leave in Inbox for manual review.
                    else:
                        self.stdout.write(self.style.WARNING(f"Email {email_id} not archived due to processing errors."))

            self.stdout.write(self.style.SUCCESS("RTA Email Fetch Complete."))

        except Exception as e:
            logger.exception(f"Fatal error in fetch_rta_emails: {e}")
            self.stdout.write(self.style.ERROR(f"Fatal error: {e}"))
