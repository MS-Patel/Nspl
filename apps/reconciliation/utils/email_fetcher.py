import imaplib
import email
import os
import logging
import zipfile
import shutil
import tempfile
from datetime import datetime, timedelta
from email.header import decode_header
from django.conf import settings

logger = logging.getLogger(__name__)

class RTAEmailFetcher:
    def __init__(self):
        self.host = settings.RTA_EMAIL_HOST
        self.port = settings.RTA_EMAIL_PORT
        self.user = settings.RTA_EMAIL_USER
        self.password = settings.RTA_EMAIL_PASSWORD
        self.sender_filters = settings.RTA_EMAIL_SENDER_FILTERS
        self.subject_filters = settings.RTA_EMAIL_SUBJECT_FILTERS
        self.file_passwords = settings.RTA_FILE_PASSWORD
        self.fetch_days = getattr(settings, 'RTA_EMAIL_FETCH_DAYS', 7)
        self.conn = None
        self.temp_dir = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        if not self.host or not self.user or not self.password:
            logger.warning("Email configuration missing. Skipping RTA Email Fetch.")
            return

        try:
            self.conn = imaplib.IMAP4_SSL(self.host, self.port)
            self.conn.login(self.user, self.password)
            logger.info(f"Connected to IMAP server {self.host} as {self.user}.")
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            raise

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            try:
                self.conn.logout()
            except:
                pass

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary directory.")

    def fetch_emails(self):
        """
        Fetches UNSEEN emails matching filters from the last N days.
        Returns a list of tuples: (email_id, [list_of_file_paths])
        """
        if not self.conn:
            # If not connected (e.g. config missing), return empty
            return []

        try:
            self.conn.select('INBOX')

            # Calculate date threshold for search
            date_threshold = (datetime.now() - timedelta(days=self.fetch_days)).strftime("%d-%b-%Y")
            search_criteria = f'(UNSEEN SINCE "{date_threshold}")'

            logger.info(f"Searching for emails with criteria: {search_criteria}")

            typ, data = self.conn.search(None, search_criteria)
            if typ != 'OK':
                logger.warning("No messages found or search failed.")
                return []

            email_ids = data[0].split()
            if not email_ids:
                return []

            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp()

            results = []

            for num in email_ids:
                try:
                    typ, msg_data = self.conn.fetch(num, '(RFC822)')
                    if typ != 'OK': continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Filter Sender
                    sender = msg.get('From', '').lower()
                    if self.sender_filters and not any(f in sender for f in self.sender_filters):
                        continue

                    # Filter Subject
                    subject_header = decode_header(msg.get('Subject', ''))[0]
                    subject = subject_header[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(subject_header[1] or 'utf-8', errors='ignore')
                    subject = subject.lower()

                    if self.subject_filters and not any(f in subject for f in self.subject_filters):
                        continue

                    logger.info(f"Processing email: {subject} from {sender}")

                    # Process Attachments
                    file_paths = self.process_attachments(msg)
                    if file_paths:
                        results.append((num, file_paths))

                except Exception as e:
                    logger.error(f"Error processing email {num}: {e}")

            return results
        except Exception as e:
            logger.error(f"Error during fetch_emails: {e}")
            return []

    def process_attachments(self, msg):
        saved_files = []
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if not filename: continue

            # Decode filename
            decoded_header = decode_header(filename)
            filename = decoded_header[0][0]
            if isinstance(filename, bytes):
                encoding = decoded_header[0][1] or 'utf-8'
                filename = filename.decode(encoding, errors='ignore')

            # sanitize filename
            filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._- ']).strip()

            filepath = os.path.join(self.temp_dir, filename)

            try:
                with open(filepath, 'wb') as f:
                    payload = part.get_payload(decode=True)
                    if payload:
                        f.write(payload)
                    else:
                        continue
            except Exception as e:
                logger.error(f"Error saving attachment {filename}: {e}")
                continue

            # Handle ZIP
            if filename.lower().endswith('.zip'):
                extracted = self.extract_zip(filepath)
                saved_files.extend(extracted)
            else:
                saved_files.append(filepath)

        return saved_files

    def extract_zip(self, zip_path):
        extracted_files = []
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Try passwords
                passwords = [None] # Try no password first
                if self.file_passwords:
                     passwords.extend([p.encode() for p in self.file_passwords])

                target_dir = os.path.dirname(zip_path)

                success = False
                for pwd in passwords:
                    try:
                        # Extract all members
                        zf.extractall(path=target_dir, pwd=pwd)

                        # Identify extracted files
                        for name in zf.namelist():
                            # Normalize path separators
                            clean_name = name.replace('/', os.sep).replace('\\', os.sep)
                            full_path = os.path.join(target_dir, clean_name)
                            if os.path.isfile(full_path):
                                extracted_files.append(full_path)
                        success = True
                        logger.info(f"Successfully extracted {zip_path}")
                        break
                    except (RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile):
                        continue

                if not success:
                    logger.error(f"Failed to extract {zip_path}: Incorrect password or unsupported encryption.")
        except Exception as e:
            logger.error(f"Error handling zip {zip_path}: {e}")

        return extracted_files

    def archive_email(self, email_id):
        if not self.conn: return

        # Move to 'Processed'
        # Check if folder exists, if not create
        try:
            self.conn.create('Processed')
        except:
            pass # Likely exists

        try:
            # Copy to Processed
            result = self.conn.copy(email_id, 'Processed')
            if result[0] == 'OK':
                # Mark as Deleted in Inbox
                self.conn.store(email_id, '+FLAGS', '\\Deleted')
                self.conn.expunge()
                logger.info(f"Moved email {email_id} to Processed.")
            else:
                logger.error(f"Failed to copy email {email_id} to Processed: {result}")
        except Exception as e:
            logger.error(f"Failed to archive email {email_id}: {e}")
