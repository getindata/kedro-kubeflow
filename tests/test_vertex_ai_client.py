"""Test kedro_kubeflow module."""

import unittest
from unittest.mock import MagicMock, patch

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.utils import strip_margin
from kedro_kubeflow.vertex_ai.client import VertexAIPipelinesClient


class TestKubeflowClient(unittest.TestCase):
    @patch("kedro_kubeflow.vertex_ai.client.CloudSchedulerClient")
    def create_client(self, cloud_scheduler_client_mock):
        self.cloud_scheduler_client_mock = (
            cloud_scheduler_client_mock.return_value
        )
        config = PluginConfig(
            {
                "project_id": "PROJECT_ID",
                "region": "REGION",
                "run_config": {"image": "IMAGE", "root": "BUCKET/PREFIX"},
            }
        )
        return VertexAIPipelinesClient(config, MagicMock(), MagicMock())

    def test_compile(self):
        with patch(
            "kedro_kubeflow.vertex_ai.generator.PipelineGenerator"
        ), patch("kedro_kubeflow.vertex_ai.client.AIPlatformClient"), patch(
            "kfp.v2.compiler.Compiler"
        ) as Compiler:
            compiler = Compiler.return_value

            client_under_test = self.create_client()
            client_under_test.compile(
                MagicMock("pipeline"), "image", "some_path"
            )

            compiler.compile.assert_called_once()

    def test_upload_not_supported_by_vertex_ai(self):
        with patch(
            "kedro_kubeflow.vertex_ai.generator.PipelineGenerator"
        ), patch("kedro_kubeflow.vertex_ai.client.AIPlatformClient"):
            client_under_test = self.create_client()

            with self.assertRaises(NotImplementedError):
                client_under_test.upload(MagicMock("pipeline"), "image")

    def test_run_once(self):
        with patch(
            "kedro_kubeflow.vertex_ai.generator.PipelineGenerator"
        ), patch(
            "kedro_kubeflow.vertex_ai.client.AIPlatformClient"
        ) as AIPlatformClient, patch(
            "kfp.v2.compiler.Compiler"
        ):
            ai_client = AIPlatformClient.return_value

            run_mock = {"run": "mock"}
            ai_client.create_run_from_job_spec.return_value = run_mock
            client_under_test = self.create_client()
            run = client_under_test.run_once(
                MagicMock("pipeline"), "image", None, "test-run"
            )

            assert run_mock == run

    def test_should_list_pipelines(self):
        with patch(
            "kedro_kubeflow.vertex_ai.client.AIPlatformClient"
        ) as AIPlatformClient:
            ai_client = AIPlatformClient.return_value
            ai_client.list_jobs.return_value = {
                "pipelineJobs": [
                    {
                        "displayName": "run1",
                        "name": "projects/29350373243/locations/"
                        "europe-west4/pipelineJobs/run1",
                    },
                    {
                        "displayName": "run2",
                        "name": "projects/29350373243/locations/"
                        "europe-west4/pipelineJobs/run2",
                    },
                    {
                        "name": "projects/123/locations/"
                        "europe-west4/pipelineJobs/no-display-name",
                    },
                ]
            }

            client_under_test = self.create_client()
            tabulation = client_under_test.list_pipelines()

            expected_output = """
            |Name    ID
            |------  ----------------------------------------------------------------
            |run1    projects/29350373243/locations/europe-west4/pipelineJobs/run1
            |run2    projects/29350373243/locations/europe-west4/pipelineJobs/run2
            |        projects/123/locations/europe-west4/pipelineJobs/no-display-name"""
            assert tabulation == strip_margin(expected_output)

    def test_should_schedule_pipeline(self):
        with patch(
            "kedro_kubeflow.vertex_ai.generator.PipelineGenerator"
        ), patch(
            "kedro_kubeflow.vertex_ai.client.AIPlatformClient"
        ) as AIPlatformClient, patch(
            "kfp.v2.compiler.Compiler"
        ):
            ai_client = AIPlatformClient.return_value

            client_under_test = self.create_client()
            client_under_test.schedule(
                MagicMock("pipeline"), None, None, "0 0 12 * *"
            )

            ai_client.create_schedule_from_job_spec.assert_called_once()
            schedule_args = ai_client.create_schedule_from_job_spec.call_args
            assert schedule_args.kwargs["time_zone"] == "Etc/UTC"
            assert schedule_args.kwargs["enable_caching"] is False
            assert schedule_args.kwargs["schedule"] == "0 0 12 * *"
            assert (
                schedule_args.kwargs["pipeline_root"] == "gs://BUCKET/PREFIX"
            )

    def test_should_remove_old_schedule(self):
        def mock_job(job_name, pipeline_name=None):
            if pipeline_name:
                body = (
                    '{"pipelineSpec": {"pipelineInfo": {"name": "'
                    + pipeline_name
                    + '"}}}'
                )
            else:
                body = ""
            return type(
                "obj",
                (object,),
                {
                    "schedule": "* * * * *",
                    "name": job_name,
                    "http_target": type("obj", (object,), {"body": body}),
                },
            )

        with patch(
            "kedro_kubeflow.vertex_ai.client.PipelineGenerator"
        ) as generator, patch(
            "kedro_kubeflow.vertex_ai.client.AIPlatformClient"
        ) as AIPlatformClient, patch(
            "kfp.v2.compiler.Compiler"
        ):
            # given
            ai_client = AIPlatformClient.return_value
            client_under_test = self.create_client()
            generator.return_value.get_pipeline_name.return_value = (
                "unittest-pipeline"
            )
            self.cloud_scheduler_client_mock.list_jobs.return_value = [
                # not removed (some other job)
                mock_job(job_name="some-job"),
                # not removed (some other pipeline)
                mock_job(
                    job_name="projects/.../locations/.../jobs/pipeline_pipeline_abc",
                    pipeline_name="some-other-pipeline",
                ),
                # removed
                mock_job(
                    job_name="projects/.../locations/.../jobs/pipeline_pipeline_def",
                    pipeline_name="unittest-pipeline",
                ),
            ]

            # when
            client_under_test.schedule(
                MagicMock("pipeline"), None, None, "0 0 12 * *"
            )

            # then
            ai_client.create_schedule_from_job_spec.assert_called_once()
            self.cloud_scheduler_client_mock.delete_job.assert_called_once()
            delete_args = self.cloud_scheduler_client_mock.delete_job.call_args
            assert (
                delete_args.kwargs["name"]
                == "projects/.../locations/.../jobs/pipeline_pipeline_def"
            )
