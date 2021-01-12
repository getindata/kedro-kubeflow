import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kedro_kubeflow.cli import (
    compile,
    init,
    list_pipelines,
    run_once,
    schedule,
    ui,
    upload_pipeline,
)
from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.context_helper import ContextHelper

test_config = PluginConfig(
    {
        "host": "https://example.com",
        "run_config": {
            "image": "gcr.io/project-image/test",
            "image_pull_policy": "Always",
            "experiment_name": "Test Experiment",
            "run_name": "test run",
            "wait_for_completion": True,
            "volume": {
                "storageclass": "default",
                "size": "3Gi",
                "access_modes": "[ReadWriteOnce]",
            },
        },
    }
)


class TestPluginCLI(unittest.TestCase):
    def test_list_pipelines(self):
        context_helper = MagicMock(ContextHelper)
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(list_pipelines, [], obj=config)

        assert result.exit_code == 0
        context_helper.kfp_client.list_pipelines.assert_called_with()

    def test_run_once(self):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(
            run_once, ["-i", "new_img", "-p", "new_pipe"], obj=config
        )

        assert result.exit_code == 0
        context_helper.kfp_client.run_once.assert_called_with(
            experiment_name="Test Experiment",
            image="new_img",
            image_pull_policy="Always",
            pipeline="new_pipe",
            run_name="test run",
            wait=True,
        )

    @patch("webbrowser.open_new_tab")
    def test_ui(self, open_new_tab):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(ui, [], obj=config)

        assert result.exit_code == 0
        open_new_tab.assert_called_with("https://example.com")

    def test_compile(self):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(
            compile, ["-p", "pipe", "-i", "img", "-o", "output"], obj=config
        )

        assert result.exit_code == 0
        context_helper.kfp_client.compile.assert_called_with(
            image="img",
            image_pull_policy="Always",
            output="output",
            pipeline="pipe",
        )

    def test_upload_pipeline(self):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(
            upload_pipeline, ["-p", "pipe", "-i", "img"], obj=config
        )

        assert result.exit_code == 0
        context_helper.kfp_client.upload.assert_called_with(
            image="img", image_pull_policy="Always", pipeline="pipe"
        )

    def test_schedule(self):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(
            schedule, ["-c", "* * *", "-x", "test_experiment"], obj=config
        )

        assert result.exit_code == 0
        context_helper.kfp_client.schedule.assert_called_with(
            "test_experiment", "* * *"
        )

    @patch.object(Path, "cwd")
    def test_init(self, cwd):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        context_helper.context.project_name = "Test Project"
        context_helper.context.project_path.name = "test_project_path"
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            cwd.return_value = path
            os.makedirs(path.joinpath("conf/base"))
            result = runner.invoke(init, ["http:/kubeflow"], obj=config)

            assert result.exit_code == 0
            assert result.output.startswith("Configuration generated in ")
            with open(path.joinpath("conf/base/kubeflow.yaml"), "r") as f:
                content = "\n".join(f.readlines())
                assert "host: http:/kubeflow" in content
