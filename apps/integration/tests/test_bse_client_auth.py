from django.test import SimpleTestCase, override_settings
from unittest.mock import MagicMock, patch
from apps.integration.bse_client import BSEStarMFClient

@override_settings(BSE_MEMBER_ID='MEMBER_ID', BSE_USER_ID='USER_ID', BSE_PASSWORD='PASSWORD')
class TestBSEAuthSplit(SimpleTestCase):

    def test_auth_split(self):
        client = BSEStarMFClient()

        # --- Mock Order Service (Existing) ---
        mock_order_client = MagicMock()
        mock_order_service_instance = MagicMock()
        mock_order_client.service = mock_order_service_instance
        # Mock getPassword response
        mock_order_service_instance.getPassword.return_value = "100|OrderAuthToken"

        # Override the method on the instance
        client._get_soap_client = MagicMock(return_value=mock_order_client)

        # --- Mock Upload Service (New) ---
        mock_upload_client = MagicMock()
        mock_upload_service_instance = MagicMock()
        # Mock getPassword response
        mock_upload_service_instance.getPassword.return_value = "100|UploadAuthToken"

        # Override the method on the instance: returns (client, service)
        client._get_upload_soap_client = MagicMock(return_value=(mock_upload_client, mock_upload_service_instance))

        # --- Mock Query Service (New for Mandate Check) ---
        mock_query_client = MagicMock()
        mock_query_service_instance = MagicMock()
        # Mock getPassword response
        mock_query_service_instance.getPassword.return_value = "100|QueryAuthToken"

        # Override the method on the instance: returns (client, service)
        client._get_query_soap_client = MagicMock(return_value=(mock_query_client, mock_query_service_instance))

        # --- TEST 1: Place Order (Should use Order Service Auth) ---
        with patch('apps.integration.bse_client.get_bse_order_params') as mock_params:
            mock_params.return_value = {'param': 'value'}

            mock_order = MagicMock()
            mock_order.unique_ref_no = "123456"
            # Ensure compliance guard passes
            mock_order.investor.nominee_auth_status = 'A'
            mock_order.investor.nomination_opt = 'Y'

            # Mock orderEntryParam response
            mock_order_service_instance.orderEntryParam.return_value = "0|OrderNo|Success"

            # CALL
            client.place_order(mock_order)

            # VERIFY
            mock_order_service_instance.getPassword.assert_called()
            mock_upload_service_instance.getPassword.assert_not_called()
            mock_query_service_instance.getPassword.assert_not_called()

            call_args = mock_order_service_instance.getPassword.call_args
            self.assertEqual(call_args.kwargs['UserId'], "USER_ID")
            self.assertEqual(call_args.kwargs['Password'], "PASSWORD")

            # Reset mocks
            mock_order_service_instance.reset_mock()
            mock_upload_service_instance.reset_mock()
            mock_query_service_instance.reset_mock()

        # --- TEST 2: Register Mandate (Should use Upload Service Auth) ---
        with patch('apps.integration.bse_client.get_bse_mandate_param_string') as mock_mandate_params:
            mock_mandate_params.return_value = "pipe|separated|string"
            mock_mandate = MagicMock()

            # Mock MFAPI call on the upload service
            mock_upload_service_instance.MFAPI.return_value = "100|MandateID|Success"

            # CALL
            client.register_mandate(mock_mandate)

            # VERIFY
            mock_upload_service_instance.getPassword.assert_called()
            mock_order_service_instance.getPassword.assert_not_called()
            mock_query_service_instance.getPassword.assert_not_called()

            call_args = mock_upload_service_instance.getPassword.call_args
            self.assertEqual(call_args.kwargs['UserId'], "USER_ID")
            self.assertEqual(call_args.kwargs['Password'], "PASSWORD")

            # Reset mocks
            mock_order_service_instance.reset_mock()
            mock_upload_service_instance.reset_mock()
            mock_query_service_instance.reset_mock()

        # --- TEST 3: Check Mandate Status (Should use Query Service Auth) ---
        # Mock MandateDetails response
        mock_query_service_instance.MandateDetails.return_value = "MandateDetailsResponse"

        # CALL
        client.get_mandate_status("12345")

        # VERIFY
        mock_query_service_instance.getPassword.assert_called()
        mock_order_service_instance.getPassword.assert_not_called()
        mock_upload_service_instance.getPassword.assert_not_called()

        call_args = mock_query_service_instance.getPassword.call_args
        self.assertEqual(call_args.kwargs['UserId'], "USER_ID")
        self.assertEqual(call_args.kwargs['Password'], "PASSWORD")
        self.assertEqual(call_args.kwargs['MemberId'], "MEMBER_ID")

        # Verify MandateDetails call used the token
        mock_query_service_instance.MandateDetails.assert_called()
        mandate_call_args = mock_query_service_instance.MandateDetails.call_args
        self.assertEqual(mandate_call_args.kwargs['Param']['EncryptedPassword'], "QueryAuthToken")
