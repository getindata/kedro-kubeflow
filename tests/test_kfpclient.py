"""Test kedro_kubeflow module."""

import os
import unittest
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from kfp import dsl

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.generators.one_pod_pipeline_generator import (
    OnePodPipelineGenerator,
)
from kedro_kubeflow.kfpclient import KubeflowClient
from kedro_kubeflow.utils import strip_margin
from tests.common import MinimalConfigMixin

TEST_TIMEOUT_DUMMY = 60 * 60


class TestKubeflowClient(unittest.TestCase, MinimalConfigMixin):
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
            {"pipelines": [type("obj", (object,), {"name": "somename", "id": "someid"})]},
        )

    def create_recurring_jobs_list(self, job_name="job_name"):
        return type(
            "obj",
            (object,),
            {
                "jobs": [
                    type(
                        "obj",
                        (object,),
                        {
                            "name": job_name,
                            "id": job_name + "ID",
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
        self.assertEqual(output, strip_margin(expected_output))

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
            timeout=TEST_TIMEOUT_DUMMY,
            experiment_namespace="exp_namespace",
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
            "namespace": "exp_namespace",
        }

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
            timeout=TEST_TIMEOUT_DUMMY,
            experiment_namespace=None,
        )

        # then
        self.kfp_client_mock.create_run_from_pipeline_func.assert_called()
        run_mock.wait_for_run_completion.assert_called()

    def test_should_run_pipeline_adjusting_the_name(self):
        # given
        run_mock = unittest.mock.MagicMock()
        self.kfp_client_mock.create_run_from_pipeline_func.return_value = run_mock

        # when
        self.client_under_test.run_once(
            run_name="unittest for region {region}",
            pipeline="pipeline",
            image="unittest-image",
            experiment_name="experiment",
            wait=False,
            timeout=TEST_TIMEOUT_DUMMY,
            experiment_namespace="exp_namespace",
            parameters={"region": "ABC"},
        )

        # then
        self.kfp_client_mock.create_run_from_pipeline_func.assert_called()
        run_mock.wait_for_run_completion.assert_not_called()
        (
            args,
            kwargs,
        ) = self.kfp_client_mock.create_run_from_pipeline_func.call_args
        assert kwargs == {
            "arguments": {"region": "ABC"},
            "experiment_name": "experiment",
            "run_name": "unittest for region ABC",
            "namespace": "exp_namespace",
        }

    def test_should_compile_pipeline(self):
        with NamedTemporaryFile(suffix=".yaml") as f:
            # when
            self.client_under_test.compile(pipeline="pipeline", image="unittest-image", output=f.name)

            # then
            with open(f.name) as yamlfile:
                assert "generateName: my-awesome-project-" in yamlfile.read()

    @patch("kedro_kubeflow.kfpclient.AuthHandler")
    @patch("kedro_kubeflow.kfpclient.PodPerNodePipelineGenerator")
    @patch("kedro_kubeflow.kfpclient.Client")
    def test_should_use_jwt_token_in_kfp_client(self, kfp_client_mock, pipeline_generator_mock, auth_handler_mock):
        # given
        os.environ["IAP_CLIENT_ID"] = "unittest-client-id"
        auth_handler_mock.return_value.obtain_id_token.return_value = "unittest-token"
        auth_handler_mock.return_value.obtain_dex_authservice_session.return_value = None

        # when
        self.client_under_test = KubeflowClient(
            PluginConfig(**self.minimal_config({"host": "http://unittest", "run_config": {}})),
            None,
            None,
        )

        # then
        kfp_client_mock.assert_called_with(host="http://unittest", existing_token="unittest-token")

    @patch("kedro_kubeflow.kfpclient.AuthHandler")
    @patch("kedro_kubeflow.kfpclient.PodPerNodePipelineGenerator")
    @patch("kedro_kubeflow.kfpclient.Client")
    def test_should_use_dex_session_in_kfp_client(self, kfp_client_mock, pipeline_generator_mock, auth_handler_mock):
        # given
        auth_handler_mock.return_value.obtain_id_token.return_value = None
        auth_handler_mock.return_value.obtain_dex_authservice_session.return_value = "session_id"

        # when
        self.client_under_test = KubeflowClient(
            PluginConfig(**self.minimal_config({"host": "http://unittest", "run_config": {}})),
            None,
            None,
        )

        # then
        kfp_client_mock.assert_called_with(host="http://unittest", cookies="authservice_session=session_id")

    def test_should_schedule_pipeline(self):
        # given
        self.kfp_client_mock.get_experiment.return_value = self.create_experiment()
        self.kfp_client_mock.get_pipeline_id.return_value = "someid"

        # when
        self.client_under_test.schedule(
            pipeline=None,
            experiment_name="EXPERIMENT",
            cron_expression="0 * * * * *",
            experiment_namespace=None,
            run_name="scheduled run of pipeline X",
            parameters={},
            env="kubeflow-env",
        )

        # then
        self.kfp_client_mock.get_experiment.assert_called()
        self.kfp_client_mock.create_experiment.assert_not_called()
        self.kfp_client_mock.create_recurring_run.assert_called_with(
            "123",
            "scheduled run of pipeline X",
            cron_expression="0 * * * * *",
            pipeline_id="someid",
            params={},
        )

    def test_should_schedule_pipeline_and_create_experiment_if_needed(self):
        # given
        self.kfp_client_mock.get_experiment.side_effect = ValueError("No experiment is found with name ....")
        self.kfp_client_mock.create_experiment.return_value = self.create_experiment()
        self.kfp_client_mock.get_pipeline_id.return_value = "someid"

        # when
        self.client_under_test.schedule(
            pipeline=None,
            experiment_name="EXPERIMENT",
            cron_expression="0 * * * * *",
            experiment_namespace=None,
            run_name="pipeline X",
            parameters={},
            env="kubeflow-env",
        )

        # then
        self.kfp_client_mock.get_experiment.assert_called()
        self.kfp_client_mock.create_experiment.assert_called()
        self.kfp_client_mock.create_recurring_run.assert_called_with(
            "123",
            "pipeline X",
            cron_expression="0 * * * * *",
            pipeline_id="someid",
            params={},
        )

    def test_should_disable_old_runs_before_schedule(self):
        # given
        self.kfp_client_mock.get_experiment.return_value = self.create_experiment()
        self.kfp_client_mock.get_pipeline_id.return_value = "someid"
        self.kfp_client_mock.list_recurring_runs.return_value = self.create_recurring_jobs_list(
            "scheduled run for region ABC"
        )

        # when
        self.client_under_test.schedule(
            pipeline=None,
            experiment_name="EXPERIMENT",
            cron_expression="0 * * * * *",
            experiment_namespace=None,
            run_name="scheduled run for region {region}",
            parameters={"region": "ABC"},
            env="kubeflow-env",
        )

        # then
        self.kfp_client_mock.get_experiment.assert_called()
        self.kfp_client_mock.create_experiment.assert_not_called()
        self.kfp_client_mock.jobs.delete_job.assert_called()
        self.kfp_client_mock.create_recurring_run.assert_called_with(
            "123",
            "scheduled run for region ABC",
            cron_expression="0 * * * * *",
            pipeline_id="someid",
            params={"region": "ABC"},
        )

    def test_should_upload_new_pipeline(self):
        # given
        self.create_client({"description": "Very Important Pipeline"})
        self.kfp_client_mock.get_pipeline_id.return_value = None

        # when
        self.client_under_test.upload(
            pipeline_name="pipeline_name",
            image="unittest-image",
            image_pull_policy="Always",
            env="kubeflow-env",
        )

        # then
        self.kfp_client_mock.pipeline_uploads.upload_pipeline.assert_called()
        self.kfp_client_mock.pipeline_uploads.upload_pipeline_version.assert_not_called()
        (
            args,
            kwargs,
        ) = self.kfp_client_mock.pipeline_uploads.upload_pipeline.call_args
        assert kwargs["name"] == "[my-awesome-project] pipeline_name (env: kubeflow-env)"
        assert kwargs["description"] == "Very Important Pipeline"

    @patch("kedro_kubeflow.kfpclient.Client")
    @patch("kedro.framework.context.context.KedroContext")
    def test_can_create_client_with_node_strategy_full(self, context, _):
        client = KubeflowClient(
            PluginConfig(
                **self.minimal_config(
                    {
                        "host": "http://unittest",
                        "run_config": {"node_merge_strategy": "full"},
                    }
                )
            ),
            "unit-test-project",
            context,
        )

        assert isinstance(client.generator, OnePodPipelineGenerator)

    def test_should_truncated_the_pipeline_name_to_100_characters_on_upload(
        self,
    ):
        # given
        self.create_client({"description": "Very Important Pipeline"})
        self.kfp_client_mock.get_pipeline_id.return_value = None

        # when
        self.client_under_test.upload(
            pipeline_name="pipeline_name",
            image="unittest-image",
            image_pull_policy="Always",
            env="kubeflow-env" + "1" * 100,
        )

        # then
        self.kfp_client_mock.pipeline_uploads.upload_pipeline.assert_called()
        self.kfp_client_mock.pipeline_uploads.upload_pipeline_version.assert_not_called()
        (
            args,
            kwargs,
        ) = self.kfp_client_mock.pipeline_uploads.upload_pipeline.call_args
        assert len(kwargs["name"]) == 100

    def test_should_upload_new_version_of_existing_pipeline(self):
        # given
        self.kfp_client_mock.get_pipeline_id.return_value = "123"

        # when
        self.client_under_test.upload(
            pipeline_name="pipeline",
            image="unittest-image",
            image_pull_policy="Always",
            env="kubeflow-env",
        )

        # then
        self.kfp_client_mock.pipeline_uploads.upload_pipeline.assert_not_called()
        self.kfp_client_mock.pipeline_uploads.upload_pipeline_version.assert_called()

    @patch("kedro_kubeflow.kfpclient.Client")
    def test_should_raise_error_if_invalid_node_merge_strategy(self, kfp_client_mock):
        with self.assertRaises(ValueError) as raises:
            KubeflowClient(
                PluginConfig(
                    **self.minimal_config(
                        {
                            "host": "http://unittest",
                            "run_config": {"node_merge_strategy": "other"},
                        }
                    )
                ),
                None,
                None,
            )
        assert "validation error" in str(raises.exception)

    @patch("kedro_kubeflow.kfpclient.PodPerNodePipelineGenerator")
    @patch("kedro_kubeflow.kfpclient.Client")
    def create_client(self, config, kfp_client_mock, pipeline_generator_mock):
        project_name = "my-awesome-project"
        self.client_under_test = KubeflowClient(
            PluginConfig(**self.minimal_config({"host": "http://unittest", "run_config": config})),
            project_name,
            None,  # context,
        )
        self.client_under_test.client = kfp_client_mock
        self.kfp_client_mock = self.client_under_test.client

        @dsl.pipeline(name=project_name)
        def empty_pipeline():
            pass

        self.client_under_test.generator.generate_pipeline.return_value = empty_pipeline

    def mock_mlflow(self, enabled=False):
        def fakeimport(name, *args, **kw):
            if not enabled and name == "mlflow":
                raise ImportError
            return self.realimport(name, *args, **kw)

        __builtins__["__import__"] = fakeimport

    def setUp(self):
        self.realimport = __builtins__["__import__"]
        self.mock_mlflow(False)
        self.create_client({})

    def tearDown(self):
        __builtins__["__import__"] = self.realimport
        os.environ["IAP_CLIENT_ID"] = ""
