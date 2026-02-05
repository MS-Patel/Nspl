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
                service_name='CVLPanInquiry',
                port_name='BasicHttpBinding_ICVLPanInquiry',
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
            # GetPassword(webApi={...})
            response = client.service.GetPassword(
                webApi={
                    'password': self.password,
                    'passKey': pass_key,
                    'userName': self.user_name,
                    'posCode': self.pos_code
                }
            )
            
            encrypted_password = None

            # Zeep might return a dictionary-like object or list for xs:any inside mixed content
            # If response is an lxml Element (unlikely with Zeep unwrapping unless raw)
            # Ensure it's not a string because strings also have .find()
            if hasattr(response, 'find') and not isinstance(response, (str, bytes)):
                pass_node = response.find('APP_GET_PASS')
                if pass_node is None:
                     pass_node = response.find('.//APP_GET_PASS')
                
                if pass_node is not None and pass_node.text:
                    encrypted_password = pass_node.text

            # Check if it's a list (common for xs:any)
            elif isinstance(response, list):
                for item in response:
                    if hasattr(item, 'find') and not isinstance(item, (str, bytes)):
                        pass_node = item.find('APP_GET_PASS') or item.find('.//APP_GET_PASS')
                        if pass_node is not None and pass_node.text:
                            encrypted_password = pass_node.text
                            break

            # Check if it's a dict or object with _value_1 or similar
            # Or if Zeep parsed the xs:any content into lxml elements directly
            elif hasattr(response, '_value_1'):
                # mixed content
                vals = response._value_1
                if isinstance(vals, list):
                    for val in vals:
                        if hasattr(val, 'find') and not isinstance(val, (str, bytes)):
                             pass_node = val.find('APP_GET_PASS') or val.find('.//APP_GET_PASS')
                             if pass_node is not None and pass_node.text:
                                encrypted_password = pass_node.text
                                break
            
            # Fallback for string/bytes response
            elif isinstance(response, (str, bytes)):
                 encrypted_password = response

            if not encrypted_password:
                # Last ditch effort: if response itself contains the element but wasn't caught
                # or if debugging shows something else.
                # For now, let's log error.
                cvl_logger.error(f"CVL Auth: APP_GET_PASS not found in response: {response}")
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

            # GetPanStatus(webApi={...})
            response = client.service.GetPanStatus(
                webApi={
                    'pan': pan,
                    'userName': self.user_name,
                    'posCode': self.pos_code,
                    'password': encrypted_password, # Encrypted password here
                    'passKey': pass_key
                }
            )
            
            # response is GetPanStatusResult (xs:any)
            
            result_str = str(response)
            cvl_logger.info(f"PAN CHECK: {pan} | RESULT: {result_str}")

            # Helper to find node in various response types
            def find_in_response(resp, tag):
                if hasattr(resp, 'find') and not isinstance(resp, (str, bytes)):
                    n = resp.find(tag)
                    if n is None: n = resp.find(f'.//{tag}')
                    return n
                if isinstance(resp, list):
                    for item in resp:
                        res = find_in_response(item, tag)
                        if res is not None: return res
                if hasattr(resp, '_value_1'):
                     return find_in_response(resp._value_1, tag)
                return None

            # Logic to parse response
            inq_node = find_in_response(response, 'APP_PAN_INQ')

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
                 error_node = find_in_response(response, 'ERROR')
                 if error_node is not None:
                     msg = error_node.find('ERROR_MSG')
                     remarks = msg.text if msg is not None else 'Unknown Error from CVL'
                     return {'status': 'error', 'remarks': remarks}

            # Fallback for unexpected formats
            return {'status': 'error', 'remarks': 'Could not parse CVL response'}

        except Exception as e:
            cvl_logger.error(f"CVL PAN Check Error: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}
