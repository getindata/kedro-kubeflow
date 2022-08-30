import unittest
from io import StringIO

import yaml
from kubernetes.client import V1EmptyDirVolumeSource, V1KeyToPath, V1Volume

from kedro_kubeflow.config import ExtraVolumeConfig


class TestExtraVolumes(unittest.TestCase):
    def test_can_construct_volumes_object_from_yaml(self):
        volumes_yaml = """
mount_path: /dev/shm
volume:
    name: unit_tests_volume
    empty_dir:
        cls: V1EmptyDirVolumeSource
        params:
            medium: Memory
    """.strip()

        volumes_dict = yaml.safe_load(StringIO(volumes_yaml))
        volumes_cfg: ExtraVolumeConfig = ExtraVolumeConfig.parse_obj(
            volumes_dict
        )
        volume_def: V1Volume = volumes_cfg.as_v1volume()
        assert volumes_cfg is not None and volume_def is not None
        assert (
            volume_def.empty_dir is not None
            and isinstance(volume_def.empty_dir, V1EmptyDirVolumeSource)
            and volume_def.empty_dir.medium == "Memory"
        )

    def test_can_construct_volume_from_arbitrary_class(self):
        volumes_yaml = """
mount_path: /dev/shm
volume:
    name: unit_tests_volume
    config_map:
        cls: V1ConfigMapVolumeSource
        params:
            default_mode: 644
            items:
            - cls: kubernetes.client.models.v1_key_to_path.V1KeyToPath
              params: {"key": "abc", "path": "./myfile"}
            name: asdf
        """.strip()

        volumes_cfg: ExtraVolumeConfig = ExtraVolumeConfig.parse_obj(
            yaml.safe_load(StringIO(volumes_yaml))
        )

        volume_def: V1Volume = volumes_cfg.as_v1volume()
        assert volumes_cfg is not None and volume_def is not None
        assert volume_def.config_map is not None
        assert (
            volume_def.config_map.default_mode == 644
            and isinstance(volume_def.config_map.items, list)
            and isinstance(volume_def.config_map.items[0], V1KeyToPath)
        )
