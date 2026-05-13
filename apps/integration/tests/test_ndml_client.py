from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.integration.ndml_client import NDMLClient
from apps.administration.models import SystemConfiguration

class TestNDMLClient(TestCase):
    def setUp(self):
        self.config = SystemConfiguration.objects.create(
            ndml_user_name='testuser',
            ndml_password='testpassword',
            ndml_pos_code='POS001',
            ndml_mi_id='MI001'
        )

    @patch('apps.integration.ndml_client.Client')
    def test_kyc_modification(self, MockZeepClient):
        # Mocking Zeep Client
        mock_service = MagicMock()
        mock_service.getPassword.return_value = "EncryptedToken123"
        mock_service.processModification.return_value = "<RESPONSE>Success</RESPONSE>"

        MockZeepClient.return_value.service = mock_service

        client = NDMLClient()
        # To avoid calling _get_auth_details internally that hits Zeep again for getPassword
        with patch.object(client, '_get_auth_details', return_value=("EncryptedToken123", "PassKey123")):
            client._okra_client = MockZeepClient()
            result = client.kyc_modification("<REQ>Test</REQ>")

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['data'], "<RESPONSE>Success</RESPONSE>")
