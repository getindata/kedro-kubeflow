import unittest

import yaml
from kedro.config.config import MissingConfigException

from kedro_kubeflow.config import PluginConfig

CONFIG_YAML = """
host: https://example.com

run_config:
  image: "gcr.io/project-image/test"
  image_pull_policy: "Always"
  experiment_name: "Test Experiment"
  run_name: "test run"
  wait_for_completion: True
  volume:
    storageclass: default
    size: 3Gi
    access_modes: [ReadWriteOnce]
"""


class TestPluginConfig(unittest.TestCase):
    def test_plugin_config(self):

        cfg = PluginConfig(yaml.safe_load(CONFIG_YAML))

        assert cfg.host == "https://example.com"
        assert cfg.run_config.image == "gcr.io/project-image/test"
        assert cfg.run_config.image_pull_policy == "Always"
        assert cfg.run_config.experiment_name == "Test Experiment"
        assert cfg.run_config.run_name == "test run"
        assert cfg.run_config.wait_for_completion
        assert cfg.run_config.volume.storageclass == "default"
        assert cfg.run_config.volume.size == "3Gi"
        assert cfg.run_config.volume.access_modes == ["ReadWriteOnce"]
        assert cfg.run_config.resources.is_set_for("node1") is False

    def test_defaults(self):
        cfg = PluginConfig({"run_config": {}})
        assert cfg.run_config.image_pull_policy == "IfNotPresent"

    def test_missing_required_config(self):
        cfg = PluginConfig({})
        with self.assertRaises(MissingConfigException):
            print(cfg.host)

    def test_resources_default_only(self):
        cfg = PluginConfig(
            {"run_config": {"resources": {"__default__": {"cpu": "100m"}}}}
        )
        assert cfg.run_config.resources.is_set_for("node2")
        assert cfg.run_config.resources.get_for("node2") == {"cpu": "100m"}
        assert cfg.run_config.resources.is_set_for("node3")
        assert cfg.run_config.resources.get_for("node3") == {"cpu": "100m"}

    def test_resources_no_default(self):
        cfg = PluginConfig(
            {"run_config": {"resources": {"node2": {"cpu": "100m"}}}}
        )
        assert cfg.run_config.resources.is_set_for("node2")
        assert cfg.run_config.resources.get_for("node2") == {"cpu": "100m"}
        assert cfg.run_config.resources.is_set_for("node3") is False

    def test_resources_default_and_node_specific(self):
        cfg = PluginConfig(
            {
                "run_config": {
                    "resources": {
                        "__default__": {"cpu": "200m", "memory": "64Mi"},
                        "node2": {"cpu": "100m"},
                    }
                }
            }
        )
        assert cfg.run_config.resources.is_set_for("node2")
        assert cfg.run_config.resources.get_for("node2") == {
            "cpu": "100m",
            "memory": "64Mi",
        }
        assert cfg.run_config.resources.is_set_for("node3")
        assert cfg.run_config.resources.get_for("node3") == {
            "cpu": "200m",
            "memory": "64Mi",
        }
