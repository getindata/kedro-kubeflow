import os
from functools import lru_cache
from typing import Any, Dict

from kedro import __version__ as kedro_version
from kedro.config import TemplatedConfigLoader
from kedro.framework.session import KedroSession
from semver import VersionInfo

from .config import PluginConfig


class EnvTemplatedConfigLoader(TemplatedConfigLoader):
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
        *,
        base_env: str = "base",
        default_run_env: str = "local"
    ):
        super().__init__(
            conf_source,
            env=env,
            runtime_params=runtime_params,
            globals_dict=self.read_env(),
            base_env=base_env,
            default_run_env=default_run_env,
        )

    def read_env(self) -> Dict:
        config = EnvTemplatedConfigLoader.ENV_DEFAULTS.copy()
        overrides = dict(
            [
                (k.replace(EnvTemplatedConfigLoader.VAR_PREFIX, "").lower(), v)
                for k, v in os.environ.copy().items()
                if k.startswith(EnvTemplatedConfigLoader.VAR_PREFIX)
            ]
        )
        config.update(**overrides)
        return config


class ContextHelper(object):

    CONFIG_FILE_PATTERN = "kubeflow*"

    def __init__(self, metadata, env):
        self._metadata = metadata
        self._env = env

    @property
    def project_name(self):
        return self._metadata.project_name

    @property
    @lru_cache()
    def session(self):
        return KedroSession.create(self._metadata.package_name, env=self._env)

    @property
    def env(self):
        return self._env

    @property
    def context(self):
        return self.session.load_context()

    @property
    @lru_cache()
    def config(self) -> PluginConfig:
        raw = EnvTemplatedConfigLoader(
            self.context.config_loader.conf_source,
            env=self._env,
        ).get(self.CONFIG_FILE_PATTERN)
        return PluginConfig(**raw)

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
        return self.context.project_name

    @property
    def context(self):
        return self.session.load_context()
