"""
Generator for Vertex AI pipelines
"""

import logging
from tempfile import NamedTemporaryFile
from typing import Dict, Set

import kfp
from kedro.pipeline.node import Node
from kfp.components.structures import (
    ComponentSpec,
    ContainerImplementation,
    ContainerSpec,
    InputSpec,
    OutputPathPlaceholder,
    OutputSpec,
)
from kfp.v2 import dsl

from kedro_kubeflow.utils import clean_name, is_mlflow_enabled
from kedro_kubeflow.vertex_ai.io import (
    generate_inputs,
    generate_mlflow_inputs,
    generate_outputs,
)


class PipelineGenerator:
    """
    Generator creates Vertex AI pipeline function that operatoes with Vertex AI specific
    opertator spec.
    """

    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.project_name = project_name
        self.context = context
        self.run_config = config.run_config
        self.catalog = context.config_loader.get("catalog*")

    def get_pipeline_name(self):
        """
        Returns Vertex-compatible pipeline name
        """
        return self.project_name.lower().replace(" ", "-")

    def generate_pipeline(self, pipeline, image, image_pull_policy, token):
        """
        This method return @dsl.pipeline annotated function that contains
        dynamically generated pipelines.
        :param pipeline: kedro pipeline
        :param image: full docker image name
        :param image_pull_policy: docker pull policy
        :param token: mlflow authentication token
        :return: kfp pipeline function
        """

        def set_dependencies(node, dependencies, kfp_ops):
            for dependency in dependencies:
                name = clean_name(node.name)
                dependency_name = clean_name(dependency.name)
                kfp_ops[name].after(kfp_ops[dependency_name])

        @dsl.pipeline(
            name=self.get_pipeline_name(),
            description=self.run_config.description,
        )
        def convert_kedro_pipeline_to_kfp() -> None:
            node_dependencies = self.context.pipelines.get(
                pipeline
            ).node_dependencies
            kfp_ops = self._build_kfp_ops(
                node_dependencies, image, pipeline, token
            )
            for node, dependencies in node_dependencies.items():
                set_dependencies(node, dependencies, kfp_ops)

            if self.run_config.volume and not self.run_config.volume.skip_init:
                self._create_data_volume_init_op(kfp_ops, image)

            for operator in kfp_ops.values():
                operator.container.set_image_pull_policy(image_pull_policy)

        return convert_kedro_pipeline_to_kfp

    def _generate_hosts_file(self):
        host_aliases = self.run_config.vertex_ai_networking.host_aliases
        return " ".join(
            f"echo {ip}\t{' '.join(hostnames)} >> /etc/hosts;"
            for ip, hostnames in host_aliases.items()
        )

    def _create_data_volume_init_op(
        self, kfp_ops: Dict[str, dsl.ContainerOp], image: str
    ):
        data_volume_init = self._setup_volume_op(image)
        for name, ops in kfp_ops.items():
            if name != "mlflow-start-run":
                ops.after(data_volume_init)
        kfp_ops["data-volume-init"] = data_volume_init

    def _create_mlflow_op(self, image, tracking_token) -> dsl.ContainerOp:
        mlflow_command = " ".join(
            [
                self._generate_hosts_file(),
                "mkdir --parents "
                "`dirname {{$.outputs.parameters['output'].output_file}}`",
                "&&",
                "MLFLOW_TRACKING_TOKEN={{$.inputs.parameters['mlflow_tracking_token']}} "
                f"kedro kubeflow -e {self.context.env} mlflow-start "
                "--output {{$.outputs.parameters['output'].output_file}} "
                + self.run_config.run_name,
            ]
        )

        spec = ComponentSpec(
            name="mlflow-start-run",
            inputs=[InputSpec("mlflow_tracking_token", "String")],
            outputs=[OutputSpec("output", "String")],
            implementation=ContainerImplementation(
                container=ContainerSpec(
                    image=image,
                    command=["/bin/bash", "-c"],
                    args=[
                        mlflow_command,
                        OutputPathPlaceholder(output_name="output"),
                    ],
                )
            ),
        )
        with NamedTemporaryFile(
            mode="w", prefix="kedro-kubeflow-spec", suffix=".yaml"
        ) as spec_file:
            spec.save(spec_file.name)
            component = kfp.components.load_component_from_file(spec_file.name)
        return component(tracking_token)

    def _create_params_parameter(self) -> str:
        params_parameter = ",".join(
            [f"{key}:{value}" for key, value in self.context.params.items()]
        )
        if params_parameter:
            params_parameter = f"--params {params_parameter}"
        return params_parameter

    def _build_kfp_ops(
        self,
        node_dependencies: Dict[Node, Set[Node]],
        image,
        pipeline,
        tracking_token=None,
    ) -> Dict[str, dsl.ContainerOp]:
        """Build kfp container graph from Kedro node dependencies."""
        kfp_ops = {}

        if is_mlflow_enabled():
            kfp_ops["mlflow-start-run"] = self._create_mlflow_op(
                image, tracking_token
            )

        params_parameter = self._create_params_parameter()

        for node in node_dependencies:
            name = clean_name(node.name)

            (
                output_specs,
                output_copy_commands,
                output_placeholders,
            ) = generate_outputs(node, self.catalog)
            input_params, input_specs = generate_inputs(
                node, node_dependencies, self.catalog
            )
            mlflow_inputs, mlflow_tokens = generate_mlflow_inputs()
            component_params = (
                [tracking_token, kfp_ops["mlflow-start-run"].output]
                if is_mlflow_enabled()
                else []
            )

            kedro_command = " ".join(
                [
                    f"kedro run -e {self.context.env}",
                    f"--pipeline {pipeline}",
                    f"{params_parameter}",
                    f'--node "{node.name}"',
                ]
            )
            node_command = " ".join(
                [
                    self._generate_hosts_file(),
                    "rm -r /home/kedro/data"
                    "&&"
                    f"ln -s /gcs/{self._get_data_path()} /home/kedro/data"
                    "&&",
                    mlflow_tokens + kedro_command,
                ]
            )
            spec = ComponentSpec(
                name=name,
                inputs=mlflow_inputs + input_specs,
                outputs=output_specs,
                implementation=ContainerImplementation(
                    container=ContainerSpec(
                        image=image,
                        command=["/bin/bash", "-c"],
                        args=[node_command + " " + output_copy_commands]
                        + output_placeholders,
                    )
                ),
            )
            kfp_ops[name] = self._create_kedro_op(
                name, spec, component_params + input_params
            )

        return kfp_ops

    def _create_kedro_op(
        self, name: str, spec: ComponentSpec, op_function_parameters
    ):
        with NamedTemporaryFile(
            mode="w", prefix="kedro-kubeflow-node-spec", suffix=".yaml"
        ) as spec_file:
            spec.save(spec_file.name)
            component = kfp.components.load_component_from_file(spec_file.name)

        operator = component(*op_function_parameters)

        self._configure_resources(name, operator)
        return operator

    def _configure_resources(self, name: str, operator):
        resources = self.run_config.resources.get_for(name)
        if "cpu" in resources:
            operator.set_cpu_limit(resources["cpu"])
            operator.set_cpu_request(resources["cpu"])
        if "memory" in resources:
            operator.set_memory_limit(resources["memory"])
            operator.set_memory_request(resources["memory"])
        if "cloud.google.com/gke-accelerator" in resources:
            operator.add_node_selector_constraint(
                "cloud.google.com/gke-accelerator",
                resources["cloud.google.com/gke-accelerator"],
            )
        if "nvidia.com/gpu" in resources:
            operator.set_gpu_limit(resources["nvidia.com/gpu"])

    def _get_data_path(self):
        return (
            f"{self.run_config.root}/"
            f"{self.run_config.experiment_name}/{self.run_config.run_name}/data"
        )

    def _setup_volume_op(self, image):
        command = " ".join(
            [
                f"mkdir --parents /gcs/{self._get_data_path()} &&",
                f"cp -r /home/kedro/data/* /gcs/{self._get_data_path()}",
            ]
        )
        spec = ComponentSpec(
            name="data-volume-init",
            inputs=[],
            implementation=ContainerImplementation(
                container=ContainerSpec(
                    image=image, command=["/bin/bash", "-c"], args=[command]
                )
            ),
        )

        with NamedTemporaryFile(
            mode="w", prefix="kedro-kubeflow-data-volume-init", suffix=".yaml"
        ) as spec_file:
            spec.save(spec_file.name)
            component = kfp.components.load_component_from_file(spec_file.name)
            volume_init = component()

        return volume_init
