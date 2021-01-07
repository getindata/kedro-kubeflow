from typing import Iterable

from kedro.config import TemplatedConfigLoader, ConfigLoader
from kedro.framework.hooks import hook_impl
from os import getenv


class ProjectHooks:
    """ Provides config loader that can substitute $(commit_id) and $(branch_name)
    placeholders with information taken from env variables. """

    @hook_impl
    def register_config_loader(self, conf_paths: Iterable[str]) -> ConfigLoader:
        return TemplatedConfigLoader(
            conf_paths,
            globals_dict={
                "commit_id": getenv("KEDRO_KUBEFLOW_COMMIT", default=None),
                "branch_name": getenv("KEDRO_KUBEFLOW_BRANCH", default=None),
            }
        )
