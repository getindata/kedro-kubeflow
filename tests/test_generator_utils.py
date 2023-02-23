"""Test utils"""

import unittest

from kedro_kubeflow.generators.utils import (
    is_local_fs,
    merge_namespaced_params_to_dict,
)


def gcsfs_is_missing():
    try:
        import gcsfs  # NOQA

        return False
    except ImportError:
        return True


@unittest.skipIf(gcsfs_is_missing(), "Package gcsfs is not installed")
class TestGeneratorUtils(unittest.TestCase):
    def test_is_local(self):
        assert is_local_fs("data/test/file.txt") is True
        assert is_local_fs("gs://test-bucket/file.txt") is False

    def test_namespaced_params_merged_into_dict_properly(self):
        # given
        params = {
            "outer_namespace.inner_namespace1.param1": "outer_namespace.inner_namespace1.param1_v",
            "outer_namespace.inner_namespace1.param2": "outer_namespace.inner_namespace1.param2_v",
            "outer_namespace.inner_namespace2.param1": "outer_namespace.inner_namespace2.param1_v",
            "outer_namespace.inner_namespace2.param2": "outer_namespace.inner_namespace2.param2_v",
            "outer_namespace.param": "outer_namespace.param",
            "param1": 42,
        }

        # when
        result = merge_namespaced_params_to_dict(params)

        # expect
        expected = {
            "outer_namespace": {
                "inner_namespace1": {
                    "param1": "outer_namespace.inner_namespace1.param1_v",
                    "param2": "outer_namespace.inner_namespace1.param2_v",
                },
                "inner_namespace2": {
                    "param1": "outer_namespace.inner_namespace2.param1_v",
                    "param2": "outer_namespace.inner_namespace2.param2_v",
                },
                "param": "outer_namespace.param",
            },
            "param1": 42,
        }
        assert result == expected
