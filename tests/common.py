import copy


def deep_update(mapping, updating_mapping):
    updated_mapping = copy.deepcopy(mapping)
    for k, v in updating_mapping.items():
        if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
            updated_mapping[k] = deep_update(updated_mapping[k], v)
        else:
            updated_mapping[k] = v
    return updated_mapping


class MinimalConfigMixin:
    def minimal_config(self, override=None):
        minimal = {
            "run_config": {
                "image": "asd",
                "experiment_name": "exp",
                "run_name": "unit tests",
                "node_merge_strategy": "none",
            },
            "host": "localhost:8080",
        }
        if override:
            minimal = deep_update(minimal, override)
        return minimal
