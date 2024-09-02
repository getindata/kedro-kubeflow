import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

import yaml
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
        metadata.project_name = "test_project"

        helper = ContextHelper.init(metadata, "test")
        assert helper.project_name == "test_project"

    def test_context(self):
        metadata = Mock()
        metadata.project_path = "test_package"
        kedro_session = MagicMock(KedroSession)
        kedro_session.load_context.return_value = "sample_context"

        with patch.object(KedroSession, "create") as create:
            create().load_context.return_value = "sample_context"
            helper = ContextHelper.init(metadata, "test")
            assert helper.context == "sample_context"
            create.assert_called_with("test_package", env="test")

    # def test_config(self):
    #     metadata = Mock()
    #     metadata.package_name = "test_package"
    #     session = MagicMock()
    #     cfg = self.minimal_config()
    #     session.load_context().config_loader.return_value = cfg.dict()
    #     with patch.object(KedroSession, "create", return_value=session), patch(
    #         "kedro_kubeflow.context_helper.EnvTemplatedConfigLoader"
    #     ) as config_loader:
    #         config_loader.return_value.get.return_value =
    #         helper = ContextHelper.init(metadata, "test")
    #         assert helper.config == PluginConfig(**self.minimal_config())
    #         assert config_loader.call_args.kwargs["env"] == "test"

    def test_config(self):
        metadata = Mock()
        metadata.package_name = "test_package"
        session = MagicMock()
        cfg = PluginConfig.parse_obj(self.minimal_config())
        session.load_context().config_loader.get.return_value = cfg.dict()
        with patch.object(KedroSession, "create", return_value=session):
            helper = ContextHelper.init(metadata, "test")
            assert helper.config == cfg

    # TODO debug and fix omegaconf test
    def test_config_with_omegaconf(self):
        from kedro.config import OmegaConfigLoader

        with TemporaryDirectory() as tmp_dir_raw:
            tmp_dir = Path(tmp_dir_raw)
            (tmp_dir / "conf" / "base").mkdir(parents=True, exist_ok=False)
            (conf_dir := tmp_dir / "conf" / "local").mkdir(parents=True, exist_ok=False)
            cfg = PluginConfig.parse_obj(self.minimal_config())
            (conf_dir / "kubeflow.yml").write_text(
                yaml.dump(json.loads(json.dumps(cfg.dict()))), None
            )  # because enums are not

            metadata = Mock()
            metadata.package_name = "test_package"
            for config_pattern in [{"kubeflow": ["kubeflow*"]}]:
                session = MagicMock()
                session.load_context().config_loader = OmegaConfigLoader(
                    str(tmp_dir / "conf"),
                    config_patterns=config_pattern,
                    default_run_env="local",
                    base_env="local",
                )
                with patch.object(KedroSession, "create", return_value=session):
                    helper = ContextHelper.init(metadata, "test")
                    assert helper.config == cfg


class TestEnvTemplatedConfigLoader(unittest.TestCase):
    @staticmethod
    def get_config():
        config_path = str(Path(os.path.dirname(os.path.abspath(__file__))) / "conf")
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
