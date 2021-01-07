import os
from typing import Any, Dict

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


mlflow_activate_parent_run = MLFlowActivateParentHook()
