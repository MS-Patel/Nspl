import logging
import threading
from django.db import connections
from apps.analytics.models import CASUpload, ExternalHolding
from apps.analytics.services.cas_parser import CASParser

logger = logging.getLogger(__name__)

def process_cas_upload(cas_upload_id, password):
    """
    Background task to process CAS Upload.
    Parses the PDF and inserts holdings using bulk_create.
    """
    try:
        # Re-fetch the object to ensure we have the latest state and fresh connection
        # We assume the ID is valid.
        cas_upload = CASUpload.objects.get(id=cas_upload_id)

        logger.info(f"Starting background processing for CASUpload {cas_upload_id}")

        # Note: cas_upload.file.path assumes local filesystem storage.
        # If using remote storage (S3), this might need adjustment (e.g. download to temp file).
        # We strictly follow the existing pattern here.
        parser = CASParser(cas_upload.file.path, password=password)
        holdings_data = parser.parse()

        # Prepare objects for bulk creation
        holdings_to_create = []
        for data in holdings_data:
            holdings_to_create.append(
                ExternalHolding(
                    cas_upload=cas_upload,
                    investor=cas_upload.investor,
                    **data
                )
            )

        # Bulk create
        if holdings_to_create:
            ExternalHolding.objects.bulk_create(holdings_to_create)
            logger.info(f"Inserted {len(holdings_to_create)} ExternalHoldings for CASUpload {cas_upload_id}")

        cas_upload.status = CASUpload.STATUS_PROCESSED
        cas_upload.save()
        logger.info(f"CASUpload {cas_upload_id} processed successfully.")

    except Exception as e:
        logger.exception(f"Error processing CASUpload {cas_upload_id}: {str(e)}")
        try:
             # Re-fetch in case connection was lost or state changed
             cas_upload = CASUpload.objects.get(id=cas_upload_id)
             cas_upload.status = CASUpload.STATUS_FAILED
             cas_upload.error_log = str(e)
             cas_upload.save()
        except Exception as db_err:
             logger.error(f"Failed to update status for CASUpload {cas_upload_id}: {str(db_err)}")

    finally:
        # Close DB connections created by this thread to prevent leaks
        connections.close_all()
