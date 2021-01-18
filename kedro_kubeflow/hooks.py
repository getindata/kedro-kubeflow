import os
from typing import Dict, Iterable

from kedro.config import ConfigLoader, TemplatedConfigLoader
from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog

VAR_PREFIX = "KEDRO_CONFIG_"

# defaults provided so default variables ${commit_id|dirty} work for some entries
ENV_DEFAULTS = {"commit_id": None, "branch_name": None}


class RegisterTemplatedConfigLoaderHook:
    """Provides config loader that can substitute $(commit_id) and $(branch_name)
    placeholders with information taken from env variables."""

    @staticmethod
    def read_env() -> Dict:
        config = ENV_DEFAULTS.copy()
        overrides = dict(
            [
                (k.replace(VAR_PREFIX, "").lower(), v)
                for k, v in os.environ.copy().items()
                if k.startswith(VAR_PREFIX)
            ]
        )
        config.update(**overrides)
        return config

    @hook_impl
    def register_config_loader(
        self, conf_paths: Iterable[str]
    ) -> ConfigLoader:
        return TemplatedConfigLoader(
            conf_paths,
            globals_dict=self.read_env(),
        )


class MlflowIapAuthHook:
    """Allows authentication trough IAP proxy the same way as kubeflow pipelines"""

    @hook_impl
    def after_catalog_created(self, catalog: DataCatalog, **kwargs) -> None:
        from .auth import AuthHandler

        token = AuthHandler().obtain_id_token()
        if token:
            os.environ["MLFLOW_TRACKING_TOKEN"] = token


register_templated_config_loader = RegisterTemplatedConfigLoaderHook()
mlflow_iap_hook = MlflowIapAuthHook()
