import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.integration.bse_client import BSEStarMFClient
client = BSEStarMFClient()
print("Method:", client._get_query_soap_client)
