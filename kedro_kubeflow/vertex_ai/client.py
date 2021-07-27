"""
Vertex AI Pipelines specific client, based on AIPlatformClient.
"""

import logging
import os
from tempfile import NamedTemporaryFile

from kfp.v2 import compiler
from kfp.v2.google.client import AIPlatformClient
from tabulate import tabulate

from .generator import PipelineGenerator


class VertexAIPipelinesClient:
    """
    Client for Vertex AI Pipelines.
    """

    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.generator = PipelineGenerator(config, project_name, context)
        self.api_client = AIPlatformClient(
            project_id=config.project_id, region=config.region
        )
        self.run_config = config.run_config

    def list_pipelines(self):
        """
        List all the jobs (current and historical) on Vertex AI Pipelines
        :return:
        """
        pipelines = self.api_client.list_jobs()["pipelineJobs"]
        return tabulate(
            map(lambda x: [x["displayName"], x["name"]], pipelines),
            headers=["Name", "ID"],
        )

    def run_once(
        self,
        pipeline,
        image,
        experiment_name,
        run_name,
        wait=False,
        image_pull_policy="IfNotPresent",
    ):
        """
        Runs the pipeline in Vertex AI Pipelines
        :param pipeline:
        :param image:
        :param experiment_name:
        :param run_name:
        :param wait:
        :param image_pull_policy:
        :return:
        """
        with NamedTemporaryFile(
            mode="rt", prefix="kedro-kubeflow", suffix=".json"
        ) as spec_output:
            self.compile(
                pipeline,
                image,
                output=spec_output.name,
                image_pull_policy=image_pull_policy,
            )

            run = self.api_client.create_run_from_job_spec(
                service_account=os.getenv("SERVICE_ACCOUNT"),
                job_spec_path=spec_output.name,
                job_id=run_name,
                pipeline_root=f"gs://{self.run_config.root}",
                parameter_values={},
                enable_caching=False,
            )
            self.log.info("Run created %s", str(run))
            return run

    def compile(
        self,
        pipeline,
        image,
        output,
        image_pull_policy="IfNotPresent",
    ):
        """
        Creates json file in given local output path
        :param pipeline:
        :param image:
        :param output:
        :param image_pull_policy:
        :return:
        """
        token = os.getenv("MLFLOW_TRACKING_TOKEN")
        pipeline_func = self.generator.generate_pipeline(
            pipeline, image, image_pull_policy, token
        )
        compiler.Compiler().compile(
            pipeline_func=pipeline_func,
            package_path=output,
        )
        self.log.info(
            "Generated pipeline definition was saved to %s", str(output)
        )

    def upload(self, pipeline, image, image_pull_policy="IfNotPresent"):
        """
        Upload is not supported by Vertex AI Pipelines
        :param pipeline:
        :param image:
        :param image_pull_policy:
        :return:
        """
        raise NotImplementedError("Upload is not supported for VertexAI")

    def schedule(
        self,
        pipeline,
        image,
        cron_expression,
        image_pull_policy="IfNotPresent",
    ):
        """
        Schedule pipeline to Vertex AI with given cron expression
        :param pipeline:
        :param image:
        :param cron_expression:
        :param image_pull_policy:
        :return:
        """
        with NamedTemporaryFile(
            mode="rt", prefix="kedro-kubeflow", suffix=".json"
        ) as spec_output:
            self.compile(
                pipeline,
                image,
                output=spec_output.name,
                image_pull_policy=image_pull_policy,
            )
            self.api_client.create_schedule_from_job_spec(
                job_spec_path=spec_output.name,
                schedule=cron_expression,
                parameter_values={},
            )

            self.log.info("Pipeline scheduled to %s", cron_expression)
