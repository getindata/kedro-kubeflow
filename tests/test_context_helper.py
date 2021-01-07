import unittest
from unittest.mock import MagicMock, Mock, patch

from kedro.framework.session import KedroSession

from kedro_kubeflow.context_helper import ContextHelper, ContextHelper16


class TestContextHelper(unittest.TestCase):
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
        with patch.object(KedroSession, "create", context) as create:
            create().load_context().config_loader.get.return_value = "one"
            helper = ContextHelper.init(metadata, "test")
            assert helper.config == "one"
