import os
import unittest
import unittest.mock as um
from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kedro_kubeflow.cli import (
    WAIT_TIMEOUT,
    compile,
    delete_pipeline_volume,
    init,
    kubeflow_group,
    list_pipelines,
    mlflow_start,
    run_once,
    schedule,
    ui,
    upload_pipeline,
)
from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.context_helper import ContextHelper

test_config = PluginConfig(
    **{
        "host": "https://example.com",
        "run_config": {
            "image": "gcr.io/project-image/test",
            "image_pull_policy": "Always",
            "experiment_name": "Test Experiment",
            "run_name": "test run",
            "wait_for_completion": False,
            "volume": {
                "storageclass": "default",
                "size": "3Gi",
                "access_modes": ["ReadWriteOnce"],
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
            run_once,
            [
                "-i",
                "new_img",
                "-p",
                "new_pipe",
                "--experiment-namespace",
                "my-ns",
                "--param",
                "key1:some value",
            ],
            obj=config,
        )
        self.assertEqual(result.exit_code, 0)
        context_helper.kfp_client.run_once.assert_called_with(
            experiment_name="Test Experiment",
            image="new_img",
            image_pull_policy="Always",
            pipeline="new_pipe",
            run_name="test run",
            wait=False,
            timeout=WAIT_TIMEOUT,
            experiment_namespace="my-ns",
            parameters={"key1": "some value"},
        )

    def test_run_once_return_values(self):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        config = dict(context_helper=context_helper)
        runner = CliRunner()
        context_helper.kfp_client.run_once.return_value = {
            "status": "succeeded",
            "error": "",
        }

        result = runner.invoke(
            run_once,
            [
                "-i",
                "new_img",
                "-p",
                "new_pipe",
                "--wait-for-completion",
                "--experiment-namespace",
                "my-ns",
                "--param",
                "key1:some value",
            ],
            obj=config,
        )
        self.assertEqual(result.exit_code, 0)
        context_helper.kfp_client.run_once.assert_called_with(
            experiment_name="Test Experiment",
            image="new_img",
            image_pull_policy="Always",
            pipeline="new_pipe",
            run_name="test run",
            wait=True,
            timeout=WAIT_TIMEOUT,
            experiment_namespace="my-ns",
            parameters={"key1": "some value"},
        )
        context_helper.kfp_client.run_once.return_value = {
            "status": "error",
            "error": "Simulated error",
        }
        result = runner.invoke(
            run_once,
            [
                "-i",
                "new_img",
                "-p",
                "new_pipe",
                "--wait-for-completion",
                "--experiment-namespace",
                "my-ns",
                "--param",
                "key1:some value",
            ],
            obj=config,
        )
        self.assertEqual(result.exit_code, 1)

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

        result = runner.invoke(compile, ["-p", "pipe", "-i", "img", "-o", "output"], obj=config)

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
        context_helper.env = "kubeflow-env"
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(upload_pipeline, ["-p", "pipe", "-i", "img"], obj=config)

        assert result.exit_code == 0
        context_helper.kfp_client.upload.assert_called_with(
            image="img",
            image_pull_policy="Always",
            pipeline_name="pipe",
            env="kubeflow-env",
        )

    def test_schedule(self):
        context_helper = MagicMock(ContextHelper)
        context_helper.config = test_config
        context_helper.env = "kubeflow-env"
        config = dict(context_helper=context_helper)
        runner = CliRunner()

        result = runner.invoke(
            schedule,
            [
                "-c",
                "* * *",
                "-x",
                "test_experiment",
                "-p",
                "my-pipeline",
                "--param",
                "key1:some value",
            ],
            obj=config,
        )

        assert result.exit_code == 0
        context_helper.kfp_client.schedule.assert_called_with(
            "my-pipeline",
            "test_experiment",
            None,
            "* * *",
            run_name="test run",
            parameters={"key1": "some value"},
            env="kubeflow-env",
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
            result = runner.invoke(init, ["http://kubeflow"], obj=config)

            assert result.exit_code == 0
            assert result.output.startswith("Configuration generated in ")
            with open(path.joinpath("conf/base/kubeflow.yaml"), "r") as f:
                assert "host: http://kubeflow" in f.read()

    @patch.object(Path, "cwd")
    def test_init_with_github_actions(self, cwd):
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
            result = runner.invoke(init, ["--with-github-actions", "http://kubeflow"], obj=config)

            assert result.exit_code == 0
            on_push_actions = path / ".github" / "workflows" / "on-push.yml"
            assert on_push_actions.exists()
            with open(on_push_actions, "r") as f:
                assert "kedro kubeflow run-once" in f.read()
            on_merge_actions = path / ".github" / "workflows" / "on-merge-to-master.yml"
            assert on_merge_actions.exists()
            with open(on_merge_actions, "r") as f:
                content = f.read()
                assert "kedro kubeflow upload-pipeline" in content
                assert "kedro kubeflow schedule" in content

    @patch("mlflow.start_run")
    @patch("mlflow.set_tag")
    @patch("mlflow.get_experiment_by_name")
    def test_mlflow_start(self, get_experiment_by_name_mock, set_tag_mock, start_run_mock):
        context_helper = MagicMock(ContextHelper)
        config = dict(context_helper=context_helper)
        runner = CliRunner()
        get_experiment_by_name_mock.return_value = type("obj", (object,), {"experiment_id": 47})
        start_run_mock.return_value = namedtuple("InfoObject", "info")(
            namedtuple("RunIdObject", "run_id")("MLFLOW_RUN_ID")
        )

        with TemporaryDirectory() as temp_dir:
            run_id_file_path = f"{temp_dir}/run_id"
            result = runner.invoke(
                mlflow_start,
                ["KUBEFLOW_RUN_ID", "--output", run_id_file_path],
                obj=config,
            )

            assert "Started run: MLFLOW_RUN_ID" in result.output
            assert result.exit_code == 0
            with open(run_id_file_path) as f:
                assert f.read() == "MLFLOW_RUN_ID"

        set_tag_mock.assert_called_with("kubeflow_run_id", "KUBEFLOW_RUN_ID")

    @patch("kubernetes.client")
    @patch("kubernetes.config")
    def test_delete_pipeline_volume(self, k8s_config_mock, k8s_client_mock):
        with um.patch("builtins.open", um.mock_open(read_data="unittest-namespace")):
            runner = CliRunner()
            result = runner.invoke(
                delete_pipeline_volume,
                ["workflow-name"],
            )
            assert result.exit_code == 0
            core_api = k8s_client_mock.CoreV1Api()
            core_api.delete_namespaced_persistent_volume_claim.assert_called_with("workflow-name", "unittest-namespace")

    @patch.object(ContextHelper, "init")
    def test_handle_env_arguments(self, context_helper_init):
        for testname, env_var, cli, expected in [
            (
                "CLI arg should have preference over environment variable",
                "pipelines",
                "custom",
                "custom",
            ),
            (
                "KEDRO_ENV should be taken into account",
                "pipelines",
                None,
                "pipelines",
            ),
            ("CLI arg should be taken into account", None, "custom", "custom"),
            ("default value should be set", None, None, "local"),
        ]:
            runner = CliRunner()
            with self.subTest(msg=testname):
                cli = ["--env", cli] if cli else []
                env = dict(KEDRO_ENV=env_var) if env_var else dict()

                runner.invoke(kubeflow_group, cli + ["compile", "--help"], env=env)
                context_helper_init.assert_called_with(None, expected)
