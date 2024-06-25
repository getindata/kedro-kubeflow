import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from kedro.framework.session import KedroSession

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.context_helper import (
    ContextHelper,
    ContextHelper16,
    EnvTemplatedConfigLoader,
)

from .common import MinimalConfigMixin
from .utils import environment


class TestContextHelper(unittest.TestCase, MinimalConfigMixin):
    def test_init_different_kedro_versions(self):

        with patch("kedro_kubeflow.context_helper.kedro_version", "0.16.0"):
            ch = ContextHelper.init(None, None)
            assert isinstance(ch, ContextHelper16)

    def test_project_name(self):
        metadata = Mock()
        metadata.project_path = Path("test_project")

        helper = ContextHelper.init(metadata, "test")
        assert helper.project_name == "test_project"

    def test_context(self):
        metadata = Mock()
        metadata.package_name = "test_package"
        kedro_session = MagicMock(KedroSession)
        kedro_session.load_context.return_value = "sample_context"

        with patch.object(KedroSession, "create") as create:
            create().load_context.return_value = "sample_context"
            helper = ContextHelper.init(metadata, "test")
            assert helper.context == "sample_context"
            create.assert_called_with("test_package", env="test")

    def test_config(self):
        metadata = Mock()
        metadata.package_name = "test_package"
        context = MagicMock()
        context.config_loader.return_value.get.return_value = ["one", "two"]
        with patch.object(KedroSession, "create", context), patch(
            "kedro_kubeflow.context_helper.EnvTemplatedConfigLoader"
        ) as config_loader:
            config_loader.return_value.get.return_value = self.minimal_config()
            helper = ContextHelper.init(metadata, "test")
            assert helper.config == PluginConfig(**self.minimal_config())
            assert config_loader.call_args.kwargs["env"] == "test"


class TestEnvTemplatedConfigLoader(unittest.TestCase):
    @staticmethod
    def get_config():
        config_path = str(
            Path(os.path.dirname(os.path.abspath(__file__))) / "conf"
        )
        loader = EnvTemplatedConfigLoader(
            config_path,
            env="unittests",
            default_run_env="base",
            config_patterns={"test_config": ["test_config.yml"]},
        )
        return loader.get("test_config")

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
