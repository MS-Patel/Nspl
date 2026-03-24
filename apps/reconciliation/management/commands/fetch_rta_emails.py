import logging
import os
from django.core.management.base import BaseCommand
from django.core.files import File
from apps.reconciliation.utils.email_fetcher import RTAEmailFetcher
from apps.reconciliation.utils.parser_registry import get_parser_for_file
from apps.reconciliation.models import RTAFile
from apps.reconciliation.parsers import DBFParser, KarvyCSVParser, FranklinParser
from django.conf import settings
from apps.administration.models import SystemConfiguration

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches RTA transaction reports from email and imports them.'

    def handle(self, *args, **options):
        config = SystemConfiguration.get_solo()
        # Basic check to avoid error if settings not present
        host = config.rta_email_host or getattr(settings, 'RTA_EMAIL_HOST', None)
        user = config.rta_email_user or getattr(settings, 'RTA_EMAIL_USER', None)
        if not host or not user:
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

                for email_id, file_items in emails:
                    email_success = True
                    processed_count = 0

                    if not file_items:
                        self.stdout.write(f"Email {email_id} had no valid attachments.")
                        continue

                    for item in file_items:
                        file_path = item.get('path')
                        source = item.get('source', 'Unknown Source')

                        try:
                            parser = get_parser_for_file(file_path)
                            if not parser:
                                # Not a recognized RTA file
                                self.stdout.write(f"Skipping unknown file: {file_path} from {source}")

                                # Log first 100 bytes to help debug (e.g. check if it's HTML error page)
                                try:
                                    with open(file_path, 'rb') as f:
                                        content_sample = f.read(100)
                                        self.stdout.write(f"File Header Sample: {content_sample}")
                                except Exception as e:
                                    self.stdout.write(f"Could not read file sample: {e}")

                                continue

                            rta_type = None
                            if isinstance(parser, DBFParser):
                                rta_type = RTAFile.RTA_CAMS
                            elif isinstance(parser, KarvyCSVParser):
                                rta_type = RTAFile.RTA_KARVY
                            elif isinstance(parser, FranklinParser):
                                rta_type = RTAFile.RTA_FRANKLIN

                            if not rta_type:
                                self.stdout.write(f"Skipping file with unknown RTA type: {file_path}")
                                continue

                            filename = os.path.basename(file_path)
                            rta_file_obj = None

                            try:
                                with open(file_path, 'rb') as f:
                                    rta_file_obj = RTAFile.objects.create(
                                        rta_type=rta_type,
                                        file_name=filename,
                                        status=RTAFile.STATUS_PENDING
                                    )
                                    rta_file_obj.file.save(filename, File(f))

                                parser.rta_file = rta_file_obj

                                self.stdout.write(f"Processing file: {file_path} from {source}")
                                parser.parse()
                                self.stdout.write(self.style.SUCCESS(f"Successfully processed {file_path}"))
                                processed_count += 1
                            except Exception as e:
                                if rta_file_obj:
                                    rta_file_obj.status = RTAFile.STATUS_FAILED
                                    rta_file_obj.error_log = str(e)
                                    rta_file_obj.save()
                                raise e

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
