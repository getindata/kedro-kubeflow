from pydantic.utils import deep_update


class MinimalConfigMixin:
    def minimal_config(self, override=None):
        minimal = {
            "run_config": {
                "image": "asd",
                "experiment_name": "exp",
                "run_name": "unit tests",
            },
            "host": "localhost:8080",
        }
        if override:
            minimal = deep_update(minimal, override)
        return minimal
