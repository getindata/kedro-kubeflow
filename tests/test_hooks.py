import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import mlflow

from kedro_kubeflow.auth import AuthHandler
from kedro_kubeflow.hooks import (  # NOQA
    MlflowIapAuthHook,
    MlflowTagsHook,
    RegisterTemplatedConfigLoaderHook,
)


@contextmanager
def environment(env):
    original_environ = os.environ.copy()
    os.environ.update(env)
    yield
    os.environ = original_environ


class TestRegisterTemplatedConfigLoaderHook(unittest.TestCase):
    @staticmethod
    def get_config():
        config_path = [os.path.dirname(os.path.abspath(__file__))]
        loader = RegisterTemplatedConfigLoaderHook().register_config_loader(
            conf_paths=config_path
        )
        return loader.get("test_config.yml")

    def test_loader_with_defaults(self):
        config = self.get_config()
        assert config["run_config"]["image"] == "gcr.io/project-image/dirty"
        assert config["run_config"]["experiment_name"] == "[Test] local"
        assert config["run_config"]["run_name"] == "dirty"

    def test_loader_with_env(self):
        with environment(
            {
                "KEDRO_CONFIG_COMMIT_ID": "123abc",
                "KEDRO_CONFIG_BRANCH_NAME": "feature-1",
                "KEDRO_CONFIG_XYZ123": "123abc",
            }
        ):
            config = self.get_config()

        assert config["run_config"]["image"] == "gcr.io/project-image/123abc"
        assert config["run_config"]["experiment_name"] == "[Test] feature-1"
        assert config["run_config"]["run_name"] == "123abc"


class TestMlflowIapAuthHook(unittest.TestCase):
    @patch.object(AuthHandler, "obtain_id_token", return_value="TEST_TOKEN")
    def test_should_inject_token_when_env_is_set(self, obtain_id_token):
        MlflowIapAuthHook().after_catalog_created(catalog=None)

        assert os.environ["MLFLOW_TRACKING_TOKEN"] == "TEST_TOKEN"
        obtain_id_token.assert_called_with()


@patch.object(mlflow, "set_tag")
class TestMlflowTagsHook(unittest.TestCase):
    def test_should_set_mlflow_tags(self, mlflow_set_tag):
        MlflowTagsHook().after_pipeline_run(
            run_params={"extra_params": {"kubeflow_run_id": "KFP_123"}}
        )

        mlflow_set_tag.assert_called_with("kubeflow_run_id", "KFP_123")

    def test_should_not_set_mlflow_tags_when_kubeflow_run_id_is_not_passed_in_params(
        self, mlflow_set_tag
    ):
        MlflowTagsHook().after_pipeline_run(
            run_params={"extra_params": {"other_param": "value"}}
        )

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
        MlflowTagsHook().after_pipeline_run(
            run_params={"extra_params": {"kubeflow_run_id": "KFP_123"}}
        )

        # then
        mlflow_set_tag.assert_not_called()

        # cleanup
        __builtins__["__import__"] = real_import
