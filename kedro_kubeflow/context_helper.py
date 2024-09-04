import os
from functools import cached_property, lru_cache
from typing import Any, Dict

from kedro import __version__ as kedro_version
from kedro.config import (
    AbstractConfigLoader,
    MissingConfigException,
    OmegaConfigLoader,
)
from kedro.framework.session import KedroSession
from omegaconf import DictConfig, OmegaConf
from omegaconf.resolvers import oc
from semver import VersionInfo

from .config import PluginConfig


class EnvTemplatedConfigLoader(OmegaConfigLoader):
    """Config loader that can substitute $(commit_id) and $(branch_name)
    placeholders with information taken from env variables."""

    VAR_PREFIX = "KEDRO_CONFIG_"
    # defaults provided so default variables ${commit_id|dirty} work for some entries
    ENV_DEFAULTS = {"commit_id": None, "branch_name": None}

    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
        config_patterns: Dict[str, Any] = None,
        *,
        base_env: str = "base",
        default_run_env: str = "local",
    ):
        import warnings  # TODO remove this class

        warnings.warn(
            "EnvTemplatedConfigLoader is deprecated and will be removed next release,"
            " please use OmegaConfigLoader with oc.env resolver"
        )
        self.read_env()

        super().__init__(
            conf_source,
            env=env,
            runtime_params=runtime_params,
            config_patterns=config_patterns,
            base_env=base_env,
            default_run_env=default_run_env,
            custom_resolvers={"oc.env": oc.env},
        )

    @staticmethod
    def read_env():
        config = EnvTemplatedConfigLoader.ENV_DEFAULTS.copy()
        overrides = dict(
            [
                (k.replace(EnvTemplatedConfigLoader.VAR_PREFIX, "").lower(), v)
                for k, v in os.environ.copy().items()
                if k.startswith(EnvTemplatedConfigLoader.VAR_PREFIX)
            ]
        )
        config.update(**overrides)
        os.environ.update({k: v for k, v in config.items() if v is not None})


class ContextHelper(object):

    CONFIG_FILE_PATTERN = "kubeflow*"
    CONFIG_KEY = "kubeflow"

    def __init__(self, metadata, env):
        self._metadata = metadata
        self._env = env

    @property
    def project_name(self):
        return self._metadata.project_name

    @property
    @lru_cache()
    def session(self):
        return KedroSession.create(self._metadata.project_path, env=self._env)

    @property
    def env(self):
        return self._env

    @property
    def context(self):
        return self.session.load_context()

    @cached_property
    def config(self) -> PluginConfig:
        cl: AbstractConfigLoader = self.context.config_loader
        try:
            if self.CONFIG_KEY not in cl.config_patterns.keys():
                cl.config_patterns.update(
                    {
                        self.CONFIG_KEY: [
                            self.CONFIG_FILE_PATTERN,
                            f"{self.CONFIG_FILE_PATTERN}/**",
                        ]
                    }
                )
            kubeflow_config = self._ensure_obj_is_dict(cl.get(self.CONFIG_KEY))
        except MissingConfigException:
            if not isinstance(cl, OmegaConfigLoader):
                raise ValueError(
                    f"You're using a custom config loader: {cl.__class__.__qualname__}{os.linesep}"
                    f"you need to add the {self.CONFIG_KEY} config to it.{os.linesep}"
                    f"Make sure you add {self.CONFIG_FILE_PATTERN} to config_pattern in CONFIG_LOADER_ARGS "
                    f"in the settings.py file.{os.linesep}"
                    """Example:
CONFIG_LOADER_ARGS = {
    # other args
    "config_patterns": {"kubeflow": ["kubeflow*"]}
}
                    """.strip()
                )
            else:
                raise ValueError(
                    "Missing kubeflow.yml files in configuration. " "Make sure that you configure your project first"
                )
        return PluginConfig.parse_obj(kubeflow_config)

    def _ensure_obj_is_dict(self, obj):
        if isinstance(obj, DictConfig):
            obj = OmegaConf.to_container(obj)
        elif isinstance(obj, dict) and any(isinstance(v, DictConfig) for v in obj.values()):
            obj = {k: (OmegaConf.to_container(v) if isinstance(v, DictConfig) else v) for k, v in obj.items()}
        return obj

    @property
    @lru_cache()
    def kfp_client(self):
        from .kfpclient import KubeflowClient

        return KubeflowClient(
            self.config,
            self.project_name,
            self.context,
        )

    @staticmethod
    def init(metadata, env):
        version = VersionInfo.parse(kedro_version)
        if version.match(">=0.17.0"):
            return ContextHelper(metadata, env)
        else:
            return ContextHelper16(metadata, env)


class ContextHelper16(ContextHelper):
    """KedroKubeflowConfig vairant for compatibility with Kedro 1.6"""

    @property
    def project_name(self):
        return self.context.project_path.name

    @property
    def context(self):
        return self.session.load_context()
