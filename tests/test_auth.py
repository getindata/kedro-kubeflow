import os
import unittest
from unittest.mock import patch

from google.auth.exceptions import DefaultCredentialsError

from kedro_kubeflow.auth import AuthHandler


class TestAuthHandler(unittest.TestCase):
    @patch("google.oauth2.id_token.fetch_id_token")
    def test_should_error_on_invalid_creds(self, fetch_id_token_mock):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        fetch_id_token_mock.side_effect = Exception()

        with self.assertLogs("kedro_kubeflow.auth", level="ERROR") as cm:
            # when

            token = AuthHandler().obtain_id_token()

            # then
            assert "Failed to obtain IAP access token" in cm.output[0]

        # then
        assert token is None

    @patch("google.oauth2.id_token.fetch_id_token")
    def test_should_warn_if_trying_to_use_default_creds(
        self, fetch_id_token_mock
    ):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        fetch_id_token_mock.side_effect = DefaultCredentialsError()

        with self.assertLogs("kedro_kubeflow.auth", level="WARNING") as cm:
            # when
            token = AuthHandler().obtain_id_token()

            # then
            assert (
                "this authentication method does not work with default credentials"
                in cm.output[0]
            )
            assert token is None

    @patch("google.oauth2.id_token.fetch_id_token")
    def test_should_provide_valid_token(self, fetch_id_token_mock):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        fetch_id_token_mock.return_value = "TOKEN"

        # when
        token = AuthHandler().obtain_id_token()

        # then
        assert token == "TOKEN"
