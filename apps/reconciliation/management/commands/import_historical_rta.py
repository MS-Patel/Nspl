import os
import logging
from django.core.management.base import BaseCommand
from apps.reconciliation.parsers import CAMSXLSParser, KarvyXLSParser, CAMSParser, KarvyParser

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

                # Identification Logic
                if filename.lower().endswith('.xls') or filename.lower().endswith('.xlsx'):
                    if 'WBR2' in filename:
                        self.stdout.write(f"Detected CAMS WBR2: {filename}")
                        parser = CAMSXLSParser(file_path=file_path)
                    elif 'MFSD201' in filename:
                        self.stdout.write(f"Detected Karvy MFSD201: {filename}")
                        parser = KarvyXLSParser(file_path=file_path)
                    else:
                        # Log but don't count as failure
                        # self.stdout.write(f"Skipping unknown Excel file: {filename}")
                        continue

                # Fallback for text files if any (Standard WBR9 or Karvy Mailback)
                elif filename.lower().endswith('.txt') or filename.lower().endswith('.csv'):
                    # Basic content check
                    # Skip known payout files
                    if 'payout' in filename.lower():
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            header = f.readline()
                            if 'HED' in header or 'TRL' in header:
                                self.stdout.write(f"Detected CAMS Text: {filename}")
                                parser = CAMSParser(file_path=file_path)
                            elif '|' in header and len(header.split('|')) > 5:
                                self.stdout.write(f"Detected Karvy/Franklin Text: {filename}")
                                parser = KarvyParser(file_path=file_path) # Default to Karvy for pipe
                    except Exception as e:
                        pass

                if parser:
                    try:
                        self.stdout.write(f"Processing {filename}...")
                        parser.parse()
                        self.stdout.write(self.style.SUCCESS(f"Successfully processed {filename}"))
                        processed_files += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to process {filename}: {e}"))
                        logger.exception(e)

                count += 1

        if processed_files == 0:
             self.stdout.write(self.style.WARNING(f"No valid transaction files processed in {path}."))
        else:
             self.stdout.write(self.style.SUCCESS(f"Import Complete. Processed {processed_files} files."))
