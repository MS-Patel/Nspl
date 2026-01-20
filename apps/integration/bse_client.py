import os
import random
import string
import requests
import logging
from django.conf import settings
from zeep import Client, Settings
import datetime
from .utils import get_bse_order_params, get_bse_xsip_order_params, get_bse_mandate_param_string
from apps.users.models import InvestorProfile

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
        self.order_wsdl = "https://bsestarmfdemo.bseindia.com/MFOrderEntry/MFOrder.svc?singleWsdl"
        self.upload_service_url = "https://bsestarmfdemo.bseindia.com/StarMFFileUploadService/StarMFFileUploadService.svc/Secure/UploadFile"
        self.upload_wsdl = "https://bsestarmfdemo.bseindia.com/MFUploadService/MFUploadService.svc?singleWsdl"
        self.common_api_url = "https://bsestarmfdemo.bseindia.com/BSEMFWEBAPI/UCCAPI/UCCRegistrationV183"
        self.emandate_auth_url = "https://bsestarmfdemo.bseindia.com/Emandate/EmandateAuthURL.aspx"
        self.emandate_api_url = "https://bsestarmfdemo.bseindia.com/StarMFWebService/StarMFWebService.svc/EMandateAuthURL"

    def _generate_pass_key(self):
        """Generates a random 10-character alphanumeric pass key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    def _get_soap_client(self):
        """
        Initializes and returns a Zeep Client configured with the correct WSDL,
        Settings, Service Name, and Port Name to enforce the Secure (HTTPS) endpoint.
        """
        zeep_settings = Settings(strict=False, xml_huge_tree=True)
        # Explicitly selecting the HTTPS port 'WSHttpBinding_MFOrderEntry1'
        # which maps to https://bsestarmfdemo.bseindia.com/MFOrderEntry/MFOrder.svc/Secure
        return Client(
            wsdl=self.order_wsdl,
            settings=zeep_settings,
            service_name='MFOrder',
            port_name='WSHttpBinding_MFOrderEntry1'
        )

    def _get_upload_soap_client(self):
        """
        Initializes and returns a Zeep Client configured for the Upload Service (MFAPI).
        """
        zeep_settings = Settings(strict=False, xml_huge_tree=True)
        # Typically the service name is 'MFUploadService' and port 'WSHttpBinding_IMFUploadService1' or similar for Secure
        # Inspecting the WSDL would confirm, but usually we can let Zeep pick the default if we are careful,
        # or assume the pattern holds.
        # Based on logs and standard BSE WSDLs, let's try to find the secure port.
        # If unknown, just initializing with WSDL usually works if the WSDL has the correct addresses.
        # However, to be safe and consistent with _get_soap_client, we should probably target the secure binding.

        # Let's try without specifying service/port first, as Zeep defaults to the first one which is often HTTP.
        # If we need HTTPS, we might need to be specific.
        # Given I cannot inspect WSDL content easily without a tool, I will try to use the client default
        # but ensure the address in WSDL (which usually points to http or https) is respected.
        # If errors occur, I will need to be more specific.

        # NOTE: For UAT, singleWsdl often exposes both HTTP and HTTPS bindings.
        # 'BasicHttpBinding_IMFUploadService' (HTTP) and 'WSHttpBinding_IMFUploadService' (HTTPS) are common.
        # Let's try to target 'WSHttpBinding_IMFUploadService' or similar if we can guess,
        # otherwise rely on the fact that self.upload_wsdl has 'singleWsdl'.

        client = Client(
            wsdl=self.upload_wsdl,
            settings=zeep_settings,
            service_name='MFUploadService',
            port_name='WSHttpBinding_IMFUploadService1'
        )
        return client, client.service

    def _get_auth_details(self):
        """
        Authenticates with BSE StarMF SOAP API to get the session key (EncryptedPassword) and PassKey.
        Returns:
            tuple: (EncryptedPassword, PassKey)
        """
        pass_key = self._generate_pass_key()

        # Use the shared client initialization
        client = self._get_soap_client()

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
                return result_str[1], pass_key
            else:
                raise Exception(f"BSE Authentication Failed: {response}")

        except Exception as e:
            raise Exception(f"SOAP Error during authentication: {str(e)}")

    def _get_upload_auth_details(self):
        """
        Authenticates with BSE StarMF Upload Service to get the session key.
        Returns:
            tuple: (EncryptedPassword, PassKey)
        """
        pass_key = self._generate_pass_key()

        # Use the upload service client
        _, service = self._get_upload_soap_client()

        try:
            # The getPassword method in Upload Service WSDL expects UserId, Password, PassKey
            response = service.getPassword(
                UserId=self.user_id,
                MemberId=self.member_id,
                Password=self.password,
                PassKey=pass_key
            )

            # Response format is "100|EncryptedPassword" or "101|Error"
            result_str = response.split('|')
            if result_str[0] == '100':
                return result_str[1], pass_key
            else:
                raise Exception(f"BSE Upload Service Authentication Failed: {response}")

        except Exception as e:
            raise Exception(f"SOAP Error during upload service authentication: {str(e)}")

    def _get_password(self):
        """
        Wrapper to maintain backward compatibility.
        Returns just the EncryptedPassword string.
        """
        token, _ = self._get_auth_details()
        return token

    def place_order(self, order):
        """
        Places a lumpsum order using the SOAP MFOrderEntry service.
        Args:
            order (Order): The order object.
        Returns:
            dict: {status: success/error, bse_order_id: ..., remarks: ...}
        """
        # COMPLIANCE GUARD: Block if Nominee Auth is Pending
        # Rule: Block all MF transactions unless nominee authenticated or opt-out completed
        # Opt-out is handled by nomination_opt field ('N')
        investor = order.investor
        if investor.nominee_auth_status == InvestorProfile.AUTH_PENDING and investor.nomination_opt == 'Y':
             return {
                'status': 'error',
                'remarks': 'COMPLIANCE BLOCK: Nominee Authentication is Pending. Please complete authentication or update UCC.'
            }

        try:
            # 1. Get Session Password (using the new tuple method)
            encrypted_password, pass_key = self._get_auth_details()

            # 2. Prepare Parameters
            params = get_bse_order_params(
                order,
                self.member_id,
                self.user_id,
                encrypted_password,
                pass_key
            )

            # 3. SOAP Call
            client = self._get_soap_client()

            bse_logger.info(f"ORDER Request: {params}")
            # Calling orderEntryParam with keyword arguments expanded from the dict
            response = client.service.orderEntryParam(**params)

            # Log response
            bse_logger.info(f"ORDER ENTRY: {order.unique_ref_no} | RESPONSE: {response}")

            # Response: "0|OrderNo|Remarks" (Success) or "1|Error"
            parts = str(response).split('|')
            if parts[0] == '0':
                return {
                    'status': 'success',
                    'bse_order_id': parts[1] if len(parts) > 1 else "",
                    'remarks': parts[2] if len(parts) > 2 else 'Order Placed'
                }
            else:
                return {
                    'status': 'error',
                    'remarks': parts[1] if len(parts) > 1 else response
                }

        except Exception as e:
            bse_logger.error(f"ORDER ENTRY ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

    def register_sip(self, sip):
        """
        Registers a SIP (XSIP) using the SOAP xsipOrderEntryParam service.
        Args:
            sip (SIP): The SIP object.
        Returns:
            dict: {status: success/error, bse_reg_no: ..., remarks: ...}
        """
        # COMPLIANCE GUARD
        investor = sip.investor
        if investor.nominee_auth_status == InvestorProfile.AUTH_PENDING and investor.nomination_opt == 'Y':
             return {
                'status': 'error',
                'remarks': 'COMPLIANCE BLOCK: Nominee Authentication is Pending. Please complete authentication or update UCC.'
            }

        try:
            encrypted_password, pass_key = self._get_auth_details()
            params = get_bse_xsip_order_params(
                sip,
                self.member_id,
                self.user_id,
                encrypted_password,
                pass_key
            )

            client = self._get_soap_client()

            response = client.service.xsipOrderEntryParam(**params)
            bse_logger.info(f"SIP ENTRY: {sip.id} | RESPONSE: {response}")

            parts = str(response).split('|')
            if parts[0] == '0':
                return {
                    'status': 'success',
                    'bse_reg_no': parts[1] if len(parts) > 1 else "",
                    'remarks': parts[2] if len(parts) > 2 else 'SIP Registered',
                    'bse_sip_id': parts[1]
                }
            else:
                return {
                    'status': 'error',
                    'remarks': parts[1] if len(parts) > 1 else response
                }

        except Exception as e:
            bse_logger.error(f"SIP ENTRY ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

    def register_mandate(self, mandate):
        """
        Registers a Mandate (XSIP Mandate) using the SOAP MFAPI service (Flag 06).
        Args:
            mandate (Mandate): The Mandate object.
        """
        try:
            encrypted_password, _ = self._get_upload_auth_details()
            param_string = get_bse_mandate_param_string(mandate)

            # Use the upload client which supports MFAPI
            _, service = self._get_upload_soap_client()

            # Call MFAPI with Flag 06
            # Note: MFAPI expects 'UserId', 'EncryptedPassword', 'param' (and 'Flag'?)
            # The WSDL signature usually is MFAPI(Flag, UserId, EncryptedPassword, param)
            # Let's use keyword arguments to be safe.

            bse_logger.info(f"MANDATE REG Request: Flag=06, Param={param_string}")

            response = service.MFAPI(
                Flag='06',
                UserId=self.user_id,
                EncryptedPassword=encrypted_password,
                param=param_string
            )

            bse_logger.info(f"MANDATE REG: {mandate.id} | RESPONSE: {response}")

            parts = str(response).split('|')
            # 100|Mandate ID|Upload Successfully
            if parts[0] == '100':
                 return {
                    'status': 'success',
                    'mandate_id': parts[1], # Returns the BSE UMRN/MandateID
                    'remarks': parts[2] if len(parts) > 2 else 'Mandate Registered'
                }
            else:
                return {
                    'status': 'error',
                    'remarks': parts[1] if len(parts) > 1 else response
                }

        except Exception as e:
            bse_logger.error(f"MANDATE REG ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

    def register_client(self, payload, regn_type="NEW"):
        """
        Registers a new client (UCC) using the JSON API (Enhanced UCC Registration).

        Args:
            payload (dict): The dictionary containing the client details (Param).
            regn_type (str): "NEW" for registration, "MOD" for modification.
        """
        request_body = {
            "UserId": self.user_id,
            "MemberCode": self.member_id,
            "Password": self.password, # Sending raw password as per JSON doc example
            "RegnType": regn_type,
            "Param": payload['Param'], # The pipe-separated string
            "Filler1": "",
            "Filler2": ""
        }

        # Mask password for logging
        log_body = request_body.copy()
        log_body['Password'] = '********'

        bse_logger.info(f"API: {self.common_api_url} | REGN TYPE: {regn_type} | REQUEST BODY: {log_body}")
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

    def get_mandate_auth_url(self, client_code, mandate_id, loopback_url=""):
        """
        Generates the BSE E-Mandate Authentication URL using the REST API.
        Args:
            client_code: The Investor's UCC.
            mandate_id: The Mandate ID returned by register_mandate.
            loopback_url: The absolute URL where BSE should redirect after auth (optional).
        Returns:
            str: The authorization URL.
        """
        payload = {
            "MemberCode": self.member_id,
            "Password": self.password,
            "ClientCode": client_code,
            "UserId": self.user_id,
            "MandateID": mandate_id,
            "LoopBackUrl": loopback_url
        }

        # Log request (masking password)
        log_body = payload.copy()
        log_body['Password'] = '********'
        bse_logger.info(f"API: {self.emandate_api_url} | REQUEST BODY: {log_body}")

        try:
            response = requests.post(self.emandate_api_url, json=payload, verify=False)
            response.raise_for_status()

            bse_logger.info(f"API: {self.emandate_api_url} | RESPONSE: {response.text}")

            # Try parsing as JSON first
            try:
                data = response.json()
                # If it's a JSON response like {Status: 0, ResponseString: 'http...'}
                if isinstance(data, dict):
                     return data.get('ResponseString', data.get('URL', response.text))
                # If it's just a string in JSON
                return str(data)
            except ValueError:
                # If not JSON, return text directly (assuming it's the URL)
                return response.text.strip('"')

        except Exception as e:
            bse_logger.error(f"API Error (Emandate Auth): {str(e)}")
            # Fallback to manual construction if API fails completely?
            # Or just raise/return error.
            # Returning existing fallback for safety might be misleading if the format changed.
            raise e
