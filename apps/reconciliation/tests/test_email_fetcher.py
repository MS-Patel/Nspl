import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from django.conf import settings
from apps.reconciliation.utils.email_fetcher import RTAEmailFetcher

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
