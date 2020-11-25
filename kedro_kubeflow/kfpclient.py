import re
from pathlib import Path

from kedro.framework.context import load_context
from kfp import Client, dsl
from tabulate import tabulate
from typing import Dict, Set
from kedro.pipeline.node import Node

_PIPELINE = None
_IMAGE = None

WAIT_TIMEOUT = 24*60*60


class KubeflowClient(object):

    def __init__(self, config):
        self.host = config['host']
        self.client = Client(config['host'])

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

    for node in node_dependencies:
        name = _clean_name(node.name)
        kfp_ops[node.name] = dsl.ContainerOp(
            name=name,
            image=_IMAGE,
            command=["kedro"],
            arguments=["run", "--node", node.name],
        )
    return kfp_ops
