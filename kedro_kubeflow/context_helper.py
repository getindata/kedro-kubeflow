import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable

from kedro import __version__ as kedro_version
from kedro.config import TemplatedConfigLoader
from semver import VersionInfo

from .config import PluginConfig


class EnvTemplatedConfigLoader(TemplatedConfigLoader):
    """Config loader that can substitute $(commit_id) and $(branch_name)
    placeholders with information taken from env variables."""

    VAR_PREFIX = "KEDRO_CONFIG_"
    # defaults provided so default variables ${commit_id|dirty} work for some entries
    ENV_DEFAULTS = {"commit_id": None, "branch_name": None}

    def __init__(self, conf_paths: Iterable[str]):
        super().__init__(conf_paths, globals_dict=self.read_env())

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
        from kedro.framework.session import KedroSession

        return KedroSession.create(self._metadata.package_name, env=self._env)

    @property
    def context(self):
        return self.session.load_context()

    @property
    @lru_cache()
    def config(self) -> PluginConfig:
        raw = EnvTemplatedConfigLoader(
            self.context.config_loader.conf_paths
        ).get(self.CONFIG_FILE_PATTERN)
        return PluginConfig(raw)

    @property
    @lru_cache()
    def kfp_client(self):
        if self.config.is_vertex_ai_pipelines:
            from .vertex_ai.client import VertexAIPipelinesClient

            return VertexAIPipelinesClient(
                self.config, self.project_name, self.context
            )
        else:
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
        from kedro.framework.context import load_context

        return load_context(Path.cwd(), env=self._env)
