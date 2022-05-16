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
  scheduled_run_name: "scheduled run"
  description: "My awesome pipeline"
  wait_for_completion: True
  ttl: 300
  volume:
    storageclass: default
    size: 3Gi
    access_modes: [ReadWriteOnce]
    keep: True
"""


class TestPluginConfig(unittest.TestCase):
    def test_plugin_config(self):
        cfg = PluginConfig(yaml.safe_load(CONFIG_YAML))
        assert cfg.host == "https://example.com"
        assert cfg.run_config.image == "gcr.io/project-image/test"
        assert cfg.run_config.image_pull_policy == "Always"
        assert cfg.run_config.experiment_name == "Test Experiment"
        assert cfg.run_config.run_name == "test run"
        assert cfg.run_config.scheduled_run_name == "scheduled run"
        assert cfg.run_config.wait_for_completion
        assert cfg.run_config.volume.storageclass == "default"
        assert cfg.run_config.volume.size == "3Gi"
        assert cfg.run_config.volume.keep is True
        assert cfg.run_config.volume.access_modes == ["ReadWriteOnce"]
        assert cfg.run_config.resources.is_set_for("node1") is False
        assert cfg.run_config.description == "My awesome pipeline"
        assert cfg.run_config.ttl == 300

    def test_defaults(self):
        cfg = PluginConfig({"run_config": {}})
        assert cfg.run_config.image_pull_policy == "IfNotPresent"
        assert cfg.run_config.description is None
        SECONDS_IN_ONE_WEEK = 3600 * 24 * 7
        assert cfg.run_config.ttl == SECONDS_IN_ONE_WEEK
        assert cfg.run_config.volume is None

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

    def test_tolerations_default_only(self):
        toleration_config = [{
            "key": "thekey",
            "operator": "equal",
            "value": "thevalue",
            "effect": "NoSchedule",
        }]
        cfg = PluginConfig(
            {"run_config": {"tolerations": {"__default__": toleration_config
                                            }}}
        )
        assert cfg.run_config.tolerations.is_set_for("node2")
        assert cfg.run_config.tolerations.get_for("node2") == toleration_config
        assert cfg.run_config.tolerations.is_set_for("node3")
        assert cfg.run_config.tolerations.get_for("node3") == toleration_config

    def test_tolerations_no_default(self):
        toleration_config = [{
            "key": "thekey",
            "operator": "equal",
            "value": "thevalue",
            "effect": "NoSchedule",
        }]
        cfg = PluginConfig(
            {"run_config": {"tolerations": {"node2": toleration_config}}}
        )
        assert cfg.run_config.tolerations.is_set_for("node2")
        assert cfg.run_config.tolerations.get_for("node2") == toleration_config
        assert cfg.run_config.tolerations.is_set_for("node3") is False

    def test_tolerations_default_and_node_specific(self):
        toleration_config = [{
            "key": "thekey",
            "operator": "equal",
            "value": "thevalue",
            "effect": "NoSchedule",
        }]
        default_toleration_config = [{
            "key": "thekeyfordefault",
            "operator": "equal",
            "value": "thevaluefordefault",
            "effect": "NoSchedule",
        }]
        cfg = PluginConfig(
            {
                "run_config": {
                    "tolerations": {
                        "__default__": default_toleration_config,
                        "node2": toleration_config,
                    }
                }
            }
        )
        assert cfg.run_config.tolerations.is_set_for("node2")
        assert cfg.run_config.tolerations.get_for("node2") == toleration_config
        assert cfg.run_config.tolerations.is_set_for("node3")
        assert cfg.run_config.tolerations.get_for("node3") == default_toleration_config

    def test_do_not_keep_volume_by_default(self):
        cfg = PluginConfig({"run_config": {"volume": {}}})
        assert cfg.run_config.volume.keep is False

    def test_reuse_run_name_for_scheduled_run_name(self):
        cfg = PluginConfig({"run_config": {"run_name": "some run"}})
        assert cfg.run_config.run_name == "some run"
        assert cfg.run_config.scheduled_run_name == "some run"

    def test_retry_policy_default_and_node_specific(self):
        cfg = PluginConfig(
            {
                "run_config": {
                    "retry_policy": {
                        "__default__": {
                            "num_retries": 4,
                            "backoff_duration": "60s",
                            "backoff_factor": 2,
                        },
                        "node3": {
                            "num_retries": "100",
                            "backoff_duration": "5m",
                            "backoff_factor": 1,
                        },
                    }
                }
            }
        )
        assert cfg.run_config.retry_policy.is_set_for("node2")
        assert cfg.run_config.retry_policy.get_for("node2") == {
            "backoff_duration": "60s",
            "backoff_factor": 2,
            "num_retries": 4,
        }
        assert cfg.run_config.retry_policy.is_set_for("node3")
        assert cfg.run_config.retry_policy.get_for("node3") == {
            "backoff_duration": "5m",
            "backoff_factor": 1,
            "num_retries": 100,
        }
