import os
import unittest
from unittest.mock import patch

import mlflow

from kedro_kubeflow.auth import AuthHandler
from kedro_kubeflow.hooks import MlflowIapAuthHook, MlflowTagsHook  # NOQA

from .utils import environment


class TestMlflowIapAuthHook(unittest.TestCase):
    @patch.object(AuthHandler, "obtain_id_token", return_value="TEST_TOKEN")
    def test_should_inject_token_when_env_is_set(self, obtain_id_token):
        MlflowIapAuthHook().after_catalog_created(catalog=None)

        assert os.environ["MLFLOW_TRACKING_TOKEN"] == "TEST_TOKEN"
        obtain_id_token.assert_called_with()


@patch.object(mlflow, "set_tag")
class TestMlflowTagsHook(unittest.TestCase):
    def test_should_set_mlflow_tags(self, mlflow_set_tag):
        with environment({"KUBEFLOW_RUN_ID": "KFP_123"}):
            MlflowTagsHook().before_node_run()

        mlflow_set_tag.assert_called_with("kubeflow_run_id", "KFP_123")

    def test_should_not_set_mlflow_tags_when_kubeflow_run_id_env_is_not_set(
        self, mlflow_set_tag
    ):
        with environment({}, delete_keys=["KUBEFLOW_RUN_ID"]):
            MlflowTagsHook().before_node_run()

        mlflow_set_tag.assert_not_called()

    def test_should_not_set_mlflow_tags_when_kubeflow_run_id_env_is_empty(
        self, mlflow_set_tag
    ):
        with environment({"KUBEFLOW_RUN_ID": ""}):
            MlflowTagsHook().before_node_run()

        mlflow_set_tag.assert_not_called()

    def test_should_not_set_mlflow_tags_when_mlflow_is_not_enabled(
        self, mlflow_set_tag
    ):
        # given
        real_import = __builtins__["__import__"]

        def mlflow_import_disabled(name, *args, **kw):
            if name == "mlflow":
                raise ImportError
            return real_import(name, *args, **kw)

        __builtins__["__import__"] = mlflow_import_disabled

        # when
        with environment({"KUBEFLOW_RUN_ID": "KFP_123"}):
            MlflowTagsHook().before_node_run()

        # then
        mlflow_set_tag.assert_not_called()

        # cleanup
        __builtins__["__import__"] = real_import
