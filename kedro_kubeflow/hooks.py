from os import getenv
from typing import Iterable

from kedro.config import ConfigLoader, TemplatedConfigLoader
from kedro.framework.hooks import hook_impl


class RegisterTemplatedConfigLoaderHook:
    """Provides config loader that can substitute $(commit_id) and $(branch_name)
    placeholders with information taken from env variables."""

    @hook_impl
    def register_config_loader(
        self, conf_paths: Iterable[str]
    ) -> ConfigLoader:
        return TemplatedConfigLoader(
            conf_paths,
            globals_dict={
                "commit_id": getenv("KEDRO_KUBEFLOW_COMMIT", default=None),
                "branch_name": getenv("KEDRO_KUBEFLOW_BRANCH", default=None),
            },
        )


register_templated_config_loader = RegisterTemplatedConfigLoaderHook()
