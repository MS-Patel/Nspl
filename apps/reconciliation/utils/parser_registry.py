import os
import logging
from apps.reconciliation.parsers import DBFParser, KarvyCSVParser

logger = logging.getLogger(__name__)

def get_parser_for_file(file_path):
    """
    Identifies and returns the appropriate parser instance for the given file path.
    Returns None if no matching parser is found.
    """
    filename = os.path.basename(file_path)
    parser = None

    # DBF Files
    if filename.lower().endswith('.dbf'):
        logger.info(f"Detected DBF File: {filename}")
        parser = DBFParser(file_path=file_path)

    # CSV Files
    elif filename.lower().endswith('.csv'):
        # Skip known payout files
        if 'payout' in filename.lower():
            return None
            
        logger.info(f"Detected Karvy CSV: {filename}")
        parser = KarvyCSVParser(file_path=file_path)

    return parser
