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

  # Location of Vertex AI GCS root, required only for vertex ai pipelines configuration
  #root: bucket_name/gcs_suffix

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

  # This sets the caching option for pipeline using
  # execution_options.caching_strategy.max_cache_staleness
  # See https://en.wikipedia.org/wiki/ISO_8601 in section 'Duration'
  #max_cache_staleness: P0D

  # Set to false to disable kfp artifacts exposal
  # This setting can be useful if you don't want to store
  # intermediate results in the MLMD
  #store_kedro_outputs_as_kfp_artifacts: True

  # Strategy used to generate Kubeflow pipeline nodes from Kedro nodes
  # Available strategies:
  #  * none (default) - nodes in Kedro pipeline are mapped to separate nodes
  #                     in Kubeflow pipelines. This strategy allows to inspect
  #                     a whole processing graph in Kubeflow UI and override
  #                     resources for each node (because they are run in separate pods)
  #                     Although, performance may not be optimal due to potential
  #                     sharing of intermediate datasets through disk.
  #  * full - nodes in Kedro pipeline are mapped to one node in Kubeflow pipelines.
  #           This strategy mitigate potential performance issues with `none` strategy
  #           but at the cost of degraded user experience within Kubeflow UI: a graph
  #           is collapsed to one node.
  #node_merge_strategy: none

  # Optional volume specification (only for non vertex-ai)
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


class VertexAiNetworkingConfig(Config):
    @property
    def vpc(self):
        return self._get_or_default("vpc", None)

    @property
    def host_aliases(self):
        aliases = self._get_or_default("host_aliases", [])
        return {alias["ip"]: alias["hostnames"] for alias in aliases}


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
    def root(self):
        return self._get_or_fail("root")

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
    def store_kedro_outputs_as_kfp_artifacts(self):
        return bool(
            self._get_or_default("store_kedro_outputs_as_kfp_artifacts", True)
        )

    @property
    def max_cache_staleness(self):
        return str(self._get_or_default("max_cache_staleness", None))

    @property
    def ttl(self):
        return int(self._get_or_default("ttl", 3600 * 24 * 7))

    @property
    def vertex_ai_networking(self):
        return VertexAiNetworkingConfig(
            self._get_or_default("vertex_ai_networking", {})
        )

    @property
    def node_merge_strategy(self):
        strategy = str(self._get_or_default("node_merge_strategy", "none"))
        if strategy not in ["none", "full"]:
            raise ValueError(
                f"Invalid {self._get_prefix()}node_merge_strategy: {strategy}"
            )
        else:
            return strategy

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

    @property
    def project_id(self):
        return self._get_or_fail("project_id")

    @property
    def region(self):
        return self._get_or_fail("region")

    @property
    def is_vertex_ai_pipelines(self):
        return self.host == "vertex-ai-pipelines"

    @staticmethod
    def initialize_github_actions(project_name, where, templates_dir):
        os.makedirs(where / ".github/workflows", exist_ok=True)
        for template in ["on-merge-to-master.yml", "on-push.yml"]:
            file_path = where / ".github/workflows" / template
            template_file = templates_dir / f"github-{template}"
            with open(template_file, "r") as tfile, open(file_path, "w") as f:
                f.write(tfile.read().format(project_name=project_name))
