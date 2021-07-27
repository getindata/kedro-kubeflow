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


class PipelineGenerator(object):
    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.project_name = project_name
        self.context = context
        self.run_config = config.run_config
        self.catalog = context.config_loader.get("catalog*")

    def generate_pipeline(self, pipeline, image, image_pull_policy, token):
        @dsl.pipeline(
            name=self.project_name.lower().replace(" ", "-"),
            description=self.run_config.description,
        )
        def convert_kedro_pipeline_to_kfp() -> None:
            node_dependencies = self.context.pipelines.get(
                pipeline
            ).node_dependencies
            kfp_ops = self._build_kfp_ops(node_dependencies, image, token)
            for node, dependencies in node_dependencies.items():
                for dependency in dependencies:
                    name = clean_name(node.name)
                    dependency_name = clean_name(dependency.name)
                    kfp_ops[name].after(kfp_ops[dependency_name])

            if self.run_config.volume and not self.run_config.volume.skip_init:
                self._create_data_volume_init_op(kfp_ops, image)

            for op in kfp_ops.values():
                op.container.set_image_pull_policy(image_pull_policy)

        return convert_kedro_pipeline_to_kfp

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
                "mkdir --parents "
                "`dirname {{$.outputs.parameters['output'].output_file}}`",
                "&&",
                "MLFLOW_TRACKING_TOKEN={{$.inputs.parameters['mlflow_tracking_token']}} "
                "kedro kubeflow mlflow-start "
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
        ) as f:
            spec.save(f.name)
            component = kfp.components.load_component_from_file(f.name)
        return component(tracking_token)

    def _create_params_parameter(self) -> str:
        params_parameter = ",".join(
            [f"{key}:{value}" for key, value in self.context.params.items()]
        )
        if params_parameter:
            params_parameter = f"--params {params_parameter}"
        return params_parameter

    def _generate_outputs(self, node: Node):
        data_mapping = {
            o: self.catalog[o]["filepath"]
            for o in node.outputs
            if o in self.catalog
            and "filepath" in self.catalog[o]
            and ":/" not in self.catalog[o]["filepath"]
        }
        output_specs = [OutputSpec(o, "Dataset") for o in data_mapping.keys()]
        output_copy_commands = " ".join(
            [
                f"&& mkdir --parents `dirname {{{{$.outputs.artifacts['{o}'].path}}}}` "
                f"&& cp /home/kedro/{filepath} {{{{$.outputs.artifacts['{o}'].path}}}}"
                for o, filepath in data_mapping.items()
            ]
        )
        output_placeholders = [
            OutputPathPlaceholder(output_name=o) for o in data_mapping.keys()
        ]
        return output_specs, output_copy_commands, output_placeholders

    def _generate_inputs(
        self, node: Node, node_dependencies: Dict[Node, Set[Node]]
    ):
        input_mapping = {
            o: self.catalog[o]["filepath"]
            for o in node.inputs
            if o in self.catalog
            and "filepath" in self.catalog[o]
            and ":/" not in self.catalog[o]["filepath"]
        }

        input_params_mapping = {}
        for i in input_mapping.keys():
            for node in node_dependencies:
                if i in node.outputs:
                    input_params_mapping[i] = node
                    break
        input_params = [
            kfp.dsl.PipelineParam(
                name=i,
                op_name=clean_name(input_params_mapping[i].name),
                param_type="Dataset",
            )
            for i in input_params_mapping.keys()
        ]
        input_specs = [
            InputSpec(param.name, "Dataset") for param in input_params
        ]

        return input_params, input_specs

    def _generate_mlflow_inputs(self):
        mlflow_inputs = (
            [
                InputSpec("mlflow_tracking_token", "String"),
                InputSpec("mlflow_run_id", "String"),
            ]
            if is_mlflow_enabled()
            else []
        )
        mlflow_tokens = (
            "MLFLOW_TRACKING_TOKEN={{$.inputs.parameters['mlflow_tracking_token']}} "
            "MLFLOW_RUN_ID=\"{{$.inputs.parameters['mlflow_run_id']}}\" "
            if is_mlflow_enabled()
            else ""
        )

        return mlflow_inputs, mlflow_tokens

    def _build_kfp_ops(
        self,
        node_dependencies: Dict[Node, Set[Node]],
        image,
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
            ) = self._generate_outputs(node)
            input_params, input_specs = self._generate_inputs(
                node, node_dependencies
            )
            mlflow_inputs, mlflow_tokens = self._generate_mlflow_inputs()
            component_params = (
                [tracking_token, kfp_ops["mlflow-start-run"].output]
                if is_mlflow_enabled()
                else []
            )

            kedro_command = (
                f'kedro run {params_parameter} --node "{node.name}"'
            )
            data_path = "gid-ml-ops-sandbox-kubeflowpipelines-default/kedro-kubeflow/data"
            node_command = " ".join(
                [
                    "rm -r /home/kedro/data"
                    "&&"
                    f"ln -s /gcs/{data_path} /home/kedro/data"
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
        ) as f:
            spec.save(f.name)
            component = kfp.components.load_component_from_file(f.name)

        op = component(*op_function_parameters)

        self._configure_resources(name, op)
        return op

    def _configure_resources(self, name: str, op):
        resources = self.run_config.resources.get_for(name)
        if "cpu" in resources:
            op.set_cpu_limit(resources["cpu"])
            op.set_cpu_request(resources["cpu"])
        if "memory" in resources:
            op.set_memory_limit(resources["memory"])
            op.set_memory_request(resources["memory"])
        if "cloud.google.com/gke-accelerator" in resources:
            op.add_node_selector_constraint(
                "cloud.google.com/gke-accelerator",
                resources["cloud.google.com/gke-accelerator"],
            )
        if "nvidia.com/gpu" in resources:
            op.set_gpu_limit(resources["nvidia.com/gpu"])

    def _setup_volume_op(self, image):
        data_path = (
            "gid-ml-ops-sandbox-kubeflowpipelines-default/kedro-kubeflow/data"
        )
        command = " ".join(
            [
                f"mkdir --parents /gcs/{data_path}",
                # TODO parametrize me
                "&&" "cp",
                "--verbose",
                "-r",
                "/home/kedro/data/*",
                "/gcs/gid-ml-ops-sandbox-kubeflowpipelines-default/kedro-kubeflow/data",
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
        ) as f:
            spec.save(f.name)
            component = kfp.components.load_component_from_file(f.name)
            volume_init = component()

        return volume_init
