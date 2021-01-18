import logging
import os

IAP_CLIENT_ID = "IAP_CLIENT_ID"


class AuthHandler(object):

    log = logging.getLogger(__name__)

    def obtain_id_token(self):
        from google.auth.exceptions import DefaultCredentialsError
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        client_id = os.environ.get(IAP_CLIENT_ID, None)

        jwt_token = None

        if not client_id:
            self.log.debug(
                "No IAP_CLIENT_ID provided, skipping custom IAP authentication"
            )
            return jwt_token

        try:
            self.log.debug("Attempt to get IAP token for %s." + client_id)
            jwt_token = id_token.fetch_id_token(Request(), client_id)
            self.log.info("Obtained JWT token for IAP proxy authentication.")
        except DefaultCredentialsError as ex:
            self.log.warning(
                str(ex)
                + (
                    " Note that this authentication method does not work with default"
                    " credentials obtained via 'gcloud auth application-default login'"
                    " command. Refer to documentation on how to configure service account"
                    " locally"
                    " (https://cloud.google.com/docs/authentication/production#manually)"
                )
            )
        except Exception as e:
            self.log.error("Failed to obtain IAP access token. " + str(e))
        finally:
            return jwt_token
