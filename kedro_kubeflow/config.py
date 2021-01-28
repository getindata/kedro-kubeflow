import os

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
  run_name: {run_name}

  # Optional pipeline description
  #description: "Very Important Pipeline"

  # Flag indicating if the run-once should wait for the pipeline to finish
  wait_for_completion: False

  # How long to keep underlying Argo workflow (together with pods and data
  # volume after pipeline finishes) [in seconds]. Default: 1 week
  ttl: 604800

  # Optional volume specification
  volume:

    # Storage class - use null (or no value) to use the default storage
    # class deployed on the Kubernetes cluster
    storageclass: # default

    # The size of the volume that is created. Applicable for some storage
    # classes
    size: 1Gi

    # Access mode of the volume used to exchange data. ReadWriteMany is
    # preferred, but it is not supported on some environements (like GKE)
    # Default value: ReadWriteOnce
    #access_modes: [ReadWriteMany]

    # Flag indicating if the data-volume-init step (copying raw data to the
    # fresh volume) should be skipped
    skip_init: False

    # Allows to specify user executing pipelines within containers
    # Default: root user (to avoid issues with volumes in GKE)
    owner: 0

    # Flak indicating if volume for inter-node data exchange should be
    # kept after the pipeline is deleted
    keep: False

  # Optional section allowing adjustment of the resources
  # reservations and limits for the nodes
  resources:

    # For nodes that require more RAM you can increase the "memory"
    data_import_step:
      memory: 2Gi

    # Training nodes can utilize more than one CPU if the algoritm
    # supports it
    model_training:
      cpu: 8
      memory: 1Gi

    # GPU-capable nodes can request 1 GPU slot
    tensorflow_step:
      nvidia.com/gpu: 1

    # Default settings for the nodes
    __default__:
      cpu: 200m
      memory: 64Mi
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
        return self._get_or_default("access_modes", ["ReadWriteOnce"])

    @property
    def skip_init(self):
        return self._get_or_default("skip_init", False)

    @property
    def keep(self):
        return self._get_or_default("keep", False)

    @property
    def owner(self):
        return self._get_or_default("owner", 0)

    def _get_prefix(self):
        return "run_config.volume."


class NodeResources(Config):
    def is_set_for(self, node_name):
        return self.get_for(node_name) != {}

    def get_for(self, node_name):
        defaults = self._get_or_default("__default__", {})
        node_specific = self._get_or_default(node_name, {})
        return {**defaults, **node_specific}


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
    def description(self):
        return self._get_or_default("description", None)

    @property
    def resources(self):
        return NodeResources(self._get_or_default("resources", {}))

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

    @property
    def ttl(self):
        return int(self._get_or_default("ttl", 3600 * 24 * 7))

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

    @staticmethod
    def initialize_github_actions(project_name, where, templates_dir):
        os.makedirs(where / ".github/workflows", exist_ok=True)
        for template in ["on-merge-to-master.yml", "on-push.yml"]:
            file_path = where / ".github/workflows" / template
            template_file = templates_dir / f"github-{template}"
            with open(template_file, "r") as tfile, open(file_path, "w") as f:
                f.write(tfile.read().format(project_name=project_name))
