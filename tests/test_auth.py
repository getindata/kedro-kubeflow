import os
import unittest
from unittest.mock import patch

import responses
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
    def test_should_warn_if_trying_to_use_default_creds(self, fetch_id_token_mock):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        fetch_id_token_mock.side_effect = DefaultCredentialsError()

        with self.assertLogs("kedro_kubeflow.auth", level="WARNING") as cm:
            # when
            token = AuthHandler().obtain_id_token()

            # then
            assert "this authentication method does not work with default credentials" in cm.output[0]
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

    def test_should_skip_dex_auth_if_env_is_not_set(self):
        # given
        # no env set

        # when
        session = AuthHandler().obtain_dex_authservice_session(None)

        # then
        assert session is None

    def test_should_skip_dex_auth_if_env_is_incomplete(self):
        # given
        os.environ["DEX_USERNAME"] = "user@example.com"
        # no password set

        # when
        session = AuthHandler().obtain_dex_authservice_session(None)

        # then
        assert session is None

    def tearDown(self):
        if "DEX_USERNAME" in os.environ:
            del os.environ["DEX_USERNAME"]
        if "DEX_PASSWORD" in os.environ:
            del os.environ["DEX_PASSWORD"]
        if "IAP_CLIENT_ID" in os.environ:
            del os.environ["IAP_CLIENT_ID"]

    @responses.activate
    def test_should_get_cookie_from_dex_secured_system(self):
        # given
        os.environ["DEX_USERNAME"] = "user@example.com"
        os.environ["DEX_PASSWORD"] = "pa$$"
        responses.add(
            responses.GET,
            "https://kubeflow.local/pipeline",
            body='<a href="/dex/auth/local?req=qjrrnpg3hngdu6odii3hcmfae" target="_self"',
        )
        responses.add(
            responses.POST,
            "https://kubeflow.local/dex/auth/local?req=qjrrnpg3hngdu6odii3hcmfae",
            headers={"Set-cookie": "authservice_session=sessionID"},
        )

        # when
        session = AuthHandler().obtain_dex_authservice_session("https://kubeflow.local/pipeline")

        # then
        assert session == "sessionID"
        assert responses.calls[1].request.body == "login=user%40example.com&password=pa%24%24"

    @responses.activate
    def test_should_get_cookie_from_dex_secured_system_with_kubeflow_1_6(self):
        # given
        os.environ["DEX_USERNAME"] = "user@example.com"
        os.environ["DEX_PASSWORD"] = "pa$$"
        responses.add(
            responses.GET,
            "https://kubeflow.local/pipeline",
            body='<a href="/dex/auth/local?client_id=kubeflow-oidc-authservice&amp;redirect_uri=%2Flogin%2Foidc&amp;response_type=code&amp;scope=profile&#43;email&#43;groups&#43;openid&amp;state=MTY2MzY3Njk0OHxFd3dBRUZVeGFtdEhaR2RPYVZsRE5XWmpTbkU9fNHbrYsoZfJQGtNhqLlcn_B7MiGljHAAOUoyvZD-53Bg" target="_self">',  # noqa: E501
        )
        responses.add(
            responses.GET,
            "https://kubeflow.local/dex/auth/local?client_id=kubeflow-oidc-authservice&redirect_uri=%2Flogin%2Foidc&response_type=code&scope=profile+email+groups+openid&state=MTY2MzY3Njk0OHxFd3dBRUZVeGFtdEhaR2RPYVZsRE5XWmpTbkU9fNHbrYsoZfJQGtNhqLlcn_B7MiGljHAAOUoyvZD-53Bg",  # noqa: E501
            body='<a href="/dex/auth/local/login?back=%2Fdex%2Fauth%3Fclient_id%3Dkubeflow-oidc-authservice%26redirect_uri%3D%252Flogin%252Foidc%26response_type%3Dcode%26scope%3Dprofile%2Bemail%2Bgroups%2Bopenid%26state%3DMTY2MzY3Njk0OHxFd3dBRUZVeGFtdEhaR2RPYVZsRE5XWmpTbkU9fNHbrYsoZfJQGtNhqLlcn_B7MiGljHAAOUoyvZD-53Bg&amp;state=o4odhdlneub2iczv2657sa2gv" target="_self">',  # noqa: E501
        )

        responses.add(
            responses.POST,
            "https://kubeflow.local/dex/auth/local/login?back=%2Fdex%2Fauth%3Fclient_id%3Dkubeflow-oidc-authservice%26redirect_uri%3D%252Flogin%252Foidc%26response_type%3Dcode%26scope%3Dprofile%2Bemail%2Bgroups%2Bopenid%26state%3DMTY2MzY3Njk0OHxFd3dBRUZVeGFtdEhaR2RPYVZsRE5XWmpTbkU9fNHbrYsoZfJQGtNhqLlcn_B7MiGljHAAOUoyvZD-53Bg&state=o4odhdlneub2iczv2657sa2gv",  # noqa: E501
            headers={"Set-cookie": "authservice_session=sessionID"},
        )

        # when
        session = AuthHandler().obtain_dex_authservice_session("https://kubeflow.local/pipeline")

        # then
        assert session == "sessionID"
        assert responses.calls[2].request.body == "login=user%40example.com&password=pa%24%24"
