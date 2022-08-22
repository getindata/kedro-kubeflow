"""Test utils"""

import unittest

from kedro_kubeflow.generators.utils import is_local_fs


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
