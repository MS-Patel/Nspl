import pytest
from unittest.mock import patch, MagicMock
from apps.integration.bse_client import BSEStarMFClient
import datetime

@pytest.mark.django_db
class TestBSEProvisionalOrder:
    def test_get_provisional_order_status_success(self):
        with patch('apps.integration.bse_client.Client') as MockZeepClient:
            # Mock Service
            mock_service = MagicMock()

            # Construct a dummy response object
            mock_response = MagicMock()
            mock_response.Status = "100"
            mock_response.Message = "Success"
            mock_response.provOrderDetails = [] # Empty list for simplicity

            mock_service.ProvOrderStatus.return_value = mock_response

            # Mock client returning this service
            MockZeepClient.return_value.service = mock_service

            client = BSEStarMFClient()

            # Define inputs
            order_no = "12345"
            client_code = "TESTCLIENT"

            # Need to force _query_client to use our mock because of class-level caching if it was already initialized
            BSEStarMFClient._query_client = None

            result = client.get_provisional_order_status(order_no=order_no, client_code=client_code)

            assert result.Status == "100"
            assert result.Message == "Success"

            # Verify call arguments
            mock_service.ProvOrderStatus.assert_called_once()
            call_args = mock_service.ProvOrderStatus.call_args[1]['Param']

            today = datetime.date.today().strftime("%d/%m/%Y")

            assert call_args['OrderNo'] == order_no
            assert call_args['ClientCode'] == client_code
            assert call_args['FromDate'] == today
            assert call_args['ToDate'] == today
            assert call_args['Filler1'] == ""
            assert call_args['TransType'] == "P"

    def test_get_provisional_order_status_failure(self):
        with patch('apps.integration.bse_client.Client') as MockZeepClient:
            # Mock Service to raise exception
            mock_service = MagicMock()
            mock_service.ProvOrderStatus.side_effect = Exception("Connection Error")
            MockZeepClient.return_value.service = mock_service

            # Reset cache
            BSEStarMFClient._query_client = None

            client = BSEStarMFClient()
            result = client.get_provisional_order_status(order_no="123")

            assert result is None
