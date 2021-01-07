import os
import unittest
from contextlib import contextmanager

from kedro_kubeflow.hooks.config_loader_hook import ProjectHooks


@contextmanager
def environment(env):
    original_environ = os.environ.copy()
    os.environ.update(env)
    yield
    os.environ = original_environ


class TestKubeflowClient(unittest.TestCase):
    @staticmethod
    def get_config():
        config_path = [os.path.dirname(os.path.abspath(__file__))]
        loader = ProjectHooks().register_config_loader(conf_paths=config_path)
        return loader.get("config.yml")

    def test_loader_with_defaults(self):
        config = self.get_config()
        assert config["run_config"]["image"] == "gcr.io/project-image/dirty"
        assert config["run_config"]["experiment_name"] == "[Test] local"
        assert config["run_config"]["run_name"] == "dirty"

    def test_loader_with_env(self):
        with environment(
            {
                "KEDRO_KUBEFLOW_COMMIT": "123abc",
                "KEDRO_KUBEFLOW_BRANCH": "feature-1",
            }
        ):
            config = self.get_config()

        assert config["run_config"]["image"] == "gcr.io/project-image/123abc"
        assert config["run_config"]["experiment_name"] == "[Test] feature-1"
        assert config["run_config"]["run_name"] == "123abc"
