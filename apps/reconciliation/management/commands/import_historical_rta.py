import os
import logging
from django.core.management.base import BaseCommand
from django.core.files import File
from apps.reconciliation.utils.parser_registry import get_parser_for_file
from apps.reconciliation.models import RTAFile
from apps.reconciliation.parsers import DBFParser, KarvyCSVParser, FranklinParser

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports historical transactions from RTA files (CAMS WBR2 / Karvy MFSD201) in docs/rta.'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, default='docs/rta', help='Path to RTA files directory')

    def handle(self, *args, **options):
        path = options['path']
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"Path does not exist: {path}"))
            return

        self.stdout.write(f"Scanning {path} for RTA files...")

        count = 0
        processed_files = 0
        for root, dirs, files in os.walk(path):
            for filename in files:
                file_path = os.path.join(root, filename)
                parser = None

                try:
                    parser = get_parser_for_file(file_path)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error identifying parser for {filename}: {e}"))
                    continue

                if parser:
                    rta_type = None
                    if isinstance(parser, DBFParser):
                        rta_type = RTAFile.RTA_CAMS
                    elif isinstance(parser, KarvyCSVParser):
                        rta_type = RTAFile.RTA_KARVY
                    elif isinstance(parser, FranklinParser):
                        rta_type = RTAFile.RTA_FRANKLIN

                    if not rta_type:
                        self.stdout.write(self.style.ERROR(f"Could not determine rta_type for {filename}"))
                        continue

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

                        self.stdout.write(f"Processing {filename}...")
                        parser.parse()
                        self.stdout.write(self.style.SUCCESS(f"Successfully processed {filename}"))
                        processed_files += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to process {filename}: {e}"))
                        if rta_file_obj:
                            rta_file_obj.status = RTAFile.STATUS_FAILED
                            rta_file_obj.error_log = str(e)
                            rta_file_obj.save()
                        logger.exception(e)

                count += 1

        if processed_files == 0:
             self.stdout.write(self.style.WARNING(f"No valid transaction files processed in {path}."))
        else:
             self.stdout.write(self.style.SUCCESS(f"Import Complete. Processed {processed_files} files."))
