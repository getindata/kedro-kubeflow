"""Test kedro_kubeflow module."""

import os
import unittest
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from kedro.pipeline import Pipeline

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.kfpclient import KubeflowClient
from kedro_kubeflow.utils import strip_margin


class TestKubeflowClient(unittest.TestCase):
    def create_experiment(self, id="123"):
        return type("obj", (object,), {"id": id})

    def create_empty_pipelines_list(self):
        return type(
            "obj",
            (object,),
            {"pipelines": None},
        )

    def create_pipelines_list(self):
        return type(
            "obj",
            (object,),
            {
                "pipelines": [
                    type(
                        "obj", (object,), {"name": "somename", "id": "someid"}
                    )
                ]
            },
        )

    def create_recurring_jobs_list(self, id="pipeline_id"):
        return type(
            "obj",
            (object,),
            {
                "jobs": [
                    type(
                        "obj",
                        (object,),
                        {
                            "id": "jobid",
                            "pipeline_spec": type(
                                "obj", (object,), {"pipeline_id": id}
                            ),
                        },
                    )
                ]
            },
        )

    def test_should_list_pipelines_tabularized(self):
        # given
        self.kfp_client_mock.list_pipelines.return_value = (
            self.create_pipelines_list()
        )

        # when
        output = self.client_under_test.list_pipelines()

        # then
        expected_output = """
        |Name      ID
        |--------  ------
        |somename  someid"""
        self.assertEqual(output, strip_margin(expected_output))

    def test_should_run_pipeline_without_waiting(self):
        # given
        run_mock = unittest.mock.MagicMock()
        self.kfp_client_mock.create_run_from_pipeline_func.return_value = (
            run_mock
        )

        # when
        self.client_under_test.run_once(
            run_name="unittest",
            pipeline="pipeline",
            image="unittest-image",
            experiment_name="experiment",
            wait=False,
        )

        # then
        self.kfp_client_mock.create_run_from_pipeline_func.assert_called()
        run_mock.wait_for_run_completion.assert_not_called()
        (
            args,
            kwargs,
        ) = self.kfp_client_mock.create_run_from_pipeline_func.call_args
        assert kwargs == {
            "arguments": {},
            "experiment_name": "experiment",
            "run_name": "unittest",
        }

    def test_should_run_pipeline_and_wait(self):
        # given
        run_mock = unittest.mock.MagicMock()
        self.kfp_client_mock.create_run_from_pipeline_func.return_value = (
            run_mock
        )

        # when
        self.client_under_test.run_once(
            run_name="unittest",
            pipeline="pipeline",
            image="unittest-image",
            experiment_name="experiment",
            wait=True,
        )

        # then
        self.kfp_client_mock.create_run_from_pipeline_func.assert_called()
        run_mock.wait_for_run_completion.assert_called()

    def test_should_compile_pipeline(self):
        with NamedTemporaryFile(suffix=".yaml") as f:
            # when
            self.client_under_test.compile(
                pipeline="pipeline", image="unittest-image", output=f.name
            )

            # then
            with open(f.name) as yamlfile:
                assert "generateName: my-awesome-project-" in yamlfile.read()

    @patch("google.oauth2.id_token.fetch_id_token")
    @patch("kedro_kubeflow.kfpclient.Client")
    def test_should_use_jwt_token_in_kfp_client(
        self, kfp_client_mock, fetch_id_token_mock
    ):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        fetch_id_token_mock.return_value = "unittest-token"

        # when
        self.client_under_test = KubeflowClient(
            PluginConfig({"host": "http://unittest", "run_config": {}}),
            None,
            None,
        )

        # then
        kfp_client_mock.assert_called_with(
            "http://unittest", existing_token="unittest-token"
        )

    def test_should_schedule_pipeline(self):
        # given
        self.kfp_client_mock.get_experiment.return_value = (
            self.create_experiment()
        )
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_pipelines_list()
        )

        # when
        self.client_under_test.schedule(
            experiment_name="EXPERIMENT",
            cron_expression="0 * * * * *",
        )

        # then
        self.kfp_client_mock.get_experiment.assert_called()
        self.kfp_client_mock.create_experiment.assert_not_called()
        self.kfp_client_mock.create_recurring_run.assert_called_with(
            "123",
            "my-awesome-project on 0 * * * * *",
            cron_expression="0 * * * * *",
            pipeline_id="someid",
        )

    def test_should_schedule_pipeline_and_create_experiment_if_needed(self):
        # given
        self.kfp_client_mock.get_experiment.side_effect = ValueError(
            "No experiment is found with name ...."
        )
        self.kfp_client_mock.create_experiment.return_value = (
            self.create_experiment()
        )
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_pipelines_list()
        )

        # when
        self.client_under_test.schedule(
            experiment_name="EXPERIMENT",
            cron_expression="0 * * * * *",
        )

        # then
        self.kfp_client_mock.get_experiment.assert_called()
        self.kfp_client_mock.create_experiment.assert_called()
        self.kfp_client_mock.create_recurring_run.assert_called_with(
            "123",
            "my-awesome-project on 0 * * * * *",
            cron_expression="0 * * * * *",
            pipeline_id="someid",
        )

    def test_should_disable_old_runs_before_schedule(self):
        # given
        self.kfp_client_mock.get_experiment.return_value = (
            self.create_experiment()
        )
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_pipelines_list()
        )
        self.kfp_client_mock.list_recurring_runs.return_value = (
            self.create_recurring_jobs_list("someid")
        )

        # when
        self.client_under_test.schedule(
            experiment_name="EXPERIMENT",
            cron_expression="0 * * * * *",
        )

        # then
        self.kfp_client_mock.get_experiment.assert_called()
        self.kfp_client_mock.create_experiment.assert_not_called()
        self.kfp_client_mock.jobs.delete_job.assert_called()
        self.kfp_client_mock.create_recurring_run.assert_called_with(
            "123",
            "my-awesome-project on 0 * * * * *",
            cron_expression="0 * * * * *",
            pipeline_id="someid",
        )

    def test_should_upload_new_pipeline(self):
        # given
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_empty_pipelines_list()
        )

        # when
        self.client_under_test.upload(
            pipeline="pipeline",
            image="unittest-image",
            image_pull_policy="Always",
        )

        # then
        self.kfp_client_mock.pipeline_uploads.upload_pipeline.assert_called()
        self.kfp_client_mock.pipeline_uploads.upload_pipeline_version.assert_not_called()

    def test_should_upload_new_version_of_existing_pipeline(self):
        # given
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_pipelines_list()
        )

        # when
        self.client_under_test.upload(
            pipeline="pipeline",
            image="unittest-image",
            image_pull_policy="Always",
        )

        # then
        self.kfp_client_mock.pipeline_uploads.upload_pipeline.assert_not_called()
        self.kfp_client_mock.pipeline_uploads.upload_pipeline_version.assert_called()

    @patch("kedro_kubeflow.kfpclient.Client")
    def create_client(self, config, params, kfp_client_mock):
        project_name = "my-awesome-project"
        context = type(
            "obj",
            (object,),
            {
                "params": params,
                "pipelines": {"pipeline": Pipeline([])},
            },
        )
        self.client_under_test = KubeflowClient(
            PluginConfig({"host": "http://unittest", "run_config": config}),
            project_name,
            context,
        )
        self.client_under_test.client = kfp_client_mock
        self.kfp_client_mock = self.client_under_test.client

    def mock_mlflow(self, enabled=False):
        def fakeimport(name, *args, **kw):
            if not enabled and name == "mlflow":
                raise ImportError
            return self.realimport(name, *args, **kw)

        __builtins__["__import__"] = fakeimport

    def setUp(self):
        self.realimport = __builtins__["__import__"]
        self.mock_mlflow(False)
        self.create_client({}, {})

    def tearDown(self):
        os.environ["IAP_CLIENT_ID"] = ""
