import os
from functools import wraps
from inspect import Parameter, signature
from typing import Iterable

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


def create_params(param_keys: Iterable[str]) -> str:
    return ",".join(
        [f"{param}:{dsl.PipelineParam(param)}" for param in param_keys]
    )


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
