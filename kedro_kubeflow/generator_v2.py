import contextlib
import logging
import os
from functools import wraps
from inspect import Parameter, signature
from tempfile import NamedTemporaryFile
from typing import Dict, Set

import kubernetes.client as k8s
from kedro.pipeline.node import Node
from kfp.v2 import dsl

from .auth import IAP_CLIENT_ID
from .utils import clean_name, is_mlflow_enabled
from kfp.components.structures import ComponentSpec, ContainerSpec, \
    ContainerImplementation, OutputSpec, InputSpec, OutputPathPlaceholder
import kfp


class PipelineGenerator(object):
    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.project_name = project_name
        self.context = context
        self.run_config = config.run_config
        self.catalog = context.config_loader.get("catalog*")

    def generate_pipeline(self, pipeline, image, image_pull_policy, token):
        @dsl.pipeline(
            name=self.project_name.lower().replace(' ', '-'),
            description=self.run_config.description,
        )
        def convert_kedro_pipeline_to_kfp() -> None:
            node_dependencies = self.context.pipelines.get(pipeline).node_dependencies
            kfp_ops = self._build_kfp_ops(
                node_dependencies, image, token
            )
            for node, dependencies in node_dependencies.items():
                for dependency in dependencies:
                    name = clean_name(node.name)
                    dependency_name = clean_name(dependency.name)
                    kfp_ops[name].after(kfp_ops[dependency_name])

            if self.run_config.volume and not self.run_config.volume.skip_init:
                data_volume_init = self._setup_volumes(image)
                for name, ops in kfp_ops.items():
                    if name is not 'mlflow-start-run':
                        ops.after(data_volume_init)
                kfp_ops['data-volume-init'] = data_volume_init

            for op in kfp_ops.values():
                op.container.set_image_pull_policy(image_pull_policy)

        return convert_kedro_pipeline_to_kfp

    def _build_kfp_ops(
            self,
            node_dependencies: Dict[Node, Set[Node]],
            image,
            tracking_token=None
    ) -> Dict[str, dsl.ContainerOp]:
        """Build kfp container graph from Kedro node dependencies."""
        kfp_ops = {}

        if is_mlflow_enabled():
            spec = ComponentSpec(
                name="mlflow-start-run",
                inputs=[InputSpec("mlflow_tracking_token", "String")],
                outputs=[OutputSpec("output", "String")],
                implementation=ContainerImplementation(
                    container=ContainerSpec(
                        image=image,
                        command=[
                            "/bin/bash", "-c"
                        ],
                        args=[
                            " ".join([
                                "mkdir --parents `dirname {{$.outputs.parameters['output'].output_file}}`",
                                "&&",
                                "MLFLOW_TRACKING_TOKEN={{$.inputs.parameters['mlflow_tracking_token']}} kedro kubeflow mlflow-start --output {{$.outputs.parameters['output'].output_file}} " + self.run_config.run_name,
                            ]),
                            OutputPathPlaceholder(output_name='output')
                        ]
                    )
                )
            )
            with NamedTemporaryFile(mode='w', prefix='kedro-kubeflow-spec',
                                    suffix='.yaml') as f:
                spec.save(f.name)
                component = kfp.components.load_component_from_file(f.name)
            kfp_ops["mlflow-start-run"] = component(tracking_token)

        params_parameter = ",".join([
            f"{key}:{value}" for key, value in self.context.params.items()
        ])
        if params_parameter:
            params_parameter = f'--params {params_parameter}'

        for node in node_dependencies:
            name = clean_name(node.name)

            kedro_command = f"kedro run {params_parameter} --node \"{node.name}\""
            spec = ComponentSpec(
                name=name,
                inputs=[InputSpec("mlflow_tracking_token", "String"),
                        InputSpec("mlflow_run_id", "String")],
                implementation=ContainerImplementation(
                    container=ContainerSpec(
                        image=image,
                        command=[
                            "/bin/bash", "-c"
                        ],
                        args=[
                            " ".join([
                                "rm -r /home/kedro/data"
                                "&&"
                                "ln -s /gcs/gid-ml-ops-sandbox-kubeflowpipelines-default/kedro-kubeflow/data /home/kedro/data"
                                "&&",
                                "MLFLOW_TRACKING_TOKEN={{$.inputs.parameters['mlflow_tracking_token']}} MLFLOW_RUN_ID=\"{{$.inputs.parameters['mlflow_run_id']}}\" " + kedro_command,
                            ])
                        ]
                    )
                )
            )
            with NamedTemporaryFile(mode='w', prefix='kedro-kubeflow-node-spec',
                                    suffix='.yaml') as f:
                spec.save(f.name)
                component = kfp.components.load_component_from_file(f.name)
            kfp_ops[name] = component(tracking_token,
                                           kfp_ops["mlflow-start-run"].output)

            resources = self.run_config.resources.get_for(name)
            if "cpu" in resources:
                kfp_ops[name].set_cpu_limit(resources['cpu'])
                kfp_ops[name].set_cpu_request(resources['cpu'])
            if "memory" in resources:
                kfp_ops[name].set_memory_limit(resources['memory'])
                kfp_ops[name].set_memory_request(resources['memory'])
            if "cloud.google.com/gke-accelerator" in resources:
                kfp_ops[name].add_node_selector_constraint(
                    "cloud.google.com/gke-accelerator",
                    resources['cloud.google.com/gke-accelerator'])
            if "nvidia.com/gpu" in resources:
                kfp_ops[name].set_gpu_limit(resources['nvidia.com/gpu'])

        return kfp_ops

    def _setup_volumes(self, image):
        spec = ComponentSpec(
            name="data-volume-init",
            inputs=[],
            implementation=ContainerImplementation(
                container=ContainerSpec(
                    image=image,
                    command=[
                        "/bin/bash", "-c"
                    ],
                    args=[
                        " ".join(
                            [
                                "mkdir --parents /gcs/gid-ml-ops-sandbox-kubeflowpipelines-default/kedro-kubeflow/data",
                                # TODO parametrize me
                                "&&"
                                "cp",
                                "--verbose",
                                "-r",
                                "/home/kedro/data/*",
                                "/gcs/gid-ml-ops-sandbox-kubeflowpipelines-default/kedro-kubeflow/data",
                            ]
                        )
                    ]
                )
            )
        )

        with NamedTemporaryFile(mode='w', prefix='kedro-kubeflow-data-volume-init',
                                suffix='.yaml') as f:
            spec.save(f.name)
            component = kfp.components.load_component_from_file(f.name)
            volume_init = component()

        return volume_init
