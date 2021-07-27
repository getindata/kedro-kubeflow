import logging
import os
from tempfile import NamedTemporaryFile

from kfp.v2 import compiler
from kfp.v2.google.client import AIPlatformClient
from tabulate import tabulate

from .generator_v2 import PipelineGenerator


class KubeflowClient(object):
    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.generator = PipelineGenerator(config, project_name, context)
        self.api_client = AIPlatformClient(project_id='gid-ml-ops-sandbox',
                                           region='europe-west4')

    def list_pipelines(self):
        pipelines = self.api_client.list_jobs()
        return tabulate(
            map(lambda x: [x.name, x.id], pipelines), headers=["Name", "ID"]
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
        with NamedTemporaryFile(mode="rt", prefix="kedro-kubeflow", suffix=".json") as f:
            self.compile(pipeline, image, output=f.name,
                         image_pull_policy=image_pull_policy)

            run = self.api_client.create_run_from_job_spec(
                service_account=os.getenv('SERVICE_ACCOUNT'),
                job_spec_path=f.name,
                job_id=run_name,
                pipeline_root='gs://gid-ml-ops-sandbox-kubeflowpipelines-default/kedro-kubeflow',
                parameter_values={},
                enable_caching=False)
            print(f'Run created {run}')
            return run

    def compile(
            self, pipeline, image, output, image_pull_policy="IfNotPresent",
    ):
        token = os.getenv('MLFLOW_TRACKING_TOKEN') # TODO pass a param maybe?
        pipeline_func = self.generator.generate_pipeline(
            pipeline, image, image_pull_policy, token
        )
        compiler.Compiler().compile(
            pipeline_func=pipeline_func,
            package_path=output,
        )
        self.log.info("Generated pipeline definition was saved to %s" % output)

    def upload(self, pipeline, image, image_pull_policy="IfNotPresent"):
        raise NotImplementedError('Upload is not supported for VertexAI')

    def schedule(self, pipeline,
                 image,
                 cron_expression, image_pull_policy="IfNotPresent"):
        with NamedTemporaryFile(mode="rt", prefix="kedro-kubeflow", suffix=".json") as f:
            self.compile(pipeline, image, output=f.name,
                         image_pull_policy=image_pull_policy)
            self.api_client.create_schedule_from_job_spec(
                job_spec_path=f.name,
                schedule=cron_expression,
                parameter_values={}
            )

            self.log.info("Pipeline scheduled to %s", cron_expression)
