from kedro.config import MissingConfigException

DEFAULT_CONFIG_TEMPLATE = """
# Base url of the Kubeflow Pipelines, should include the schema (http/https)
host: {url}

# Configuration used to run the pipeline
run_config:

  # Name of the image to run as the pipeline steps
  image: {image}

  # Pull pilicy to be used for the steps. Use Always if you push the images
  # on the same tag, or Never if you use only local images
  image_pull_policy: IfNotPresent

  # Name of the kubeflow experiment to be created
  experiment_name: {project}

  # Name of the run for run-once
  run_name: {project}

  # Flag indicating if the run-once should wait for the pipeline to finish
  wait_for_completion: False

  # Optional volume specification
  volume:

    # Storage class - use null (or no value) to use the default storage
    # class deployed on the Kubernetes cluster
    storageclass: # default

    # The size of the volume that is created. Applicable for some storage
    # classes
    size: 1Gi

    # Access mode of the volume used to exchange data. ReadWriteOnce doesn't
    # allos multiple nodes to bind the volume at the same time, but may be
    # the only option on some environments. Default value: ReadWriteMany
    #access_modes: [ReadWriteOnce]

    # Flag indicating if the data-volume-init step (copying raw data to the
    # fresh volume) should be skipped
    skip_init: False
"""


class Config(object):
    def __init__(self, raw):
        self._raw = raw

    def _get_or_default(self, prop, default):
        return self._raw.get(prop, default)

    def _get_or_fail(self, prop):
        if prop in self._raw.keys():
            return self._raw[prop]
        else:
            raise MissingConfigException(
                f"Missing required configuration: '{self._get_prefix()}{prop}'."
            )

    def _get_prefix(self):
        return ""

    def __eq__(self, other):
        return self._raw == other._raw


class VolumeConfig(Config):
    @property
    def storageclass(self):
        return self._get_or_default("storageclass", None)

    @property
    def size(self):
        return self._get_or_default("size", "1Gi")

    @property
    def access_modes(self):
        return self._get_or_default("access_modes", ["ReadWriteMany"])

    @property
    def skip_init(self):
        return self._get_or_default("skip_init", False)

    def _get_prefix(self):
        return "run_config.volume."


class RunConfig(Config):
    @property
    def image(self):
        return self._get_or_fail("image")

    @property
    def image_pull_policy(self):
        return self._get_or_default("image_pull_policy", "IfNotPresent")

    @property
    def experiment_name(self):
        return self._get_or_fail("experiment_name")

    @property
    def run_name(self):
        return self._get_or_fail("run_name")

    @property
    def volume(self):
        if "volume" in self._raw.keys():
            cfg = self._get_or_fail("volume")
            return VolumeConfig(cfg)
        else:
            return None

    @property
    def wait_for_completion(self):
        return bool(self._get_or_default("wait_for_completion", False))

    def _get_prefix(self):
        return "run_config."


class PluginConfig(Config):
    @property
    def host(self):
        return self._get_or_fail("host")

    @property
    def run_config(self):
        cfg = self._get_or_fail("run_config")
        return RunConfig(cfg)

    @staticmethod
    def sample_config(**kwargs):
        return DEFAULT_CONFIG_TEMPLATE.format(**kwargs)
