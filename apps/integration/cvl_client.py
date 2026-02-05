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
        self.wsdl_path = settings.CVL_SERVICE_URL

    def _generate_pass_key(self):
        """Generates a random 10-character alphanumeric pass key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    @classmethod
    def _get_soap_client(cls, instance):
        if cls._soap_client is None:
            transport = Transport(timeout=15)
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            # Use 'file://' prefix for local WSDL path
            wsdl_url = instance.wsdl_path
            
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
            
            encrypted_password = None
            print(f"Raw GetPassword response: {response}")  # Debug log for raw response
            # Check if response is an lxml Element (standard for xs:any return)
            if hasattr(response, 'find'):
                # Traverse: APP_RES_ROOT -> APP_GET_PASS
                # Note: APP_RES_ROOT usually has empty namespace, so direct find might work or we use local-name
                pass_node = response.find('APP_GET_PASS')
                if pass_node is None:
                     # Try searching recursively if structure varies
                     pass_node = response.find('.//APP_GET_PASS')
                
                if pass_node is not None and pass_node.text:
                    encrypted_password = pass_node.text
                else:
                    # Fallback log
                    cvl_logger.error(f"CVL Auth: APP_GET_PASS not found in response: {etree.tostring(response)}")
            
            # Fallback for string/bytes response
            elif isinstance(response, (str, bytes)):
                 encrypted_password = response

            if not encrypted_password:
                 raise Exception("Empty or invalid response from GetPassword")

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
            
            # response is GetPanStatusResult (xs:any), usually an lxml Element
            
            # Log the raw response for debugging (converting element to string if needed)
            if hasattr(response, 'find'):
                result_str = etree.tostring(response, pretty_print=True).decode()
            else:
                result_str = str(response)
                
            cvl_logger.info(f"PAN CHECK: {pan} | RESULT: {result_str}")

            if hasattr(response, 'find'):
                # Handle XML structure
                # Structure: APP_RES_ROOT -> APP_PAN_INQ -> [APP_NAME, APP_STATUS, ERROR, etc.]
                
                inq_node = response.find('APP_PAN_INQ')
                if inq_node is None:
                     inq_node = response.find('.//APP_PAN_INQ')

                if inq_node is not None:
                    # Check for Error
                    error_node = inq_node.find('ERROR')
                    if error_node is not None:
                        msg = error_node.find('ERROR_MSG')
                        remarks = msg.text if msg is not None else 'Unknown Error from CVL'
                        return {'status': 'error', 'remarks': remarks}
                    
                    # Extract Success Data
                    name_node = inq_node.find('APP_NAME')
                    status_node = inq_node.find('APP_STATUS')
                    
                    name = name_node.text if name_node is not None else ""
                    status = status_node.text if status_node is not None else ""
                    
                    return {
                        'status': 'success',
                        'data': {
                            'name': name,
                            'status': status,
                            'raw': result_str
                        }
                    }
                else:
                     # Check if ERROR is directly under root or somewhere else
                     error_node = response.find('.//ERROR')
                     if error_node is not None:
                         msg = error_node.find('ERROR_MSG')
                         remarks = msg.text if msg is not None else 'Unknown Error from CVL'
                         return {'status': 'error', 'remarks': remarks}

            # Fallback for unexpected formats
            return {'status': 'error', 'remarks': 'Could not parse CVL response'}

        except Exception as e:
            cvl_logger.error(f"CVL PAN Check Error: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}
