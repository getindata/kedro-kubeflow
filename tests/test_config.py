import unittest
from os import path

import yaml
from kedro.config.config import MissingConfigException

from kedro_kubeflow.config import PluginConfig


class TestPluginConfig(unittest.TestCase):
    def test_plugin_config(self):

        test_dir = path.dirname(path.abspath(__file__))
        with open(path.join(test_dir, "test_config.yml"), "r") as stream:
            raw_cfg = yaml.safe_load(stream)

        cfg = PluginConfig(raw_cfg)

        assert cfg.host == "https://example.com"
        assert (
            cfg.run_config.image == "gcr.io/project-image/${commit_id|dirty}"
        )
        assert cfg.run_config.image_pull_policy == "Always"
        assert cfg.run_config.experiment_name == "[Test] ${branch_name|local}"
        assert cfg.run_config.run_name == "${commit_id|dirty}"
        assert cfg.run_config.wait_for_completion
        assert cfg.run_config.volume.storageclass == "default"
        assert cfg.run_config.volume.size == "3Gi"
        assert cfg.run_config.volume.access_modes == "[ReadWriteMany]"

    def test_defaults(self):
        cfg = PluginConfig({"run_config": {}})
        assert cfg.run_config.image_pull_policy == "IfNotPresent"

    def test_missing_required_config(self):
        cfg = PluginConfig({})
        with self.assertRaises(MissingConfigException):
            print(cfg.host)
