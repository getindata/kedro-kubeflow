import contextlib
import itertools
import json
import os
from functools import reduce, wraps
from inspect import Parameter, signature

import fsspec
import kubernetes.client as k8s
from fsspec.implementations.local import LocalFileSystem
from kfp import dsl
from kfp.compiler._k8s_helper import sanitize_k8s_name

from ..auth import IAP_CLIENT_ID
from ..config import RunConfig


def ensure_json_serializable(value):
    return json.loads(json.dumps(value, default=str))


def maybe_add_params(kedro_parameters):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f()

        sig = signature(f)
        new_params = (
            Parameter(
                name,
                Parameter.KEYWORD_ONLY,
                default=ensure_json_serializable(default),
            )
            for name, default in kedro_parameters.items()
        )
        wrapper.__signature__ = sig.replace(parameters=new_params)
        return wrapper

    return decorator


def merge_namespaced_params_to_dict(kedro_parameters):
    def dict_merge(dct, merge_dct):
        """Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
        updating only top-level keys, dict_merge recurses down into dicts nested
        to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
        ``dct``.
        :param dct: dict onto which the merge is executed
        :param merge_dct: dct merged into dct
        :return: None
        """
        for k, v in merge_dct.items():
            if k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], dict):  # noqa
                dict_merge(dct[k], merge_dct[k])
            else:
                dct[k] = merge_dct[k]

        return dct

    normalized_params = []
    for key, param in kedro_parameters.items():
        if "." in key:
            nested_keys = key.split(".")
            top_key = nested_keys.pop(0)
            bottom_key = nested_keys.pop()
            inner_dict = {bottom_key: param}
            for nested_key in nested_keys[-1:]:
                inner_dict = {nested_key: inner_dict}

            inner_dict = {top_key: inner_dict}
            normalized_params.append(inner_dict)
        else:
            normalized_params.append({key: param})

    if normalized_params:
        return reduce(dict_merge, normalized_params)
    else:
        return dict()


def create_container_environment():
    env_vars = [
        k8s.V1EnvVar(name=IAP_CLIENT_ID, value=os.environ.get(IAP_CLIENT_ID, "")),
        k8s.V1EnvVar(name="KUBEFLOW_RUN_ID", value=dsl.RUN_ID_PLACEHOLDER),
    ]
    for key in os.environ.keys():
        if key.startswith("KEDRO_CONFIG_"):
            env_vars.append(k8s.V1EnvVar(name=key, value=os.environ[key]))

    return env_vars


def create_command_using_params_dumper(command):
    return [
        "bash",
        "-c",
        "python -c 'import yaml, sys;"
        "load=lambda e: yaml.load(e, Loader=yaml.FullLoader);"
        "params=dict(zip(sys.argv[1::2], [load(e) for e in sys.argv[2::2]]));"
        'f=open("config.yaml", "w");'
        'yaml.dump({"run": {"params": params}}, f)\' "$@" &&' + command,
    ]


def create_arguments_from_parameters(paramter_names):
    return ["_"] + list(itertools.chain(*[[param, dsl.PipelineParam(param)] for param in paramter_names]))


def create_pipeline_exit_handler(pipeline, image, image_pull_policy, run_config, context):
    enable_volume_cleaning = run_config.volume is not None and not run_config.volume.keep

    if not enable_volume_cleaning and not run_config.on_exit_pipeline:
        return contextlib.nullcontext()

    commands = []

    if enable_volume_cleaning:
        commands.append(
            "kedro kubeflow delete-pipeline-volume " "{{workflow.name}}-" + sanitize_k8s_name(f"{pipeline}-data-volume")
        )

    if run_config.on_exit_pipeline:
        commands.append(
            "kedro run " "--config config.yaml " f"--env {context.env} " f"--pipeline {run_config.on_exit_pipeline}"
        )

    exit_container_op = dsl.ContainerOp(
        name="on-exit",
        image=image,
        command=create_command_using_params_dumper(";".join(commands)),
        arguments=create_arguments_from_parameters(context.params.keys())
        + [
            "status",
            "{{workflow.status}}",
            "failures",
            "{{workflow.failures}}",
        ],
        container_kwargs={"env": create_container_environment()},
    )

    if run_config.max_cache_staleness not in [None, ""]:
        exit_container_op.execution_options.caching_strategy.max_cache_staleness = run_config.max_cache_staleness

    return dsl.ExitHandler(customize_op(exit_container_op, image_pull_policy, run_config))


def customize_op(op, image_pull_policy, run_config: RunConfig):
    op.container.set_image_pull_policy(image_pull_policy)
    if run_config.volume and run_config.volume.owner is not None:
        op.container.set_security_context(k8s.V1SecurityContext(run_as_user=run_config.volume.owner))

    resources = run_config.resources[op.name]
    op.container.resources = k8s.V1ResourceRequirements(
        limits=resources,
        requests=resources,
    )

    if retry_policy := run_config.retry_policy[op.name]:
        op.set_retry(policy="Always", **retry_policy.dict())

    for toleration in run_config.tolerations[op.name]:
        op.add_toleration(k8s.V1Toleration(**toleration.dict()))

    if extra_volumes := run_config.extra_volumes[op.name]:
        op.add_pvolumes({ev.mount_path: dsl.PipelineVolume(volume=ev.as_v1volume()) for ev in extra_volumes})
    return op


def is_local_fs(filepath):

    file_open = fsspec.open(filepath)
    return isinstance(file_open.fs, LocalFileSystem)
