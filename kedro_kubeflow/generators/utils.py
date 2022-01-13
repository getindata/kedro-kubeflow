import itertools
import os
from functools import wraps
from inspect import Parameter, signature

import kubernetes.client as k8s
from kfp import dsl

from ..auth import IAP_CLIENT_ID


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


def create_container_environment():
    env_vars = [
        k8s.V1EnvVar(
            name=IAP_CLIENT_ID, value=os.environ.get(IAP_CLIENT_ID, "")
        ),
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
    return ["_"] + list(
        itertools.chain(
            *[[param, dsl.PipelineParam(param)] for param in paramter_names]
        )
    )
