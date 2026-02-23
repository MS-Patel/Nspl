import pytest
from unittest.mock import MagicMock, patch, ANY, call
from datetime import datetime, timedelta
from django.conf import settings
from apps.reconciliation.utils.email_fetcher import RTAEmailFetcher
import zipfile
import pyzipper
import io
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

@patch('apps.reconciliation.utils.email_fetcher.imaplib.IMAP4_SSL')
def test_fetch_emails_search_criteria(mock_imap):
    # Setup
    mock_conn = MagicMock()
    mock_imap.return_value = mock_conn

    # Mock search return
    mock_conn.search.return_value = ('OK', [b'']) # No emails found, but search command sent

    # Mock settings
    with patch.object(settings, 'RTA_EMAIL_FETCH_DAYS', 7, create=True), \
         patch.object(settings, 'RTA_EMAIL_HOST', 'imap.test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_USER', 'test@test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_PASSWORD', 'password', create=True):

        fetcher = RTAEmailFetcher()
        fetcher.connect()
        fetcher.fetch_emails()

        # Calculate expected date
        expected_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
        expected_criteria = f'(UNSEEN SINCE "{expected_date}")'

        # Verify search called with correct criteria
        mock_conn.search.assert_called_with(None, expected_criteria)

@patch('apps.reconciliation.utils.email_fetcher.imaplib.IMAP4_SSL')
def test_fetch_emails_search_criteria_custom_days(mock_imap):
    # Setup
    mock_conn = MagicMock()
    mock_imap.return_value = mock_conn
    mock_conn.search.return_value = ('OK', [b''])

    # Mock settings
    with patch.object(settings, 'RTA_EMAIL_FETCH_DAYS', 3, create=True), \
         patch.object(settings, 'RTA_EMAIL_HOST', 'imap.test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_USER', 'test@test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_PASSWORD', 'password', create=True):

        fetcher = RTAEmailFetcher()
        fetcher.connect()
        fetcher.fetch_emails()

        # Calculate expected date
        expected_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
        expected_criteria = f'(UNSEEN SINCE "{expected_date}")'

        # Verify search called with correct criteria
        mock_conn.search.assert_called_with(None, expected_criteria)

@patch('apps.reconciliation.utils.email_fetcher.requests.get')
@patch('apps.reconciliation.utils.email_fetcher.imaplib.IMAP4_SSL')
def test_fetch_emails_with_cams_link(mock_imap, mock_get):
    # Setup IMAP mock
    mock_conn = MagicMock()
    mock_imap.return_value = mock_conn

    # Mock search result with one email ID
    mock_conn.search.return_value = ('OK', [b'123'])

    # Mock fetch result with HTML content containing CAMS link
    cams_html = """
    <html>
        <body>
            <table>
                <tr>
                    <td>DownloadURL</td>
                    <td><a href="https://mailback12.camsonline.com/mailback_result/testfile.zip">Click here</a></td>
                </tr>
            </table>
        </body>
    </html>
    """

    # Construct a multipart email message
    msg = MIMEMultipart()
    msg['From'] = 'donotreply@camsonline.com'
    msg['Subject'] = 'WBR2 Report'
    msg.attach(MIMEText(cams_html, 'html'))

    # Mock fetch return value
    mock_conn.fetch.return_value = ('OK', [(b'123 (RFC822 {123}', msg.as_bytes())])

    # Mock requests.get response (ZIP file download)
    mock_response = MagicMock()
    mock_response.status_code = 200

    # Create a valid dummy zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr('test_cams_data.csv', 'dummy data')
    zip_content = zip_buffer.getvalue()

    mock_response.iter_content = MagicMock(return_value=[zip_content])
    mock_response.headers = {'Content-Disposition': 'attachment; filename="testfile.zip"'}
    mock_get.return_value = mock_response

    # Mock settings
    with patch.object(settings, 'RTA_EMAIL_FETCH_DAYS', 7, create=True), \
         patch.object(settings, 'RTA_EMAIL_HOST', 'imap.test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_USER', 'test@test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_PASSWORD', 'password', create=True), \
         patch.object(settings, 'RTA_EMAIL_SENDER_FILTERS', ['camsonline.com'], create=True), \
         patch.object(settings, 'RTA_EMAIL_SUBJECT_FILTERS', [], create=True), \
         patch.object(settings, 'RTA_FILE_PASSWORD', [], create=True):

        fetcher = RTAEmailFetcher()
        fetcher.connect()
        results = fetcher.fetch_emails()

        # Assertions
        assert len(results) == 1
        email_id, files = results[0]
        assert email_id == b'123'
        assert len(files) == 1
        assert 'test_cams_data.csv' in files[0] # Should be the extracted file

        # Verify requests.get was called correctly
        mock_get.assert_called_with('https://mailback12.camsonline.com/mailback_result/testfile.zip', stream=True, timeout=30)


@patch('apps.reconciliation.utils.email_fetcher.requests.get')
@patch('apps.reconciliation.utils.email_fetcher.imaplib.IMAP4_SSL')
def test_fetch_emails_with_karvy_link(mock_imap, mock_get):
    # Setup IMAP mock
    mock_conn = MagicMock()
    mock_imap.return_value = mock_conn

    # Mock search result with one email ID
    mock_conn.search.return_value = ('OK', [b'456'])

    # Mock fetch result with HTML content containing Karvy link
    karvy_html = """
    <html>
        <body>
            <a href="https://scdelivery.kfintech.com/c/?u=xyz"><b> Click Here</b></a> to download the report.
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = 'distributorcare@kfintech.com'
    msg['Subject'] = 'Transaction Feeds Report'
    msg.attach(MIMEText(karvy_html, 'html'))

    mock_conn.fetch.return_value = ('OK', [(b'456 (RFC822 {123}', msg.as_bytes())])

    # Mock requests.get response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_content = MagicMock(return_value=[b'csv_data_content'])
    # Karvy usually sends filename in Content-Disposition
    mock_response.headers = {'Content-Disposition': 'attachment; filename="karvy_report.csv"'}
    mock_get.return_value = mock_response

    # Mock settings
    with patch.object(settings, 'RTA_EMAIL_FETCH_DAYS', 7, create=True), \
         patch.object(settings, 'RTA_EMAIL_HOST', 'imap.test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_USER', 'test@test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_PASSWORD', 'password', create=True), \
         patch.object(settings, 'RTA_EMAIL_SENDER_FILTERS', ['kfintech.com'], create=True), \
         patch.object(settings, 'RTA_EMAIL_SUBJECT_FILTERS', [], create=True), \
         patch.object(settings, 'RTA_FILE_PASSWORD', [], create=True):

        fetcher = RTAEmailFetcher()
        fetcher.connect()
        results = fetcher.fetch_emails()

        # Assertions
        assert len(results) == 1
        email_id, files = results[0]
        assert email_id == b'456'
        assert len(files) == 1
        assert 'karvy_report.csv' in files[0]

        mock_get.assert_called_with('https://scdelivery.kfintech.com/c/?u=xyz', stream=True, timeout=30)

@patch('apps.reconciliation.utils.email_fetcher.requests.get')
@patch('apps.reconciliation.utils.email_fetcher.imaplib.IMAP4_SSL')
def test_fetch_emails_with_aes_encrypted_zip(mock_imap, mock_get):
    # Setup IMAP mock
    mock_conn = MagicMock()
    mock_imap.return_value = mock_conn

    # Mock search result with one email ID
    mock_conn.search.return_value = ('OK', [b'789'])

    # Mock fetch result with HTML content containing CAMS link (or any link/attachment)
    html_content = """
    <html>
        <body>
            <table>
                <tr>
                    <td>DownloadURL</td>
                    <td><a href="https://mailback12.camsonline.com/mailback_result/encrypted.zip">Click here</a></td>
                </tr>
            </table>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = 'donotreply@camsonline.com'
    msg['Subject'] = 'Encrypted Report'
    msg.attach(MIMEText(html_content, 'html'))

    mock_conn.fetch.return_value = ('OK', [(b'789 (RFC822 {123}', msg.as_bytes())])

    # Mock requests.get response
    mock_response = MagicMock()
    mock_response.status_code = 200

    # Create an AES encrypted zip file in memory
    zip_buffer = io.BytesIO()
    password = b'secret'
    # Use ZIP_LZMA or ZIP_DEFLATED, but with AES encryption
    with pyzipper.AESZipFile(zip_buffer, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password)
        zf.writestr('encrypted_data.csv', 'secret data')
    zip_content = zip_buffer.getvalue()

    mock_response.iter_content = MagicMock(return_value=[zip_content])
    mock_response.headers = {'Content-Disposition': 'attachment; filename="encrypted.zip"'}
    mock_get.return_value = mock_response

    # Mock settings with password
    with patch.object(settings, 'RTA_EMAIL_FETCH_DAYS', 7, create=True), \
         patch.object(settings, 'RTA_EMAIL_HOST', 'imap.test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_USER', 'test@test.com', create=True), \
         patch.object(settings, 'RTA_EMAIL_PASSWORD', 'password', create=True), \
         patch.object(settings, 'RTA_EMAIL_SENDER_FILTERS', ['camsonline.com'], create=True), \
         patch.object(settings, 'RTA_EMAIL_SUBJECT_FILTERS', [], create=True), \
         patch.object(settings, 'RTA_FILE_PASSWORD', ['wrong_pass', 'secret'], create=True):

        fetcher = RTAEmailFetcher()
        fetcher.connect()
        results = fetcher.fetch_emails()

        # Assertions
        assert len(results) == 1
        email_id, files = results[0]
        assert email_id == b'789'
        assert len(files) == 1
        assert 'encrypted_data.csv' in files[0] # Should be the extracted file
