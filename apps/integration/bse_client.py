import os
import random
import string
import requests
import logging
from django.conf import settings
from zeep import Client, Settings
import datetime

# Configure a specific logger for BSE API
# propagate=False ensures these logs don't bubble up to the root Django logger
bse_logger = logging.getLogger('bse_api')
bse_logger.setLevel(logging.INFO)
bse_logger.propagate = False

# Create a file handler
file_handler = logging.FileHandler('bse_api.log')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)

# Add handler to logger (avoid adding multiple times if module is reloaded)
if not bse_logger.handlers:
    bse_logger.addHandler(file_handler)

class BSEStarMFClient:
    def __init__(self):
        self.member_id = settings.BSE_MEMBER_ID
        self.user_id = settings.BSE_USER_ID
        self.password = settings.BSE_PASSWORD

        # UAT Endpoints
        self.order_wsdl = "https://bsestarmfdemo.bseindia.com/MFOrderEntry/MFOrder.svc?wsdl"
        self.upload_service_url = "https://bsestarmfdemo.bseindia.com/StarMFFileUploadService/StarMFFileUploadService.svc/Secure/UploadFile"
        self.common_api_url = "https://bsestarmfdemo.bseindia.com/StarMFCommonAPI/ClientMaster/Registration"

    def _generate_pass_key(self):
        """Generates a random 10-character alphanumeric pass key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    def _get_password(self):
        """
        Authenticates with BSE StarMF SOAP API to get the session key (EncryptedPassword).
        """
        pass_key = self._generate_pass_key()

        # Configure Zeep client
        zeep_settings = Settings(strict=False, xml_huge_tree=True)
        client = Client(wsdl=self.order_wsdl, settings=zeep_settings)

        try:
            # The getPassword method in WSDL expects UserId, Password, PassKey
            response = client.service.getPassword(
                UserId=self.user_id,
                Password=self.password,
                PassKey=pass_key
            )

            # Response format is usually "100|EncryptedPassword" or "101|Error"
            result_str = response.split('|')
            if result_str[0] == '100':
                return result_str[1]
            else:
                raise Exception(f"BSE Authentication Failed: {response}")

        except Exception as e:
            raise Exception(f"SOAP Error during authentication: {str(e)}")

    def register_client(self, payload):
        """
        Registers a new client (UCC) using the JSON API (Enhanced UCC Registration).

        Args:
            payload (dict): The dictionary containing the client details (Param).
        """
        request_body = {
            "UserId": self.user_id,
            "MemberCode": self.member_id,
            "Password": self.password, # Sending raw password as per JSON doc example
            "RegnType": "NEW",
            "Param": payload['Param'], # The pipe-separated string
            "Filler1": "",
            "Filler2": ""
        }

        try:
            response = requests.post(self.common_api_url, json=request_body, verify=False) # verify=False for UAT often needed
            response.raise_for_status()

            # --- LOGGING REQUIREMENT: Base Response Only ---
            # We log the raw text response from the API
            bse_logger.info(f"API: {self.common_api_url} | RESPONSE: {response.text}")

            result = response.json()

            if result.get("Status") == "0":
                return {
                    "status": "success",
                    "remarks": result.get("Remarks"),
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "remarks": result.get("Remarks"),
                    "data": result
                }

        except Exception as e:
            # Also log errors to the specific file
            bse_logger.error(f"API Error: {str(e)}")
            return {
                "status": "error",
                "remarks": f"HTTP/Network Error: {str(e)}"
            }
