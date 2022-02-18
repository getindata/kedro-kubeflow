import logging
from typing import Dict, Set

import kubernetes.client as k8s
from kedro.pipeline.node import Node
from kfp import dsl

from ..utils import clean_name, is_mlflow_enabled
from .utils import (
    create_arguments_from_parameters,
    create_command_using_params_dumper,
    create_container_environment,
    create_pipeline_exit_handler,
    customize_op,
    maybe_add_params,
)


class PodPerNodePipelineGenerator(object):
    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.project_name = project_name
        self.context = context
        dsl.ContainerOp._DISABLE_REUSABLE_COMPONENT_WARNING = True
        self.run_config = config.run_config
        self.catalog = context.config_loader.get("catalog*")

    def configure_max_cache_staleness(self, kfp_ops):
        if self.run_config.max_cache_staleness not in [None, ""]:
            for _, op in kfp_ops.items():
                op.execution_options.caching_strategy.max_cache_staleness = (
                    self.run_config.max_cache_staleness
                )

    def generate_pipeline(self, pipeline, image, image_pull_policy):
        @dsl.pipeline(
            name=self.project_name,
            description=self.run_config.description,
        )
        @maybe_add_params(self.context.params)
        def convert_kedro_pipeline_to_kfp() -> None:
            """Convert from a Kedro pipeline into a kfp container graph."""
            dsl.get_pipeline_conf().set_ttl_seconds_after_finished(
                self.run_config.ttl
            )
            node_dependencies = self.context.pipelines.get(
                pipeline
            ).node_dependencies
            with create_pipeline_exit_handler(
                pipeline,
                image,
                image_pull_policy,
                self.run_config,
                self.context,
            ):
                kfp_ops = self._build_kfp_ops(
                    pipeline, node_dependencies, image, image_pull_policy
                )

                self.configure_max_cache_staleness(kfp_ops)
                for node, dependencies in node_dependencies.items():
                    for dependency in dependencies:
                        kfp_ops[node.name].after(kfp_ops[dependency.name])

        return convert_kedro_pipeline_to_kfp

    def _build_kfp_ops(
        self,
        pipeline,
        node_dependencies: Dict[Node, Set[Node]],
        image,
        image_pull_policy,
    ) -> Dict[str, dsl.ContainerOp]:
        """Build kfp container graph from Kedro node dependencies."""
        kfp_ops = {}

        node_volumes = (
            self._setup_volumes(
                f"{pipeline}-data-volume", image, image_pull_policy
            )
            if self.run_config.volume is not None
            else {}
        )

        nodes_env = create_container_environment()

        if is_mlflow_enabled():
            kfp_ops["mlflow-start-run"] = customize_op(
                dsl.ContainerOp(
                    name="mlflow-start-run",
                    image=image,
                    command=["kedro"],
                    arguments=[
                        "kubeflow",
                        "--env",
                        self.context.env,
                        "mlflow-start",
                        dsl.RUN_ID_PLACEHOLDER,
                    ],
                    container_kwargs={"env": nodes_env.copy()},
                    file_outputs={"mlflow_run_id": "/tmp/mlflow_run_id"},
                ),
                image_pull_policy,
                self.run_config,
            )

            nodes_env.append(
                k8s.V1EnvVar(
                    name="MLFLOW_RUN_ID",
                    value=kfp_ops["mlflow-start-run"].output,
                )
            )

        for node in node_dependencies:
            name = clean_name(node.name)
            kwargs = {"env": nodes_env}
            if self.run_config.resources.is_set_for(node.name):
                kwargs["resources"] = k8s.V1ResourceRequirements(
                    limits=self.run_config.resources.get_for(node.name),
                    requests=self.run_config.resources.get_for(node.name),
                )

            kfp_ops[node.name] = customize_op(
                dsl.ContainerOp(
                    name=name,
                    image=image,
                    command=create_command_using_params_dumper(
                        "kedro "
                        "run "
                        f"--env {self.context.env} "
                        f"--pipeline {pipeline} "
                        f"--node {node.name} "
                        f"--config config.yaml"
                    ),
                    arguments=create_arguments_from_parameters(
                        self.context.params.keys()
                    ),
                    pvolumes=node_volumes,
                    container_kwargs=kwargs,
                    file_outputs={
                        output: "/home/kedro/"
                        + self.catalog[output]["filepath"]
                        for output in node.outputs
                        if output in self.catalog
                        and "filepath" in self.catalog[output]
                        and self.run_config.store_kedro_outputs_as_kfp_artifacts
                    },
                ),
                image_pull_policy,
                self.run_config,
            )

        return kfp_ops

    def _setup_volumes(self, volume_name, image, image_pull_policy):
        vop = dsl.VolumeOp(
            name="data-volume-create",
            resource_name=volume_name,
            size=self.run_config.volume.size,
            modes=self.run_config.volume.access_modes,
            storage_class=self.run_config.volume.storageclass,
        )

        if self.run_config.max_cache_staleness not in [None, ""]:
            vop.add_pod_annotation(
                "pipelines.kubeflow.org/max_cache_staleness",
                self.run_config.max_cache_staleness,
            )

        if self.run_config.volume.skip_init:
            return {"/home/kedro/data": vop.volume}
        else:
            volume_init = customize_op(
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
                self.run_config,
            )
            return {"/home/kedro/data": volume_init.pvolume}
