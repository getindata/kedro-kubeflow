import logging
import os
from functools import wraps
from inspect import Parameter, signature
from typing import Dict, Set

from kedro.pipeline.node import Node
from kfp import dsl
from kubernetes.client import V1EnvVar, V1SecurityContext

from .auth import IAP_CLIENT_ID
from .utils import clean_name, is_mlflow_enabled


def maybe_add_params(kedro_parameters):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f()

        sig = signature(f)
        new_params = (
            Parameter(name, Parameter.KEYWORD_ONLY, default=default)
            for name, default in kedro_parameters.items()
        )
        wrapper.__signature__ = sig.replace(parameters=new_params)
        return wrapper

    return decorator


class PipelineGenerator(object):

    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.project_name = project_name
        self.context = context
        dsl.ContainerOp._DISABLE_REUSABLE_COMPONENT_WARNING = True
        self.volume_meta = config.run_config.volume

    def generate_pipeline(self, pipeline, image, image_pull_policy):
        @dsl.pipeline(
            name=self.project_name,
            description="Kubeflow pipeline for Kedro project",
        )
        @maybe_add_params(self.context.params)
        def convert_kedro_pipeline_to_kfp() -> None:
            """Convert from a Kedro pipeline into a kfp container graph."""
            node_dependencies = self.context.pipelines.get(
                pipeline
            ).node_dependencies
            kfp_ops = self._build_kfp_ops(
                node_dependencies, image, image_pull_policy
            )
            for node, dependencies in node_dependencies.items():
                for dependency in dependencies:
                    kfp_ops[node.name].after(kfp_ops[dependency.name])

        return convert_kedro_pipeline_to_kfp

    def _build_kfp_ops(
        self,
        node_dependencies: Dict[Node, Set[Node]],
        image,
        image_pull_policy,
    ) -> Dict[str, dsl.ContainerOp]:
        """Build kfp container graph from Kedro node dependencies. """
        kfp_ops = {}

        node_volumes = (
            self._setup_volumes(image, image_pull_policy)
            if self.volume_meta is not None
            else {}
        )

        iap_env_var = V1EnvVar(
            name=IAP_CLIENT_ID, value=os.environ.get(IAP_CLIENT_ID, "")
        )
        nodes_env = [iap_env_var]

        if is_mlflow_enabled():
            kfp_ops["mlflow-start-run"] = self._customize_op(
                dsl.ContainerOp(
                    name="mlflow-start-run",
                    image=image,
                    command=["kedro"],
                    arguments=[
                        "kubeflow",
                        "mlflow-start",
                        dsl.RUN_ID_PLACEHOLDER,
                    ],
                    container_kwargs={"env": [iap_env_var]},
                    file_outputs={"mlflow_run_id": "/tmp/mlflow_run_id"},
                ),
                image_pull_policy,
            )

            nodes_env.append(
                V1EnvVar(
                    name="MLFLOW_RUN_ID",
                    value=kfp_ops["mlflow-start-run"].output,
                )
            )

        for node in node_dependencies:
            name = clean_name(node.name)
            params = ",".join(
                [
                    f"{param}:{dsl.PipelineParam(param)}"
                    for param in self.context.params.keys()
                ]
            )
            kfp_ops[node.name] = self._customize_op(
                dsl.ContainerOp(
                    name=name,
                    image=image,
                    command=["kedro"],
                    arguments=[
                        "run",
                        "--params",
                        params,
                        "--node",
                        node.name,
                    ],
                    pvolumes=node_volumes,
                    container_kwargs={"env": nodes_env},
                ),
                image_pull_policy,
            )

        return kfp_ops

    def _customize_op(self, op, image_pull_policy):
        op.container.set_image_pull_policy(image_pull_policy)
        if self.volume_meta and self.volume_meta.owner is not None:
            op.container.set_security_context(
                V1SecurityContext(run_as_user=self.volume_meta.owner)
            )
        return op

    def _setup_volumes(self, image, image_pull_policy):
        vop = dsl.VolumeOp(
            name="data-volume-create",
            resource_name="data-volume",
            size=self.volume_meta.size,
            modes=self.volume_meta.access_modes,
            storage_class=self.volume_meta.storageclass,
        )
        if self.volume_meta.skip_init:
            return {"/home/kedro/data": vop.volume}
        else:
            volume_init = self._customize_op(
                dsl.ContainerOp(
                    name="data-volume-init",
                    image=image,
                    command=["sh", "-c"],
                    arguments=[
                        " ".join(
                            [
                                "cp",
                                "--verbose",
                                "-r",
                                "/home/kedro/data/*",
                                "/home/kedro/datavolume",
                            ]
                        )
                    ],
                    pvolumes={"/home/kedro/datavolume": vop.volume},
                ),
                image_pull_policy,
            )
            return {"/home/kedro/data": volume_init.pvolume}
