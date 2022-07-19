"""Test utils"""

import unittest

from kedro_kubeflow.generators.utils import is_local_fs


class TestGeneratorUtils(unittest.TestCase):
    def test_is_local(self):

        assert is_local_fs("data/test/file.txt") is True
        assert is_local_fs("gs://test-bucket/file.txt") is False
