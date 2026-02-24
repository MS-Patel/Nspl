import os
import logging
from apps.reconciliation.parsers import CAMSXLSParser, KarvyXLSParser, CAMSParser, KarvyParser, DBFParser

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

    # Excel Files
    elif filename.lower().endswith('.xls') or filename.lower().endswith('.xlsx'):
        if 'WBR2' in filename:
            logger.info(f"Detected CAMS WBR2: {filename}")
            parser = CAMSXLSParser(file_path=file_path)
        elif 'MFSD201' in filename:
            logger.info(f"Detected Karvy MFSD201: {filename}")
            parser = KarvyXLSParser(file_path=file_path)
        else:
             # Basic fallback logic if filename isn't explicit but content might be?
             # For now, sticking to filename convention as per original code.
             pass

    # Text/CSV Files
    elif filename.lower().endswith('.txt') or filename.lower().endswith('.csv'):
        # Skip known payout files
        if 'payout' in filename.lower():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                header = f.readline()
                if 'HED' in header or 'TRL' in header:
                    logger.info(f"Detected CAMS Text: {filename}")
                    parser = CAMSParser(file_path=file_path)
                elif '|' in header and len(header.split('|')) > 5:
                    # Default to Karvy for pipe delimited as per original logic
                    logger.info(f"Detected Karvy/Franklin Text: {filename}")
                    parser = KarvyParser(file_path=file_path)
        except Exception as e:
            logger.debug(f"Error checking file header: {e}")

    return parser
