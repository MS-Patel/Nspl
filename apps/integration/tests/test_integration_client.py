import pytest
from unittest.mock import patch, MagicMock
from apps.users.factories import InvestorProfileFactory, BankAccountFactory
from apps.products.factories import SchemeFactory
from apps.investments.factories import OrderFactory
from apps.investments.models import Order
from apps.integration.bse_client import BSEStarMFClient
from apps.integration.utils import map_investor_to_bse_param_string
from django.contrib.auth import get_user_model

@pytest.mark.django_db
class TestBSEClient:
    def test_get_password_soap_success(self):
        with patch('apps.integration.bse_client.Client') as MockZeepClient:
            # Mock SOAP Response
            mock_service = MagicMock()
            mock_service.getPassword.return_value = "100|EncryptedToken123"
            MockZeepClient.return_value.service = mock_service

            client = BSEStarMFClient()
            token = client._get_password() # Should return string only

            assert token == "EncryptedToken123"
            mock_service.getPassword.assert_called_once()

    def test_get_auth_details_success(self):
        with patch('apps.integration.bse_client.Client') as MockZeepClient:
            # Mock SOAP Response
            mock_service = MagicMock()
            mock_service.getPassword.return_value = "100|EncryptedToken123"
            MockZeepClient.return_value.service = mock_service

            client = BSEStarMFClient()
            token, pass_key = client._get_auth_details() # Should return tuple

            assert token == "EncryptedToken123"
            assert pass_key is not None
            assert len(pass_key) == 10
            mock_service.getPassword.assert_called_once()

    def test_register_client_success(self):
        investor = InvestorProfileFactory(ucc_code='TEST001')
        BankAccountFactory(investor=investor, is_default=True)
        # Assuming we need a nominee, but factories handle basics.
        # The mapper might need explicit fields like address, but factory provides Faker data.

        with patch('apps.integration.bse_client.requests.post') as mock_post:
            # Mock JSON Response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "Status": "0",
                "Remarks": "CLIENT REGISTERED SUCCESSFULLY"
            }
            mock_post.return_value = mock_response

            client = BSEStarMFClient()
            # Create payload using our utility
            param_string = map_investor_to_bse_param_string(investor)
            payload = {'Param': param_string}

            result = client.register_client(payload)

            assert result['status'] == 'success'
            assert result['remarks'] == 'CLIENT REGISTERED SUCCESSFULLY'
            mock_post.assert_called_once()

    def test_place_order_success(self):
        investor = InvestorProfileFactory(ucc_code='TEST001')
        scheme = SchemeFactory(scheme_code='SCHEME001')
        order = OrderFactory(
            investor=investor,
            scheme=scheme,
            amount=5000,
            transaction_type=Order.PURCHASE,
            is_new_folio=True
        )

        with patch('apps.integration.bse_client.Client') as MockZeepClient:
            # Mock Service
            mock_service = MagicMock()
            mock_service.getPassword.return_value = "100|EncryptedToken123"
            mock_service.orderEntryParam.return_value = "0|123456|Order Placed Successfully"

            MockZeepClient.return_value.service = mock_service

            client = BSEStarMFClient()
            result = client.place_order(order)

            assert result['status'] == 'success'
            assert result['bse_order_id'] == '123456'

            # Verify calls
            mock_service.getPassword.assert_called_once()
            mock_service.orderEntryParam.assert_called_once()

            call_args = mock_service.orderEntryParam.call_args[1]
            assert call_args['ClientCode'] == 'TEST001'
            assert call_args['SchemeCode'] == 'SCHEME001'
            assert call_args['TxtAmount'] == '5000.00'
            assert call_args['TxtQuantity'] == '0'

    def test_place_redemption_with_decimals(self):
        investor = InvestorProfileFactory(ucc_code='TEST001')
        scheme = SchemeFactory(scheme_code='SCHEME001')
        order = OrderFactory(
            investor=investor,
            scheme=scheme,
            amount=0,
            units=10.5567,
            transaction_type=Order.REDEMPTION,
            is_new_folio=False
        )

        with patch('apps.integration.bse_client.Client') as MockZeepClient:
            # Mock Service
            mock_service = MagicMock()
            mock_service.getPassword.return_value = "100|EncryptedToken123"
            mock_service.orderEntryParam.return_value = "0|123456|Redemption Placed"

            MockZeepClient.return_value.service = mock_service

            client = BSEStarMFClient()
            result = client.place_order(order)

            assert result['status'] == 'success'

            call_args = mock_service.orderEntryParam.call_args[1]
            assert call_args['TxtQuantity'] == '10.5567'

    def test_mapper_utility(self):
        investor = InvestorProfileFactory(pan='ABCDE1234F')
        BankAccountFactory(investor=investor, is_default=True)
        # Test if the mapper generates a string with pipes
        param_string = map_investor_to_bse_param_string(investor)
        assert isinstance(param_string, str)
        assert 'ABCDE1234F' in param_string # PAN
        assert '|' in param_string
