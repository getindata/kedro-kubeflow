"""Test kedro_kubeflow module."""

import unittest
from unittest.mock import MagicMock, patch

from kedro_kubeflow.utils import strip_margin
from kedro_kubeflow.vertex_ai.client import VertexAIPipelinesClient


class TestKubeflowClient(unittest.TestCase):
    def create_client(self):
        return VertexAIPipelinesClient(MagicMock(), MagicMock(), MagicMock())

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
            ai_client.list_jobs.return_value = [
                type("pipeline", (), {"name": "run1", "id": "abc123"}),
                type("pipeline", (), {"name": "run2", "id": "def456"}),
            ]

            client_under_test = self.create_client()
            tabulation = client_under_test.list_pipelines()

            expected_output = """
            |Name    ID
            |------  ------
            |run1    abc123
            |run2    def456"""
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
                MagicMock("pipeline"), "image", "0 0 12 * *", "test-run"
            )

            ai_client.create_schedule_from_job_spec.assert_called_once()
