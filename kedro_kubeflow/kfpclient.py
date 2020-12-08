import re
from pathlib import Path

from kedro.framework.context import load_context
from kfp import Client, dsl
from kfp.compiler import Compiler
from kubernetes.client import V1EnvVar
from tabulate import tabulate
from typing import Dict, Set
from kedro.pipeline.node import Node
import os
import logging

IAP_CLIENT_ID = "IAP_CLIENT_ID"

_PIPELINE = None
_IMAGE = None

WAIT_TIMEOUT = 24*60*60

class KubeflowClient(object):

    log = logging.getLogger(__name__)

    def __init__(self, config):
        token = KubeflowClient.obtain_id_token(self.log)
        self.token = None
        self.host = config['host']
        self.client = Client(self.host, existing_token=token)

    def list_pipelines(self):
        pipelines = self.client.list_pipelines(page_size=30).pipelines
        print(tabulate(map(lambda x: [x.name, x.id], pipelines), headers=["Name", "ID"]))

    def run_once(self, pipeline, image, experiment_name, run_name, env, wait) -> None:
        global _PIPELINE
        global _IMAGE

        context = load_context(Path.cwd(), env=env)

        _IMAGE = image
        _PIPELINE = context.pipelines.get(pipeline)

        convert_kedro_pipeline_to_kfp._component_human_name = context.project_name

        run = self.client.create_run_from_pipeline_func(
            convert_kedro_pipeline_to_kfp,
            arguments={},
            experiment_name=experiment_name,
            run_name=run_name
        )

        if wait:
            run.wait_for_run_completion(timeout=WAIT_TIMEOUT)

    @staticmethod
    def obtain_id_token(log):
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
        from google.auth.exceptions import DefaultCredentialsError

        client_id = os.environ.get(IAP_CLIENT_ID, None)

        jwt_token = None

        if not client_id:
            log.info("No IAP_CLIENT_ID provided, skipping custom IAP authentication")
            return jwt_token

        try:
            log.debug("Obtaining JWT token for %s." + client_id)
            jwt_token = id_token.fetch_id_token(Request(), client_id)
            log.info("Obtained JWT token for MLFLOW connectivity.")
        except DefaultCredentialsError as ex:
            log.warning(str(ex) + (" Note that this authentication method does not work with default credentials"
                                   " obtained via 'gcloud auth application-default login' command. Refer to"
                                   " documentation on how to configure service account locally "
                                   "(https://cloud.google.com/docs/authentication/production#manually)"))
        except Exception as e:
            log.error("Failed to obtain IAP access token. " + str(e))
        finally:
            return jwt_token

    def compile(self, pipeline, image, env, output):
        global _PIPELINE
        global _IMAGE

        context = load_context(Path.cwd(), env=env)

        _IMAGE = image
        _PIPELINE = context.pipelines.get(pipeline)
        print(_PIPELINE)
        convert_kedro_pipeline_to_kfp._component_human_name = context.project_name
        Compiler().compile(convert_kedro_pipeline_to_kfp, output)
        self.log.info("Generated pipeline definition was saved to %s" % output)


@dsl.pipeline(name="Kedro pipeline", description="Kubeflow pipeline for Kedro project")
def convert_kedro_pipeline_to_kfp() -> None:
    """Convert from a Kedro pipeline into a kfp container graph."""

    node_dependencies = _PIPELINE.node_dependencies
    kfp_ops = _build_kfp_ops(node_dependencies)
    for node, dependencies in node_dependencies.items():
        for dependency in dependencies:
            kfp_ops[node.name].after(kfp_ops[dependency.name])


def _clean_name(name: str) -> str:
    return re.sub(r"[\W_]+", "-", name).strip("-")


def _build_kfp_ops(node_dependencies: Dict[Node, Set[Node]]) -> Dict[str, dsl.ContainerOp]:
    """Build kfp container graph from Kedro node dependencies. """
    kfp_ops = {}

    env = V1EnvVar(name=IAP_CLIENT_ID, value=os.environ.get(IAP_CLIENT_ID, ""))

    for node in node_dependencies:
        name = _clean_name(node.name)
        kfp_ops[node.name] = dsl.ContainerOp(
            name=name,
            image=_IMAGE,
            command=["kedro"],
            arguments=["run", "--node", node.name],
        )

        kfp_ops[node.name].container.add_env_variable(env)

    return kfp_ops
