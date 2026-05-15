import os
import unittest
from unittest.mock import MagicMock, patch

from kedro_kubeflow.auth import AuthHandler
from kedro_kubeflow.hooks import MlflowIapAuthHook, MlflowTagsHook  # NOQA

from .utils import environment


class TestMlflowIapAuthHook(unittest.TestCase):
    @patch.object(AuthHandler, "obtain_id_token", return_value="TEST_TOKEN")
    def test_should_inject_token_when_env_is_set(self, obtain_id_token):
        MlflowIapAuthHook().after_catalog_created(catalog=None)

        assert os.environ["MLFLOW_TRACKING_TOKEN"] == "TEST_TOKEN"
        obtain_id_token.assert_called_with()


class TestMlflowTagsHook(unittest.TestCase):
    def test_should_set_mlflow_tags(self):
        mlflow_mock = MagicMock()
        with patch.dict("sys.modules", {"mlflow": mlflow_mock, "kedro_mlflow": MagicMock()}), environment(
            {"KUBEFLOW_RUN_ID": "KFP_123"}
        ):
            MlflowTagsHook().before_node_run()

        mlflow_mock.set_tag.assert_called_with("kubeflow_run_id", "KFP_123")

    def test_should_not_set_mlflow_tags_when_kubeflow_run_id_env_is_not_set(self):
        mlflow_mock = MagicMock()
        with patch.dict("sys.modules", {"mlflow": mlflow_mock, "kedro_mlflow": MagicMock()}), environment(
            {}, delete_keys=["KUBEFLOW_RUN_ID"]
        ):
            MlflowTagsHook().before_node_run()

        mlflow_mock.set_tag.assert_not_called()

    def test_should_not_set_mlflow_tags_when_kubeflow_run_id_env_is_empty(self):
        mlflow_mock = MagicMock()
        with patch.dict("sys.modules", {"mlflow": mlflow_mock, "kedro_mlflow": MagicMock()}), environment(
            {"KUBEFLOW_RUN_ID": ""}
        ):
            MlflowTagsHook().before_node_run()

        mlflow_mock.set_tag.assert_not_called()

    @patch("kedro_kubeflow.hooks.is_mlflow_enabled", return_value=False)
    def test_should_not_set_mlflow_tags_when_mlflow_is_not_enabled(self, _):
        mlflow_mock = MagicMock()
        with environment({"KUBEFLOW_RUN_ID": "KFP_123"}):
            with patch.dict("sys.modules", {"mlflow": mlflow_mock}):
                MlflowTagsHook().before_node_run()

        mlflow_mock.set_tag.assert_not_called()
