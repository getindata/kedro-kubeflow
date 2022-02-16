import os

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog

from kedro_kubeflow.utils import is_mlflow_enabled


class MlflowIapAuthHook:
    """Allows authentication trough IAP proxy the same way as kubeflow pipelines"""

    @hook_impl
    def after_catalog_created(self, catalog: DataCatalog, **kwargs) -> None:
        from .auth import AuthHandler

        token = AuthHandler().obtain_id_token()
        if token:
            os.environ["MLFLOW_TRACKING_TOKEN"] = token


class MlflowTagsHook:
    """Adds `kubeflow_run_id` to MLFlow tags based on environment variables"""

    @hook_impl
    def before_node_run(self) -> None:
        if is_mlflow_enabled():
            import mlflow

            if os.getenv("KUBEFLOW_RUN_ID"):
                mlflow.set_tag(
                    "kubeflow_run_id", os.environ["KUBEFLOW_RUN_ID"]
                )


mlflow_iap_hook = MlflowIapAuthHook()
mlflow_tags_hook = MlflowTagsHook()
