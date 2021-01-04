import re
import os
import logging
import json
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from kfp import Client, dsl
from kfp.compiler import Compiler
from kubernetes.client import V1EnvVar
from tabulate import tabulate
from typing import Dict, Set
from kedro.pipeline.node import Node


IAP_CLIENT_ID = "IAP_CLIENT_ID"

WAIT_TIMEOUT = 24*60*60

class KubeflowClient(object):

    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        token = self.obtain_id_token()
        self.host = config['host']
        self.client = Client(self.host, existing_token=token)
        self.project_name = project_name
        self.context = context

    def list_pipelines(self):
        pipelines = self.client.list_pipelines(page_size=30).pipelines
        return tabulate(map(lambda x: [x.name, x.id], pipelines), headers=["Name", "ID"])

    def run_once(self, pipeline, image, experiment_name, run_name, wait, image_pull_policy="IfNotPresent") -> None:
        run = self.client.create_run_from_pipeline_func(
            self.generate_pipeline(pipeline, image, image_pull_policy),
            arguments={},
            experiment_name=experiment_name,
            run_name=run_name
        )

        if wait:
            run.wait_for_run_completion(timeout=WAIT_TIMEOUT)

    def obtain_id_token(self):
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
        from google.auth.exceptions import DefaultCredentialsError

        client_id = os.environ.get(IAP_CLIENT_ID, None)

        jwt_token = None

        if not client_id:
            self.log.info("No IAP_CLIENT_ID provided, skipping custom IAP authentication")
            return jwt_token

        try:
            self.log.debug("Obtaining JWT token for %s." + client_id)
            jwt_token = id_token.fetch_id_token(Request(), client_id)
            self.log.info("Obtained JWT token for MLFLOW connectivity.")
        except DefaultCredentialsError as ex:
            self.log.warning(str(ex) + (" Note that this authentication method does not work with default credentials"
                                   " obtained via 'gcloud auth application-default login' command. Refer to"
                                   " documentation on how to configure service account locally "
                                   "(https://cloud.google.com/docs/authentication/production#manually)"))
        except Exception as e:
            self.log.error("Failed to obtain IAP access token. " + str(e))
        finally:
            return jwt_token

    def generate_pipeline(self, pipeline, image, image_pull_policy):
        @dsl.pipeline(name=self.project_name, description="Kubeflow pipeline for Kedro project")
        def convert_kedro_pipeline_to_kfp() -> None:
            """Convert from a Kedro pipeline into a kfp container graph."""

            node_dependencies = self.context.pipelines.get(pipeline).node_dependencies
            kfp_ops = _build_kfp_ops(node_dependencies)
            for node, dependencies in node_dependencies.items():
                for dependency in dependencies:
                    kfp_ops[node.name].after(kfp_ops[dependency.name])

        def _build_kfp_ops(node_dependencies: Dict[Node, Set[Node]]) -> Dict[str, dsl.ContainerOp]:
            """Build kfp container graph from Kedro node dependencies. """
            kfp_ops = {}

            env = V1EnvVar(name=IAP_CLIENT_ID, value=os.environ.get(IAP_CLIENT_ID, ""))

            for node in node_dependencies:
                name = _clean_name(node.name)
                kfp_ops[node.name] = dsl.ContainerOp(
                    name=name,
                    image=image,
                    command=["kedro"],
                    arguments=["run", "--node", node.name],
                )

                kfp_ops[node.name].container.add_env_variable(env)
                kfp_ops[node.name].container.set_image_pull_policy(image_pull_policy)

            return kfp_ops

        return convert_kedro_pipeline_to_kfp


    def compile(self, pipeline, image, output, image_pull_policy='IfNotPresent'):
        Compiler().compile(self.generate_pipeline(pipeline, image, image_pull_policy), output)
        self.log.info("Generated pipeline definition was saved to %s" % output)

    def upload(self, pipeline, image, image_pull_policy='IfNotPresent'):
        pipeline = self.generate_pipeline(pipeline, image, image_pull_policy)

        if self._pipeline_exists(self.project_name):
            pipeline_id = self._get_pipeline_id(self.project_name)
            version_id = self._upload_pipeline_version(pipeline, pipeline_id, self.project_name)
            self.log.info("New version of pipeline created: %s", version_id)
        else:
            (pipeline_id, version_id) = self._upload_pipeline(
                pipeline, self.project_name
            )
            self.log.info("Pipeline created")

        self.log.info(
            f"Pipeline link: {self.host}/#/pipelines/details/%s/version/%s",
            pipeline_id,
            version_id,
        )

    def _pipeline_exists(self, pipeline_name):
        try:
            self._get_pipeline_id(pipeline_name)
            return True
        except:
            return False

    def _get_pipeline_id(self, pipeline_name):
        return (
            self.client.pipelines.list_pipelines(
                filter=json.dumps(
                    {
                        "predicates": [
                            {"key": "name", "op": 1, "string_value": pipeline_name}
                        ]
                    }
                )
            )
            .pipelines[0]
            .id
        )

    def _upload_pipeline_version(self, pipeline_func, pipeline_id, pipeline_name):
        version_name = f"{_clean_name(pipeline_name)}-{uuid.uuid4()}"[:100]
        with NamedTemporaryFile(suffix=".yaml") as f:
            Compiler().compile(pipeline_func, f.name)
            return self.client.pipeline_uploads.upload_pipeline_version(
                f.name, name=version_name, pipelineid=pipeline_id
            ).id

    def _upload_pipeline(self, pipeline_func, pipeline_name):
        with NamedTemporaryFile(suffix=".yaml") as f:
            Compiler().compile(pipeline_func, f.name)
            pipeline = self.client.pipeline_uploads.upload_pipeline(
                f.name, name=pipeline_name
            )
            return (pipeline.id, pipeline.default_version.id)

    def _ensure_experiment_exists(self, experiment_name):
        try:
            experiment = self.client.get_experiment(
                experiment_name=experiment_name
            )
            self.log.info(f"Existing experiment found: {experiment.id}")
        except:
            experiment = self.client.create_experiment(
                experiment_name
            )
            self.log.info(f"New experiment created: {experiment.id}")

        return experiment.id


    def schedule(self, experiment_name, cron_expression):
        experiment_id = self._ensure_experiment_exists(experiment_name)
        pipeline_id = self._get_pipeline_id(self.project_name)
        self._disable_runs(experiment_id, pipeline_id)
        job = self.client.create_recurring_run(
            experiment_id,
            f'{self.project_name} on {cron_expression}',
            cron_expression=cron_expression,
            pipeline_id=pipeline_id,
        )
        self.log.info("Pipeline scheduled to %s", cron_expression)

    def _disable_runs(self, experiment_id, pipeline_id):
        runs = self.client.list_recurring_runs(experiment_id=experiment_id)
        if runs.jobs is not None:
            my_runs = [job for job in runs.jobs if job.pipeline_spec.pipeline_id == pipeline_id]
            for job in my_runs:
                self.client.jobs.delete_job(job.id)
                self.log.info(f"Previous schedule deleted {job.id}")


def _clean_name(name: str) -> str:
    return re.sub(r"[\W_]+", "-", name).strip("-")


