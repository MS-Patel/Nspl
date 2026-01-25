import os
import random
import string
import requests
import logging
from django.conf import settings
from zeep import Client, Settings
import datetime
from .utils import get_bse_order_params, get_bse_xsip_order_params, get_bse_mandate_param_string, map_investor_to_fatca_string
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

class BSEStarMFClient:
    # Class-level cache for Zeep Clients to avoid re-parsing WSDLs
    _soap_client = None
    _upload_client = None
    _query_client = None

    def __init__(self):
        self.member_id = settings.BSE_MEMBER_ID
        self.user_id = settings.BSE_USER_ID
        self.password = settings.BSE_PASSWORD

        # UAT Endpoints
        self.order_wsdl = "https://bsestarmfdemo.bseindia.com/MFOrderEntry/MFOrder.svc?singleWsdl"
        self.upload_service_url = "https://bsestarmfdemo.bseindia.com/StarMFFileUploadService/StarMFFileUploadService.svc/Secure/UploadFile"
        self.upload_wsdl = "https://bsestarmfdemo.bseindia.com/MFUploadService/MFUploadService.svc?singleWsdl"
        self.query_wsdl = "https://bsestarmfdemo.bseindia.com/StarMFWebService/StarMFWebService.svc?singleWsdl"
        self.common_api_url = "https://bsestarmfdemo.bseindia.com/BSEMFWEBAPI/UCCAPI/UCCRegistrationV183"
        self.emandate_auth_url = "https://bsestarmfdemo.bseindia.com/Emandate/EmandateAuthURL.aspx"
        self.emandate_api_url = "https://bsestarmfdemo.bseindia.com/StarMFWebService/StarMFWebService.svc/EMandateAuthURL"

    def _generate_pass_key(self):
        """Generates a random 10-character alphanumeric pass key."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    @classmethod
    def _get_soap_client(cls, instance):
        """
        Returns cached Zeep Client for Order Service.
        """
        if cls._soap_client is None:
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            cls._soap_client = Client(
                wsdl=instance.order_wsdl,
                settings=zeep_settings,
                service_name='MFOrder',
                port_name='WSHttpBinding_MFOrderEntry1'
            )
        return cls._soap_client

    @classmethod
    def _get_upload_soap_client(cls, instance):
        """
        Returns cached Zeep Client for Upload Service.
        """
        if cls._upload_client is None:
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            client = Client(
                wsdl=instance.upload_wsdl,
                settings=zeep_settings,
                service_name='MFUploadService',
                port_name='WSHttpBinding_IMFUploadService1'
            )
            cls._upload_client = (client, client.service)
        return cls._upload_client

    @classmethod
    def _get_query_soap_client(cls, instance):
        """
        Returns cached Zeep Client for Query Service.
        """
        if cls._query_client is None:
            zeep_settings = Settings(strict=False, xml_huge_tree=True)
            client = Client(
                wsdl=instance.query_wsdl,
                settings=zeep_settings,
                service_name='StarMFWebService',
                port_name='WSHttpBinding_IStarMFWebService1'
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
                return {
                    'status': 'error',
                    'remarks': parts[1] if len(parts) > 1 else response
                }
        except Exception as e:
            bse_logger.error(f"ORDER ENTRY ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

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
                return {
                    'status': 'error',
                    'remarks': parts[1] if len(parts) > 1 else response
                }
        except Exception as e:
            bse_logger.error(f"SIP ENTRY ERROR: {str(e)}")
            return {'status': 'error', 'remarks': str(e)}

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
            return {'status': 'error', 'remarks': str(e)}

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

    def get_order_status(self, order_no, client_code=None, order_type="All"):
        encrypted_password, pass_key = self._get_auth_details()
        _, service = self._get_query_soap_client(self)
        today = datetime.date.today().strftime("%d/%m/%Y")
        try:
            response = service.OrderStatus(Param={
                "MemberCode": self.member_id,
                "UserId": self.user_id,
                "Password": encrypted_password,
                "FromDate": today,
                "ToDate": today,
                "ClientCode": client_code if client_code else "",
                "OrderType": order_type,
                "SubOrderType": "All",
                "OrderStatus": "All",
                "SettlementType": "ALL",
                "OrderNo": order_no
            })
            bse_logger.info(f"ORDER STATUS: {order_no} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"ORDER STATUS ERROR: {str(e)}")
            return None

    def get_allotment_statement(self, order_no, client_code=None, order_type="All"):
        encrypted_password, pass_key = self._get_auth_details()
        _, service = self._get_query_soap_client(self)
        today = datetime.date.today().strftime("%d/%m/%Y")
        try:
            response = service.AllotmentStatement(Param={
                "MemberCode": self.member_id,
                "UserId": self.user_id,
                "Password": encrypted_password,
                "FromDate": today,
                "ToDate": today,
                "ClientCode": client_code if client_code else "",
                "OrderType": order_type,
                "SubOrderType": "All",
                "OrderStatus": "All",
                "SettlementType": "ALL",
                "OrderNo": order_no
            })
            bse_logger.info(f"ALLOTMENT STATEMENT: {order_no} | RESPONSE: {response}")
            return response
        except Exception as e:
            bse_logger.error(f"ALLOTMENT STATEMENT ERROR: {str(e)}")
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
        encrypted_password, _ = self._get_query_auth_details()
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
        encrypted_password, pass_key = self._get_auth_details()
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
