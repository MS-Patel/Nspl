import os
import random
import string
import logging
import re
import json
from django.conf import settings
from zeep import Client, Settings, Plugin
from lxml import etree
from zeep.transports import Transport

# Configure a specific logger for CVL API
cvl_logger = logging.getLogger('cvl_api')
cvl_logger.setLevel(logging.INFO)
cvl_logger.propagate = False

file_handler = logging.FileHandler('cvl_api.log')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)

if not cvl_logger.handlers:
    cvl_logger.addHandler(file_handler)

class CVLLoggingPlugin(Plugin):
    def egress(self, envelope, http_headers, operation, binding_options):
        xml = etree.tostring(envelope, pretty_print=True).decode()
        xml = self._mask_sensitive_data(xml)
        cvl_logger.info(f"CVL REQUEST XML:\n{xml}")
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        if envelope is not None:
            xml = etree.tostring(envelope, pretty_print=True).decode()
            xml = self._mask_sensitive_data(xml)
            cvl_logger.info(f"CVL RESPONSE XML:\n{xml}")
        return envelope, http_headers

    def _mask_sensitive_data(self, xml_str):
        sensitive_tags = ['password', 'passKey', 'GetPasswordResult']
        for tag in sensitive_tags:
            # Match <Tag>Content</Tag> or <ns:Tag>Content</ns:Tag>
            pattern = r'(<(?:[\w]+:)?' + tag + r'>)(.*?)(</(?:[\w]+:)?' + tag + r'>)'
            xml_str = re.sub(pattern, r'\1********\3', xml_str, flags=re.DOTALL)
        return xml_str

class CVLClient:
    _soap_client = None

    def __init__(self):
        self.user_name = settings.CVL_USER_NAME
        self.pos_code = settings.CVL_POS_CODE
        self.password = settings.CVL_PASSWORD
        self.wsdl_path = os.path.join(settings.BASE_DIR, 'docs', 'wsdl', 'CVLRestInquiry.wsdl')
        
        # Ensure wsdl exists
        if not os.path.exists(self.wsdl_path):
             cvl_logger.error(f"WSDL file not found at {self.wsdl_path}")
             raise FileNotFoundError(f"WSDL file not found at {self.wsdl_path}")

    def _generate_pass_key(self):
        """Generates a random 10-character alphanumeric pass key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    @classmethod
    def _get_soap_client(cls, instance):
        if cls._soap_client is None:
            transport = Transport(timeout=15)
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            # Use 'file://' prefix for local WSDL path
            wsdl_url = f"file://{instance.wsdl_path}"
            
            cls._soap_client = Client(
                wsdl=wsdl_url,
                transport=transport,
                settings=zeep_settings,
                service_name='CVLRestInquiry',
                port_name='BasicHttpBinding_ICVLRestInquiry',
                plugins=[CVLLoggingPlugin()]
            )
        return cls._soap_client

    def _get_auth_details(self):
        """
        Calls GetPassword to get the encrypted password using a generated pass_key.
        """
        pass_key = self._generate_pass_key()
        client = self._get_soap_client(self)

        try:
            # GetPassword(password, passKey)
            response = client.service.GetPassword(
                password=self.password,
                passKey=pass_key
            )
            
            # The result is in GetPasswordResult
            # If successful, it returns the encrypted password.
            # If failure, it might return an error string or fault.
            # Assuming standard behavior: return value is the encrypted string.
            encrypted_password = response
            
            # Basic validation: check if it looks like an error or empty
            if not encrypted_password:
                 raise Exception("Empty response from GetPassword")

            return encrypted_password, pass_key

        except Exception as e:
            cvl_logger.error(f"CVL Auth Error: {str(e)}")
            raise Exception(f"CVL Authentication Failed: {str(e)}")

    def get_pan_status(self, pan):
        """
        Checks PAN status via CVL KRA.
        Returns a dict: {'status': 'success/error', 'data': {...}, 'remarks': '...'}
        """
        try:
            encrypted_password, pass_key = self._get_auth_details()
            client = self._get_soap_client(self)

            # GetPanStatus(panNo, userName, posCode, password, passKey)
            response = client.service.GetPanStatus(
                panNo=pan,
                userName=self.user_name,
                posCode=self.pos_code,
                password=encrypted_password, # Encrypted password here
                passKey=pass_key
            )
            
            # response is GetPanStatusResult (xs:any)
            # Typically returns a pipe-separated string or JSON string.
            # Let's handle generic string response first.
            
            result_str = str(response)
            cvl_logger.info(f"PAN CHECK: {pan} | RESULT: {result_str}")

            # Typical CVL Response Format (Assumption based on industry standard):
            # RETURN_CODE|APP_NAME|APP_STATUS|STATUS_DATE|...
            # 0 -> Success? 1 -> Success?
            # Or JSON: {"Name": "...", "Status": "..."}
            
            # Since I don't have the exact response spec documentation, I will try to infer.
            # If it's JSON:
            try:
                json_data = json.loads(result_str)
                return {
                    'status': 'success',
                    'data': {
                        'name': json_data.get('APP_NAME', json_data.get('Name', '')),
                        'status': json_data.get('APP_STATUS', json_data.get('Status', '')),
                        'raw': json_data
                    }
                }
            except json.JSONDecodeError:
                pass
            
            # If Pipe Separated
            if '|' in result_str:
                parts = result_str.split('|')
                # Assuming: Code | Name | Status | ...
                # If first part is '1' or '0' (Success)
                # Let's assume index 1 is Name as requested by user ("fill name directly")
                
                # Heuristic: Find the name part.
                # Usually: CODE|NAME|STATUS
                
                # Check if it's an error message
                if "INVALID" in result_str.upper() or "ERROR" in result_str.upper():
                     return {'status': 'error', 'remarks': result_str}

                name = parts[1] if len(parts) > 1 else ""
                status = parts[2] if len(parts) > 2 else ""
                
                return {
                    'status': 'success',
                    'data': {
                        'name': name,
                        'status': status,
                        'raw': result_str
                    }
                }
            
            # If plain string (maybe just name? unlikely)
            return {'status': 'success', 'data': {'name': '', 'status': result_str, 'raw': result_str}}

        except Exception as e:
            cvl_logger.error(f"CVL PAN Check Error: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}
