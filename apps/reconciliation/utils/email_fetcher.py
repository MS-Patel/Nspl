import imaplib
import email
import os
import logging
import pyzipper
import shutil
import tempfile
import requests
import urllib.parse
import re
import mimetypes
from bs4 import BeautifulSoup
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

        self.file_passwords = getattr(settings, 'RTA_FILE_PASSWORD', [])
        if isinstance(self.file_passwords, str):
            self.file_passwords = [self.file_passwords]

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
        Returns a list of tuples: (email_id, [list_of_file_dicts])
        Each dict has 'path' and 'source' (URL or 'Attachment: <name>')
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
                    file_items = self.process_attachments(msg)

                    # Process Links (CAMS/Karvy)
                    link_files = self.process_links(msg)
                    file_items.extend(link_files)

                    if file_items:
                        results.append((num, file_items))

                except Exception as e:
                    logger.error(f"Error processing email {num}: {e}")

            return results
        except Exception as e:
            logger.error(f"Error during fetch_emails: {e}")
            return []

    def process_attachments(self, msg):
        saved_items = []
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

            source_info = f"Attachment: {filename}"
            # Handle ZIP
            if filename.lower().endswith('.zip'):
                extracted = self.extract_zip(filepath)
                for f in extracted:
                    saved_items.append({'path': f, 'source': source_info})
            else:
                saved_items.append({'path': filepath, 'source': source_info})

        return saved_items

    def process_links(self, msg):
        """
        Parses email body for CAMS and Karvy download links.
        """
        saved_items = []
        html_content = ""

        # Extract HTML content
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_content = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                        break
        else:
            if msg.get_content_type() == "text/html":
                payload = msg.get_payload(decode=True)
                if payload:
                    html_content = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')

        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. CAMS: Look for "DownloadURL" in a table cell
        # "DownloadURL" in the table cell preceding the link.
        cams_links = []
        download_cells = soup.find_all(string=re.compile("DownloadURL", re.IGNORECASE))
        for cell in download_cells:
            # The cell is a NavigableString, parent is the <td>
            parent_td = cell.parent
            if parent_td and parent_td.name == 'td':
                 # Look for next sibling td
                next_td = parent_td.find_next_sibling('td')
                if next_td:
                    link = next_td.find('a', href=True)
                    if link and 'camsonline.com' in link['href']:
                        cams_links.append(link['href'])

        # 2. Karvy: Look for "Click Here" link before "to download"
        # "click here link before to download transaction report word"
        karvy_links = []
        click_here_links = soup.find_all('a', string=re.compile("Click Here", re.IGNORECASE))
        for link in click_here_links:
            if 'href' in link.attrs and 'kfintech.com' in link['href']:
                # Check context if needed, but domain filter + "Click Here" is strong signal
                # Checking next text node for "download" as requested
                next_node = link.next_sibling
                if next_node and "download" in str(next_node).lower():
                     karvy_links.append(link['href'])
                else:
                    # Sometimes markup might be nested, let's be lenient if domain matches and text is "Click Here"
                     karvy_links.append(link['href'])

        # Deduplicate
        all_links = list(set(cams_links + karvy_links))

        for url in all_links:
            try:
                filepath = self.download_file(url)
                if filepath:
                    if filepath.lower().endswith('.zip'):
                        extracted = self.extract_zip(filepath)
                        for f in extracted:
                            saved_items.append({'path': f, 'source': url})
                    else:
                        saved_items.append({'path': filepath, 'source': url})
            except Exception as e:
                logger.error(f"Error downloading file from {url}: {e}")

        return saved_items

    def download_file(self, url):
        try:
            logger.info(f"Downloading file from {url}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            filename = None
            if "Content-Disposition" in response.headers:
                content_disposition = response.headers["Content-Disposition"]
                filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if filename_match:
                    filename = filename_match.group(1)

            # Fallback 1: Try guessing from Content-Type if filename missing or generic
            content_type = response.headers.get('Content-Type', '')

            if not filename:
                # Fallback 2: URL path
                path = urllib.parse.urlparse(url).path
                filename = os.path.basename(path)

            if not filename or filename == '':
                # Last resort
                filename = f"downloaded_file_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Sanitize filename
            filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in '._- ']).strip()

            # Append extension if missing, based on content-type
            root, ext = os.path.splitext(filename)
            if not ext and content_type:
                 guess_ext = mimetypes.guess_extension(content_type.split(';')[0].strip())
                 if guess_ext:
                     filename = f"{filename}{guess_ext}"

            filepath = os.path.join(self.temp_dir, filename)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Post-processing: Magic Byte detection if extension is missing or generic
            # Re-check extension
            root, ext = os.path.splitext(filepath)

            # Skip checking if we already have a trusted extension like .csv or .txt
            # to avoid false positives with DBF magic bytes (like 'c' for 0x63)
            if ext.lower() in ['.csv', '.txt', '.log']:
                 return filepath

            try:
                with open(filepath, 'rb') as f:
                    header = f.read(4)

                new_ext = None
                if header.startswith(b'PK\x03\x04'):
                    new_ext = '.zip'
                # DBF header checks: 0x03 (dBase III), 0x30 (VFP), 0x83 (dBase III+), 0xF5 (FoxPro)
                # Removed 0x63 ('c'), 0x43 ('C') to avoid conflict with CSV/text
                elif header and header[0] in [0x03, 0x30, 0x31, 0x32, 0x83, 0x8B, 0xCB, 0xF5]:
                     new_ext = '.dbf'

                if new_ext:
                    if not ext or ext.lower() != new_ext:
                        new_filepath = f"{root}{new_ext}"
                        # Ensure uniqueness if file exists
                        if os.path.exists(new_filepath):
                            timestamp = datetime.now().strftime('%H%M%S')
                            new_filepath = f"{root}_{timestamp}{new_ext}"

                        os.rename(filepath, new_filepath)
                        logger.info(f"Renamed {filepath} to {new_filepath} based on content detection.")
                        filepath = new_filepath

            except Exception as e:
                logger.warning(f"Failed to inspect file magic bytes for {filepath}: {e}")

            logger.info(f"Downloaded to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    def extract_zip(self, zip_path):
        extracted_files = []
        try:
            with pyzipper.AESZipFile(zip_path, 'r') as zf:
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
                    except (RuntimeError, pyzipper.BadZipFile, pyzipper.LargeZipFile) as e:
                        if pwd is None:
                            logger.info(f"Extraction failed without password for {zip_path}: {e}")
                        else:
                            logger.warning(f"Extraction failed with provided password for {zip_path}: {e}")

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
