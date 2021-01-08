import os
from os import getenv
from typing import Any, Dict, Iterable

from kedro.config import ConfigLoader, TemplatedConfigLoader
from kedro.framework.context import load_context
from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline

from .utils import is_mlflow_enabled


class MLFlowActivateParentHook:
    @hook_impl
    def before_pipeline_run(
        self,
        run_params: Dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ) -> None:

        if not is_mlflow_enabled():
            return

        import mlflow
        from kedro_mlflow.framework.context import get_mlflow_config

        context = load_context(
            project_path=run_params["project_path"],
            env=run_params["env"],
            extra_params=run_params["extra_params"],
        )
        mlflow_conf = get_mlflow_config(context)
        mlflow_conf.setup(context)

        mlflow.start_run(run_id=os.getenv("MLFLOW_PARENT_ID"))


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


mlflow_activate_parent_run = MLFlowActivateParentHook()

register_templated_config_loader = RegisterTemplatedConfigLoaderHook()
