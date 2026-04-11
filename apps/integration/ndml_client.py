import logging
import random
import string
import re
from django.conf import settings
from zeep import Client, Settings, Plugin
from lxml import etree
from zeep.transports import Transport
from apps.administration.models import SystemConfiguration

# Configure a specific logger for NDML API
ndml_logger = logging.getLogger('ndml_api')
ndml_logger.setLevel(logging.INFO)
ndml_logger.propagate = False

file_handler = logging.FileHandler('ndml_api.log')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)

if not ndml_logger.handlers:
    ndml_logger.addHandler(file_handler)

class NDMLLoggingPlugin(Plugin):
    def egress(self, envelope, http_headers, operation, binding_options):
        xml = etree.tostring(envelope, pretty_print=True).decode()
        xml = self._mask_sensitive_data(xml)
        ndml_logger.info(f"NDML REQUEST XML:\n{xml}")
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        if envelope is not None:
            xml = etree.tostring(envelope, pretty_print=True).decode()
            xml = self._mask_sensitive_data(xml)
            ndml_logger.info(f"NDML RESPONSE XML:\n{xml}")
        return envelope, http_headers

    def _mask_sensitive_data(self, xml_str):
        sensitive_tags = ['password', 'passKey', 'encryptedPassword']
        for tag in sensitive_tags:
            pattern = r'(<(?:[\w]+:)?' + tag + r'>)(.*?)(</(?:[\w]+:)?' + tag + r'>)'
            xml_str = re.sub(pattern, r'\1********\3', xml_str, flags=re.DOTALL)
        return xml_str

class NDMLClient:
    _okra_client = None
    _pan_client = None

    def __init__(self):
        config = SystemConfiguration.get_solo()
        self.user_name = config.ndml_user_name
        self.password = config.ndml_password
        self.pos_code = config.ndml_pos_code
        self.mi_id = config.ndml_mi_id
        self.okra_wsdl = settings.NDML_OKRA_WSDL
        self.pan_wsdl = settings.NDML_PAN_WSDL

        if not all([self.user_name, self.password, self.pos_code, self.mi_id]):
            ndml_logger.warning("NDML configuration is incomplete in SystemConfiguration.")

    def _generate_pass_key(self):
        return ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=10))

    @classmethod
    def _get_okra_client(cls, instance):
        if cls._okra_client is None:
            transport = Transport(timeout=15)
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            cls._okra_client = Client(
                wsdl=instance.okra_wsdl,
                transport=transport,
                settings=zeep_settings,
                plugins=[NDMLLoggingPlugin()]
            )
        return cls._okra_client

    @classmethod
    def _get_pan_client(cls, instance):
        if cls._pan_client is None:
            transport = Transport(timeout=15)
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            cls._pan_client = Client(
                wsdl=instance.pan_wsdl,
                transport=transport,
                settings=zeep_settings,
                plugins=[NDMLLoggingPlugin()]
            )
        return cls._pan_client

    def _get_auth_details(self, client_type='okra'):
        pass_key = self._generate_pass_key()

        try:
            if client_type == 'okra':
                client = self._get_okra_client(self)
                response = client.service.getPassword(
                    password=self.password,
                    key=pass_key
                )
            else:
                client = self._get_pan_client(self)
                response = client.service.getPasscode(
                    arg0=self.password,
                    arg1=pass_key
                )

            if not response:
                raise Exception("Empty response from NDML Authentication.")

            return response, pass_key

        except Exception as e:
            ndml_logger.error(f"NDML Auth Error ({client_type}): {str(e)}")
            raise Exception(f"NDML Authentication Failed: {str(e)}")

    def kyc_registration(self, request_xml):
        """
        Sends the KYC Registration XML to NDML Okra Service.
        """
        try:
            encrypted_password, pass_key = self._get_auth_details('okra')
            client = self._get_okra_client(self)

            response = client.service.registration(
                input=request_xml.encode('utf-8'),
                userId=self.user_name,
                userPassword=encrypted_password,
                passKey=pass_key,
                okraCdOrMiId=self.mi_id
            )

            return {'status': 'success', 'data': response}
        except Exception as e:
            ndml_logger.error(f"NDML Registration Error: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

    def pan_inquiry_details_two(self, request_xml):
        """
        Sends PAN Inquiry XML to NDML PAN Service.
        """
        try:
            encrypted_password, pass_key = self._get_auth_details('pan')
            client = self._get_pan_client(self)

            response = client.service.panInquiryDetailsTwo(
                arg0=request_xml,
                arg1=self.user_name,
                arg2=encrypted_password,
                arg3=pass_key,
                arg4=self.mi_id
            )

            return {'status': 'success', 'data': response}
        except Exception as e:
            ndml_logger.error(f"NDML PAN Inquiry Error: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

    def kyc_download_details(self, request_xml):
        """
        Sends KYC Download XML to NDML PAN Service.
        """
        try:
            encrypted_password, pass_key = self._get_auth_details('pan')
            client = self._get_pan_client(self)

            response = client.service.panDownloadDetailsComplete(
                arg0=request_xml,
                arg1=self.user_name,
                arg2=encrypted_password,
                arg3=pass_key,
                arg4=self.mi_id
            )

            return {'status': 'success', 'data': response}
        except Exception as e:
            ndml_logger.error(f"NDML KYC Download Error: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}
