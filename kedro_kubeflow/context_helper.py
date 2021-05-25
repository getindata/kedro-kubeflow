from functools import lru_cache
from pathlib import Path

from kedro import __version__ as kedro_version
from semver import VersionInfo

from .config import PluginConfig
from .kfpclient import KubeflowClient


class ContextHelper(object):

    CONFIG_FILE_PATTERN = "kubeflow*"

    def __init__(
        self,
        metadata,
        env,
        username,
        password,
        experiment_namespace,
        namespace,
    ):
        self._metadata = metadata
        self._env = env
        self._username = username
        self._password = password
        self._experiment_namespace = experiment_namespace
        self._namespace = namespace

    @property
    def project_name(self):
        return self._metadata.project_name

    @property
    def context(self):
        from kedro.framework.session import KedroSession

        return KedroSession.create(
            self._metadata.package_name,
            env=self._env,
            extra_params={},
        ).load_context()

    @property
    @lru_cache()
    def config(self) -> PluginConfig:
        raw = self.context.config_loader.get(self.CONFIG_FILE_PATTERN)
        return PluginConfig(raw)

    @property
    @lru_cache()
    def connection(self) -> PluginConfig:
        raw = self.context.config_loader.get(self.CONFIG_FILE_PATTERN)
        return PluginConfig(raw)

    @property
    @lru_cache()
    def kfp_client(self):
        return KubeflowClient(
            self.config,
            self.project_name,
            self.context,
            self._username,
            self._password,
            self._namespace,
        )

    @staticmethod
    def init(
        metadata,
        env,
        username,
        password,
        experiment_namespace,
        namespace,
    ):
        version = VersionInfo.parse(kedro_version)
        if version.match(">=0.17.0"):
            return ContextHelper(
                metadata,
                env,
                username,
                password,
                experiment_namespace,
                namespace,
            )
        else:
            return ContextHelper16(
                metadata,
                env,
                username,
                password,
                experiment_namespace,
                namespace,
            )


class ContextHelper16(ContextHelper):
    """KedroKubeflowConfig vairant for compatibility with Kedro 1.6"""

    @property
    def project_name(self):
        return self.context.project_name

    @property
    def context(self):
        from kedro.framework.context import load_context

        return load_context(Path.cwd(), env=self._env)
