"""
Pipeline input and output helper methods for spec generation
"""

from typing import Dict, Set

import kfp
from kedro.pipeline.node import Node
from kfp.components import structures

from kedro_kubeflow.utils import clean_name, is_mlflow_enabled


def _find_input_node(input_name, nodes):
    return [node for node in nodes if input_name in node.outputs]


def generate_inputs(
    node: Node, node_dependencies: Dict[Node, Set[Node]], catalog
):
    """
    Generates inputs for a particular kedro node
    """

    def is_file_path_input(input_data):
        return (
            input_data in catalog
            and "filepath" in catalog[input_data]
            and ":/" not in catalog[input_data]["filepath"]
        )

    input_mapping = {
        i: catalog[i]["filepath"] for i in node.inputs if is_file_path_input(i)
    }

    input_params_mapping = {}
    for input_name in input_mapping:
        input_node = _find_input_node(input_name, node_dependencies)
        if input_node:
            input_params_mapping[input_name] = input_node[0]

    input_params = [
        kfp.dsl.PipelineParam(
            name=i,
            op_name=clean_name(input_params_mapping[i].name),
            param_type="Dataset",
        )
        for i in input_params_mapping
    ]
    input_specs = [
        structures.InputSpec(param.name, "Dataset") for param in input_params
    ]

    return input_params, input_specs


def get_output_type(output, catalog):
    """
    Returns Vertex output type based on the layer in Kedro catalog
    """
    if catalog[output].get("layer") == "models":
        return "Model"
    return "Dataset"


def generate_outputs(node: Node, catalog):
    """
    Generates outputs for a particular kedro node
    """
    data_mapping = {
        o: catalog[o]["filepath"]
        for o in node.outputs
        if o in catalog
        and "filepath" in catalog[o]
        and ":/" not in catalog[o]["filepath"]
    }
    output_specs = [
        structures.OutputSpec(o, get_output_type(o, catalog))
        for o in data_mapping.keys()
    ]
    output_copy_commands = " ".join(
        [
            f"&& mkdir --parents `dirname {{{{$.outputs.artifacts['{o}'].path}}}}` "
            f"&& cp /home/kedro/{filepath} {{{{$.outputs.artifacts['{o}'].path}}}}"
            for o, filepath in data_mapping.items()
        ]
    )
    output_placeholders = [
        structures.OutputPathPlaceholder(output_name=o)
        for o in data_mapping.keys()
    ]
    return output_specs, output_copy_commands, output_placeholders


def generate_mlflow_inputs():
    """
    Generates inputs that are required to correctly generate mlflow specific data.
    :return: mlflow_inputs, mlflow_tokens
    """
    mlflow_inputs = (
        [
            structures.InputSpec("mlflow_tracking_token", "String"),
            structures.InputSpec("mlflow_run_id", "String"),
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
