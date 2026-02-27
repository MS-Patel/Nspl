import os
import logging
from apps.reconciliation.parsers import KarvyXLSParser, KarvyParser, DBFParser, KarvyMFSD307Parser

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
        if 'MFSD307' in filename:
            logger.info(f"Detected Karvy MFSD307: {filename}")
            parser = KarvyMFSD307Parser(file_path=file_path)

        # If not matched by filename, try content inspection
        if not parser:
            # Skip known payout files
            if 'payout' in filename.lower():
                return None

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    header = f.readline()
                    # Removed CAMS text detection
                    if '|' in header and len(header.split('|')) > 5:
                        # Default to Karvy for pipe delimited as per original logic
                        logger.info(f"Detected Karvy/Franklin Text: {filename}")
                        parser = KarvyParser(file_path=file_path)
            except Exception as e:
                logger.debug(f"Error checking file header: {e}")

    # Text Files
    elif filename.lower().endswith('.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                header = f.readline()
                # Removed CAMS text detection
                if '|' in header and len(header.split('|')) > 5:
                    logger.info(f"Detected Karvy/Franklin Text: {filename}")
                    parser = KarvyParser(file_path=file_path)
        except Exception as e:
            logger.debug(f"Error checking file header: {e}")

    return parser
