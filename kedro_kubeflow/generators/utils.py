from functools import wraps
from inspect import Parameter, signature
from typing import Iterable

from kfp import dsl


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
