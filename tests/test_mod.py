"""Test kedro_kubeflow module."""

import os
import re
import unittest
from unittest.mock import patch
from tempfile import NamedTemporaryFile

import kfp
from google.auth.exceptions import DefaultCredentialsError

from kedro_kubeflow.kfpclient import KubeflowClient
from kedro.pipeline import Pipeline, node


def identity(input1: str):
    return input1  # pragma: no cover


class TestKubeflowClient(unittest.TestCase):
    @staticmethod
    def _strip_margin(text: str) -> str:
        return re.sub("\n[ \t]*\\|", "\n", text).strip()

    def create_pipeline(self):
        return Pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
            ]
        )

    def create_experiment(self, id="123"):
        return type("obj", (object,), {"id": id})

    def create_pipelines_list(self):
        return type(
            "obj",
            (object,),
            {
                "pipelines": [
                    type("obj", (object,), {"name": "somename", "id": "someid"})
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
        self.kfp_client_mock.list_pipelines.return_value = self.create_pipelines_list()

        # when
        output = self.client_under_test.list_pipelines()

        # then
        expected_output = """
        |Name      ID
        |--------  ------
        |somename  someid"""
        self.assertEqual(output, TestKubeflowClient._strip_margin(expected_output))

    def test_should_run_pipeline_without_waiting(self):
        # given
        run_mock = unittest.mock.MagicMock()
        self.kfp_client_mock.create_run_from_pipeline_func.return_value = run_mock

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
        args, kwargs = self.kfp_client_mock.create_run_from_pipeline_func.call_args
        assert kwargs == {
            "arguments": {},
            "experiment_name": "experiment",
            "run_name": "unittest",
        }

        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            args[0]()

        assert dsl_pipeline.ops["node1"].image == "unittest-image"
        assert dsl_pipeline.ops["node1"].container.image_pull_policy == "IfNotPresent"

    def test_should_run_pipeline_and_wait(self):
        # given
        run_mock = unittest.mock.MagicMock()
        self.kfp_client_mock.create_run_from_pipeline_func.return_value = run_mock

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
        self.client_under_test = KubeflowClient({"host": "http://unittest"}, None, None)

        # then
        kfp_client_mock.assert_called_with(
            "http://unittest", existing_token="unittest-token"
        )

    @patch("google.oauth2.id_token.fetch_id_token")
    @patch("kedro_kubeflow.kfpclient.Client")
    def test_should_warn_if_trying_to_use_default_creds(
        self, kfp_client_mock, fetch_id_token_mock
    ):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        fetch_id_token_mock.side_effect = DefaultCredentialsError()

        with self.assertLogs("kedro_kubeflow.kfpclient", level="WARNING") as cm:
            # when
            self.client_under_test = KubeflowClient(
                {"host": "http://unittest"}, None, None
            )
            # then
            assert (
                "this authentication method does not work with default credentials"
                in cm.output[0]
            )

        # then
        kfp_client_mock.assert_called_with("http://unittest", existing_token=None)

    @patch("google.oauth2.id_token.fetch_id_token")
    @patch("kedro_kubeflow.kfpclient.Client")
    def test_should_error_on_invalid_creds(self, kfp_client_mock, fetch_id_token_mock):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        fetch_id_token_mock.side_effect = Exception()

        with self.assertLogs("kedro_kubeflow.kfpclient", level="ERROR") as cm:
            # when
            self.client_under_test = KubeflowClient(
                {"host": "http://unittest"}, None, None
            )
            # then
            assert "Failed to obtain IAP access token" in cm.output[0]

        # then
        kfp_client_mock.assert_called_with("http://unittest", existing_token=None)

    def test_should_modify_pull_policy_in_run(self):
        # given
        run_mock = unittest.mock.MagicMock()
        self.kfp_client_mock.create_run_from_pipeline_func.return_value = run_mock

        # when
        self.client_under_test.run_once(
            run_name="unittest",
            pipeline="pipeline",
            image="unittest-image",
            experiment_name="experiment",
            wait=False,
            image_pull_policy="Never",
        )

        # then
        args, kwargs = self.kfp_client_mock.create_run_from_pipeline_func.call_args
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            args[0]()

        assert dsl_pipeline.ops["node1"].image == "unittest-image"
        assert dsl_pipeline.ops["node1"].container.image_pull_policy == "Never"

    def test_should_compile_pipeline_with_modified_pull_policy(self):
        with NamedTemporaryFile(suffix=".yaml") as f:
            # when
            self.client_under_test.compile(
                pipeline="pipeline",
                image="unittest-image",
                output=f.name,
                image_pull_policy="Always",
            )

            # then
            with open(f.name) as yamlfile:
                compiled_file = yamlfile.read()
                assert "generateName: my-awesome-project-" in compiled_file
                assert "imagePullPolicy: Always" in compiled_file

    def test_should_schedule_pipeline(self):
        # given
        self.kfp_client_mock.get_experiment.return_value = self.create_experiment()
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_pipelines_list()
        )

        # when
        self.client_under_test.schedule(
            experiment_name="EXPERIMENT", cron_expression="0 * * * * *",
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
        self.kfp_client_mock.get_experiment.side_effect = Exception()
        self.kfp_client_mock.create_experiment.return_value = self.create_experiment()
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_pipelines_list()
        )

        # when
        self.client_under_test.schedule(
            experiment_name="EXPERIMENT", cron_expression="0 * * * * *",
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
        self.kfp_client_mock.get_experiment.return_value = self.create_experiment()
        self.kfp_client_mock.pipelines = unittest.mock.MagicMock()
        self.kfp_client_mock.pipelines.list_pipelines.return_value = (
            self.create_pipelines_list()
        )
        self.kfp_client_mock.list_recurring_runs.return_value = self.create_recurring_jobs_list(
            "someid"
        )

        # when
        self.client_under_test.schedule(
            experiment_name="EXPERIMENT", cron_expression="0 * * * * *",
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
        self.kfp_client_mock.pipelines.list_pipelines.side_effect = Exception()

        # when
        self.client_under_test.upload(
            pipeline="pipeline", image="unittest-image", image_pull_policy="Always",
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
            pipeline="pipeline", image="unittest-image", image_pull_policy="Always",
        )

        # then
        self.kfp_client_mock.pipeline_uploads.upload_pipeline.assert_not_called()
        self.kfp_client_mock.pipeline_uploads.upload_pipeline_version.assert_called()

    def tearDown(self):
        os.environ["IAP_CLIENT_ID"] = ""

    @patch("kedro_kubeflow.kfpclient.Client")
    def setUp(self, kfp_client_mock):
        project_name = "my-awesome-project"
        context = type(
            "obj", (object,), {"pipelines": {"pipeline": self.create_pipeline()}},
        )
        self.client_under_test = KubeflowClient(
            {"host": "http://unittest"}, project_name, context
        )
        self.kfp_client_mock = self.client_under_test.client
