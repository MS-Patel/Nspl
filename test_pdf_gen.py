from django.conf import settings
import os
import django

# Setup barebones django for testing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.reports.services.pdf_generator import BaseReportGenerator
print("Import successful!")
