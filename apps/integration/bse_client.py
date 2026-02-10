import os
import random
import string
import requests
import logging
import re
from django.conf import settings
from zeep import Client, Settings, Plugin
from lxml import etree
from zeep.transports import Transport
import datetime
from .utils import get_bse_order_params, get_bse_xsip_order_params, get_bse_switch_order_params, get_bse_mandate_param_string, map_investor_to_fatca_string
from apps.users.models import InvestorProfile

# Configure a specific logger for BSE API
bse_logger = logging.getLogger('bse_api')
bse_logger.setLevel(logging.INFO)
bse_logger.propagate = False

file_handler = logging.FileHandler('bse_api.log')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)

if not bse_logger.handlers:
    bse_logger.addHandler(file_handler)

class BSELoggingPlugin(Plugin):
    def egress(self, envelope, http_headers, operation, binding_options):
        xml = etree.tostring(envelope, pretty_print=True).decode()
        xml = self._mask_sensitive_data(xml)
        bse_logger.info(f"BSE REQUEST XML:\n{xml}")
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        if envelope is not None:
            xml = etree.tostring(envelope, pretty_print=True).decode()
            xml = self._mask_sensitive_data(xml)
            bse_logger.info(f"BSE RESPONSE XML:\n{xml}")
        return envelope, http_headers

    def _mask_sensitive_data(self, xml_str):
        sensitive_tags = ['Password', 'PassKey', 'EncryptedPassword']
        for tag in sensitive_tags:
            # Match <Tag>Content</Tag> or <ns:Tag>Content</ns:Tag>
            pattern = r'(<(?:[\w]+:)?' + tag + r'>)(.*?)(</(?:[\w]+:)?' + tag + r'>)'
            xml_str = re.sub(pattern, r'\1********\3', xml_str, flags=re.DOTALL)
        return xml_str

class BSEStarMFClient:
    # Class-level cache for Zeep Clients to avoid re-parsing WSDLs
    _soap_client = None
    _upload_client = None
    _query_client = None

    def __init__(self):
        self.member_id = settings.BSE_MEMBER_ID
        self.user_id = settings.BSE_USER_ID
        self.password = settings.BSE_PASSWORD

        # BSE Endpoints (Configurable via Settings)
        self.order_wsdl = settings.BSE_ORDER_WSDL
        self.upload_service_url = settings.BSE_UPLOAD_SERVICE_URL
        self.upload_wsdl = settings.BSE_UPLOAD_WSDL
        self.query_wsdl = settings.BSE_QUERY_WSDL
        self.common_api_url = settings.BSE_COMMON_API_URL
        self.emandate_auth_url = settings.BSE_EMANDATE_AUTH_URL
        self.emandate_api_url = settings.BSE_EMANDATE_API_URL

    def _generate_pass_key(self):
        """Generates a random 10-character alphanumeric pass key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    @classmethod
    def _get_soap_client(cls, instance):
        """
        Returns cached Zeep Client for Order Service.
        """
        if cls._soap_client is None:
            transport = Transport(timeout=10)
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            cls._soap_client = Client(
                wsdl=instance.order_wsdl,
                transport=transport,
                settings=zeep_settings,
                service_name='MFOrder',
                port_name='WSHttpBinding_MFOrderEntry1',
                plugins=[BSELoggingPlugin()]
            )
        return cls._soap_client

    @classmethod
    def _get_upload_soap_client(cls, instance):
        """
        Returns cached Zeep Client for Upload Service.
        """
        if cls._upload_client is None:
            transport = Transport(timeout=10)
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            client = Client(
                wsdl=instance.upload_wsdl,
                transport=transport,
                settings=zeep_settings,
                service_name='MFUploadService',
                port_name='WSHttpBinding_IMFUploadService1',
                plugins=[BSELoggingPlugin()]
            )
            cls._upload_client = (client, client.service)
        return cls._upload_client

    @classmethod
    def _get_query_soap_client(cls, instance):
        """
        Returns cached Zeep Client for Query Service.
        """
        if cls._query_client is None:
            transport = Transport(timeout=10)
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            client = Client(
                wsdl=instance.query_wsdl,
                transport=transport,
                settings=zeep_settings,
                service_name='StarMFWebService',
                port_name='WSHttpBinding_IStarMFWebService1',
                plugins=[BSELoggingPlugin()]
            )
            cls._query_client = (client, client.service)
        return cls._query_client

    def _get_auth_details(self):
        pass_key = self._generate_pass_key()
        client = self._get_soap_client(self)

        try:
            response = client.service.getPassword(
                UserId=self.user_id,
                Password=self.password,
                PassKey=pass_key
            )
            result_str = response.split('|')
            if result_str[0] == '100':
                return result_str[1], pass_key
            else:
                raise Exception(f"BSE Authentication Failed: {response}")
        except Exception as e:
            raise Exception(f"SOAP Error during authentication: {str(e)}")

    def _get_upload_auth_details(self):
        pass_key = self._generate_pass_key()
        _, service = self._get_upload_soap_client(self)

        try:
            response = service.getPassword(
                UserId=self.user_id,
                MemberId=self.member_id,
                Password=self.password,
                PassKey=pass_key
            )
            result_str = response.split('|')
            if result_str[0] == '100':
                return result_str[1], pass_key
            else:
                raise Exception(f"BSE Upload Service Authentication Failed: {response}")
        except Exception as e:
            raise Exception(f"SOAP Error during upload service authentication: {str(e)}")


    def _get_query_auth_details(self):
        pass_key = self._generate_pass_key()
        _, service = self._get_query_soap_client(self)

        try:
            response = service.getPassword(
                UserId=self.user_id,
                MemberId=self.member_id,
                Password=self.password,
                PassKey=pass_key
            )
            result_str = response.split('|')
            if result_str[0] == '100':
                return result_str[1], pass_key
            else:
                raise Exception(f"BSE Query Service Authentication Failed: {response}")
        except Exception as e:
            raise Exception(f"SOAP Error during query service authentication: {str(e)}")


    def _get_query_auth_token(self):
        pass_key = self._generate_pass_key()
        _, service = self._get_query_soap_client(self)

        try:
            param = {
                "MemberId": self.member_id,
                "UserId": self.user_id,
                "Password": self.password,
                "PassKey": pass_key,
                "RequestType": "MANDATE"
            }
            response = service.GetAccessToken(Param=param)
            
            status = getattr(response, 'Status', '')
            if status == '100':
                return getattr(response, 'ResponseString', ''), pass_key
            else:
                raise Exception(f"BSE Query Service Authentication Failed: {response}")
        except Exception as e:
            raise Exception(f"SOAP Error during query service authentication: {str(e)}")

    def _get_password(self):
        token, _ = self._get_auth_details()
        return token

    def place_order(self, order):
        # COMPLIANCE GUARD
        investor = order.investor
        if investor.nominee_auth_status == InvestorProfile.AUTH_PENDING and investor.nomination_opt == 'Y':
             return {
                'status': 'error',
                'remarks': 'COMPLIANCE BLOCK: Nominee Authentication is Pending.'
            }

        try:
            encrypted_password, pass_key = self._get_auth_details()
            params = get_bse_order_params(
                order,
                self.member_id,
                self.user_id,
                encrypted_password,
                pass_key
            )
            client = self._get_soap_client(self)
            bse_logger.info(f"ORDER Request: {params}")
            response = client.service.orderEntryParam(**params)
            bse_logger.info(f"ORDER ENTRY: {order.unique_ref_no} | RESPONSE: {response}")

            parts = str(response).split('|')
            if parts[0] == '0':
                return {
                    'status': 'success',
                    'bse_order_id': parts[1] if len(parts) > 1 else "",
                    'remarks': parts[2] if len(parts) > 2 else 'Order Placed'
                }
            else:
                remarks = parts[1] if len(parts) > 1 else str(response)
                # Handle Echo format where remarks are at index 6
                if len(parts) > 6 and not parts[0].isdigit():
                     remarks = parts[6]
                return {
                    'status': 'error',
                    'remarks': remarks
                }
        except Exception as e:
            bse_logger.error(f"ORDER ENTRY ERROR: {str(e)}")
            return {'status': 'exception', 'remarks': str(e)}

    def switch_order(self, order):
        # COMPLIANCE GUARD
        investor = order.investor
        if investor.nominee_auth_status == InvestorProfile.AUTH_PENDING and investor.nomination_opt == 'Y':
             return {
                'status': 'error',
                'remarks': 'COMPLIANCE BLOCK: Nominee Authentication is Pending.'
            }

        try:
            encrypted_password, pass_key = self._get_auth_details()
            params = get_bse_switch_order_params(
                order,
                self.member_id,
                self.user_id,
                encrypted_password,
                pass_key
            )
            client = self._get_soap_client(self)
            bse_logger.info(f"SWITCH ORDER Request: {params}")
            response = client.service.switchOrderEntryParam(**params)
            bse_logger.info(f"SWITCH ORDER ENTRY: {order.unique_ref_no} | RESPONSE: {response}")

            parts = str(response).split('|')
            if parts[0] == '0':
                return {
                    'status': 'success',
                    'bse_order_id': parts[1] if len(parts) > 1 else "",
                    'remarks': parts[2] if len(parts) > 2 else 'Switch Order Placed'
                }
            else:
                remarks = parts[1] if len(parts) > 1 else str(response)
                # Handle Echo format where remarks are at index 6
                if len(parts) > 6 and not parts[0].isdigit():
                     remarks = parts[6]
                return {
                    'status': 'error',
                    'remarks': remarks
                }
        except Exception as e:
            bse_logger.error(f"SWITCH ORDER ENTRY ERROR: {str(e)}")
            return {'status': 'exception', 'remarks': str(e)}

    def register_sip(self, sip):
        investor = sip.investor
        if investor.nominee_auth_status == InvestorProfile.AUTH_PENDING and investor.nomination_opt == 'Y':
             return {
                'status': 'error',
                'remarks': 'COMPLIANCE BLOCK: Nominee Authentication is Pending.'
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
            bse_logger.info(f"SIP ENTRY: {sip.id} | Params: {params}")
            client = self._get_soap_client(self)
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
                remarks = parts[1] if len(parts) > 1 else str(response)
                # Handle Echo format where remarks are at index 6
                if len(parts) > 6 and not parts[0].isdigit():
                     remarks = parts[6]
                return {
                    'status': 'error',
                    'remarks': remarks
                }
        except Exception as e:
            bse_logger.error(f"SIP ENTRY ERROR: {str(e)}")
            return {'status': 'exception', 'remarks': str(e)}

    def register_mandate(self, mandate):
        try:
            encrypted_password, _ = self._get_upload_auth_details()
            param_string = get_bse_mandate_param_string(mandate)
            _, service = self._get_upload_soap_client(self)
            bse_logger.info(f"MANDATE REG Request: Flag=06, Param={param_string}")
            response = service.MFAPI(
                Flag='06',
                UserId=self.user_id,
                EncryptedPassword=encrypted_password,
                param=param_string
            )
            bse_logger.info(f"MANDATE REG: {mandate.id} | RESPONSE: {response}")
            parts = str(response).split('|')
            if parts[0] == '100':
                 return {
                    'status': 'success',
                    'remarks': parts[1] if len(parts) > 1 else 'Mandate Registered',
                    'mandate_id': parts[2] if len(parts) > 2 else None,
                }
            else:
                return {
                    'status': 'error',
                    'remarks': parts[1] if len(parts) > 1 else response
                }
        except Exception as e:
            bse_logger.error(f"MANDATE REG ERROR: {str(e)}")
            return {'status': 'exception', 'remarks': str(e)}

    def register_client(self, payload, regn_type="NEW"):
        request_body = {
            "UserId": self.user_id,
            "MemberCode": self.member_id,
            "Password": self.password,
            "RegnType": regn_type,
            "Param": payload['Param'],
            "Filler1": "",
            "Filler2": ""
        }
        log_body = request_body.copy()
        log_body['Password'] = '********'
        bse_logger.info(f"API: {self.common_api_url} | REGN TYPE: {regn_type} | REQUEST BODY: {log_body}")
        try:
            response = requests.post(self.common_api_url, json=request_body, verify=False)
            response.raise_for_status()
            bse_logger.info(f"API: {self.common_api_url} | RESPONSE: {response.text}")
            result = response.json()
            if result.get("Status") == "0":
                return {"status": "success", "remarks": result.get("Remarks"), "data": result}
            else:
                return {"status": "error", "remarks": result.get("Remarks"), "data": result}
        except Exception as e:
            bse_logger.error(f"API Error: {str(e)}")
            return {"status": "error", "remarks": f"HTTP/Network Error: {str(e)}"}

    def fatca_upload(self, investor):
        try:
            encrypted_password, _ = self._get_upload_auth_details()
            param_string = map_investor_to_fatca_string(investor)
            _, service = self._get_upload_soap_client(self)
            bse_logger.info(f"FATCA UPLOAD Request: Flag=01, Param={param_string}")
            response = service.MFAPI(
                Flag='01',
                UserId=self.user_id,
                EncryptedPassword=encrypted_password,
                param=param_string
            )
            bse_logger.info(f"FATCA UPLOAD: {investor.pan} | RESPONSE: {response}")
            parts = str(response).split('|')
            if parts[0] == '100':
                 return {'status': 'success', 'remarks': parts[1] if len(parts) > 1 else 'FATCA Uploaded'}
            else:
                return {'status': 'error', 'remarks': parts[1] if len(parts) > 1 else response}
        except Exception as e:
            bse_logger.error(f"FATCA UPLOAD ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

    def get_mandate_auth_url(self, client_code, mandate_id, loopback_url=""):
        payload = {
            "MemberCode": self.member_id,
            "Password": self.password,
            "ClientCode": client_code,
            "UserId": self.user_id,
            "MandateID": mandate_id,
            "LoopBackUrl": loopback_url
        }
        log_body = payload.copy()
        log_body['Password'] = '********'
        bse_logger.info(f"API: {self.emandate_api_url} | REQUEST BODY: {log_body}")
        try:
            response = requests.post(self.emandate_api_url, json=payload, verify=False)
            response.raise_for_status()
            bse_logger.info(f"API: {self.emandate_api_url} | RESPONSE: {response.text}")
            try:
                data = response.json()
                if isinstance(data, dict):
                     return data.get('ResponseString', data.get('URL', response.text))
                return str(data)
            except ValueError:
                return response.text.strip('"')
        except Exception as e:
            bse_logger.error(f"API Error (Emandate Auth): {str(e)}")
            raise e

    def get_order_status(self, order_no=None, client_code=None, order_type="All", from_date=None, to_date=None):
        try:
            _, service = self._get_query_soap_client(self)

            today = datetime.date.today().strftime("%d/%m/%Y")
            f_date = from_date if from_date else today
            t_date = to_date if to_date else today

            params = {
                "MemberCode": self.member_id,
                "UserId": self.user_id,
                "Password": self.password,
                "FromDate": f_date,
                "ToDate": t_date,
                "ClientCode": client_code if client_code else "",
                "OrderType": order_type,
                "SubOrderType": "All",
                "OrderStatus": "All",
                "SettType": "ALL",
                "OrderNo": order_no if order_no else "",
                "TransType": "P"
            }
            log_params = params.copy()
            log_params['Password'] = '********'
            bse_logger.info(f"ORDER STATUS Request: {log_params}")
            response = service.OrderStatus(Param=params)
            bse_logger.info(f"ORDER STATUS: {order_no} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"ORDER STATUS ERROR: {str(e)}")
            return None

    def get_provisional_order_status(self, order_no=None, client_code=None, order_type="All", from_date=None, to_date=None, trans_type="P"):
        """
        Fetches the provisional order status from BSE.
        """
        try:
            _, service = self._get_query_soap_client(self)

            today = datetime.date.today().strftime("%d/%m/%Y")
            f_date = from_date if from_date else today
            t_date = to_date if to_date else today

            params = {
                "MemberCode": self.member_id,
                "UserId": self.user_id,
                "Password": self.password,
                "FromDate": f_date,
                "ToDate": t_date,
                "ClientCode": client_code if client_code else "",
                "OrderType": order_type,
                "SubOrderType": "All",
                "OrderStatus": "All",
                "SettType": "ALL",
                "OrderNo": order_no if order_no else "",
                "TransType": trans_type,
                "Filler1": "",
                "Filler2": "",
                "Filler3": ""
            }
            log_params = params.copy()
            log_params['Password'] = '********'
            bse_logger.info(f"PROVISIONAL ORDER STATUS Request: {log_params}")
            response = service.ProvOrderStatus(Param=params)
            bse_logger.info(f"PROVISIONAL ORDER STATUS: {order_no} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"PROVISIONAL ORDER STATUS ERROR: {str(e)}")
            return None

    def get_allotment_statement(self, order_no=None, client_code=None, order_type="All", from_date=None, to_date=None):
        try:
            _, service = self._get_query_soap_client(self)

            today = datetime.date.today().strftime("%d/%m/%Y")
            f_date = from_date if from_date else today
            t_date = to_date if to_date else today

            params = {
                "MemberCode": self.member_id,
                "UserId": self.user_id,
                "Password": self.password,
                "FromDate": f_date,
                "ToDate": t_date,
                "ClientCode": client_code if client_code else "",
                "OrderType": order_type,
                "SubOrderType": "All",
                "OrderStatus": "All",
                "SettType": "ALL",
                "OrderNo": order_no if order_no else "",
                "Filler1": ""
            }
            log_params = params.copy()
            log_params['Password'] = '********'
            bse_logger.info(f"ALLOTMENT STATEMENT Request: {log_params}")
            response = service.AllotmentStatement(Param=params)
            bse_logger.info(f"ALLOTMENT STATEMENT: {order_no} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"ALLOTMENT STATEMENT ERROR: {str(e)}")
            return None

    def get_redemption_statement(self, order_no=None, client_code=None, from_date=None, to_date=None):
        try:
            _, service = self._get_query_soap_client(self)

            today = datetime.date.today().strftime("%d/%m/%Y")
            f_date = from_date if from_date else today
            t_date = to_date if to_date else today
            params = {
                "MemberCode": self.member_id,
                "UserId": self.user_id,
                "Password": self.password,
                "FromDate": f_date,
                "ToDate": t_date,
                "ClientCode": client_code if client_code else "",
                "OrderType": "All",
                "SubOrderType": "All",
                "OrderStatus": "All",
                "SettType": "ALL",
                "OrderNo": order_no if order_no else "",
                "Filler1": "",
                "Filler2": "",
                "Filler3": ""
            }
            log_params = params.copy()
            log_params['Password'] = '********'
            bse_logger.info(f"REDEMPTION STATEMENT Request: {log_params}")
            response = service.RedemptionStatement(Param=params)
            bse_logger.info(f"REDEMPTION STATEMENT: {order_no} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"REDEMPTION STATEMENT ERROR: {str(e)}")
            return None

    def get_payment_status(self, client_code, order_no):
        try:
            encrypted_password, _ = self._get_upload_auth_details()
            _, service = self._get_upload_soap_client(self)
            param_string = f"{client_code}|{order_no}|BSEMF"
            bse_logger.info(f"PAYMENT STATUS Request: Flag=11, Param={param_string}")
            response = service.MFAPI(
                Flag='11',
                UserId=self.user_id,
                EncryptedPassword=encrypted_password,
                param=param_string
            )
            bse_logger.info(f"PAYMENT STATUS: {order_no} | RESPONSE: {response}")
            parts = str(response).split('|')
            if parts[0] == '100':
                return {'status': 'success', 'remarks': parts[1] if len(parts) > 1 else 'Success'}
            else:
                return {'status': 'error', 'remarks': parts[1] if len(parts) > 1 else response}
        except Exception as e:
            bse_logger.error(f"PAYMENT STATUS ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

    def get_mandate_status(self, mandate_id, client_code=None):
        encrypted_password, _ = self._get_query_auth_token()
        _, service = self._get_query_soap_client(self)
        today = datetime.date.today().strftime("%d/%m/%Y")
        start_date = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%d/%m/%Y")
        try:
            response = service.MandateDetails(Param={
                "MemberCode": self.member_id,
                "ClientCode": client_code if client_code else "",
                "MandateId": mandate_id,
                "FromDate": start_date,
                "ToDate": today,
                "EncryptedPassword": encrypted_password
            })
            bse_logger.info(f"MANDATE STATUS: {mandate_id} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"MANDATE STATUS ERROR: {str(e)}")
            return None

    def get_child_orders(self, regn_no, client_code, plan_type="XSIP"):
        encrypted_password, _ = self._get_query_auth_details()
        _, service = self._get_query_soap_client(self)
        today = datetime.date.today().strftime("%d %b %Y").upper()
        try:
            response = service.ChildOrderDetails(Param={
                "Date": today,
                "MemberCode": self.member_id,
                "ClientCode": client_code,
                "SystematicPlanType": plan_type,
                "RegnNo": regn_no,
                "EncryptedPassword": encrypted_password
            })
            bse_logger.info(f"CHILD ORDERS: {regn_no} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"CHILD ORDERS ERROR: {str(e)}")
            return None

    def check_pan_status(self, pan):
        """
        Checks the status of a PAN using AOFPanSearch API.
        """
        encrypted_password, pass_key = self._get_query_auth_details()
        _, service = self._get_query_soap_client(self)
        try:
            response = service.AOFPanSearch(Param={
                "MemberCode": self.member_id,
                "PAN": pan,
                "Password": encrypted_password,
                "UserId": self.user_id
            })
            bse_logger.info(f"PAN CHECK: {pan} | RESPONSE: {response}")

            # Serialize the Zeep object to a dictionary
            # Note: Zeep objects can be converted to dict using helpers, but simple attribute access works
            result_data = {
                'status': getattr(response, 'Status', ''),
                'remarks': getattr(response, 'BSERemarks', ''),
                'pan': getattr(response, 'PAN', ''),
                'inv_name': getattr(response, 'InvName', '')
            }

            return {
                'status': 'success',
                'data': result_data
            }
        except Exception as e:
            bse_logger.error(f"PAN CHECK ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}
