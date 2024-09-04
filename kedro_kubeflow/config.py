import logging
import os
from collections import defaultdict
from enum import Enum
from importlib import import_module
from typing import Any, Dict, List, Optional, Type, Union

from kubernetes import client as k8s_client
from kubernetes.client import V1Volume
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_TEMPLATE = """
# Base url of the Kubeflow Pipelines, should include the schema (http/https)
host: {url}

# Configuration used to run the pipeline
run_config:

  # Name of the image to run as the pipeline steps
  image: {image}

  # Pull policy to be used for the steps. Use Always if you push the images
  # on the same tag, or Never if you use only local images
  image_pull_policy: IfNotPresent

  # Name of the kubeflow experiment to be created
  experiment_name: {project}

  # Name of the run for run-once, templated with the run-once parameters
  run_name: {run_name}

  # Name of the scheduled run, templated with the schedule parameters
  scheduled_run_name: {run_name}

  # Optional pipeline description
  #description: "Very Important Pipeline"

  # Flag indicating if the run-once should wait for the pipeline to finish
  wait_for_completion: False

  # How long to keep underlying Argo workflow (together with pods and data
  # volume after pipeline finishes) [in seconds]. Default: 1 week
  ttl: 604800

  # What Kedro pipeline should be run as the last step regardless of the
  # pipeline status. Used to send notifications or raise the alerts
  # on_exit_pipeline: notify_via_slack

  # This sets the caching option for pipeline using
  # execution_options.caching_strategy.max_cache_staleness
  # See https://en.wikipedia.org/wiki/ISO_8601 in section 'Duration'
  # max_cache_staleness: P0D

  # Set to false to disable kfp artifacts exposal
  # This setting can be useful if you don't want to store
  # intermediate results in the MLMD
  # store_kedro_outputs_as_kfp_artifacts: True

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
  # node_merge_strategy: none

  # Optional volume specification
  volume:

    # Storage class - use null (or no value) to use the default storage
    # class deployed on the Kubernetes cluster
    storageclass: null # default

    # The size of the volume that is created. Applicable for some storage
    # classes
    size: 1Gi

    # Access mode of the volume used to exchange data. ReadWriteMany is
    # preferred, but it is not supported on some environements (like GKE)
    # Default value: ReadWriteOnce
    # access_modes: [ReadWriteMany]

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
      cpu: 1
      memory: 1Gi

  # Optional section to allow mounting additional volumes (such as EmptyDir)
  # to specific nodes
  extra_volumes:
    tensorflow_step:
    - mount_path: /dev/shm
      volume:
        name: shared_memory
        empty_dir:
          cls: V1EmptyDirVolumeSource
          params:
            medium: Memory

  # Optional section to provide retry policy for the steps
  # and default policy for steps with no policy specified
  retry_policy:
    # 90 retries every 5 minutes
    wait_for_partition_availability:
      num_retries: 90
      backoff_duration: 5m
      backoff_factor: 1

    # 4 retries after: 1 minute, 2 minutes, 4 minutes, 8 minutes
    __default__:
      num_retries: 4
      backoff_duration: 60s
      backoff_factor: 2
    # Optional section allowing adjustment of the resources
  # reservations and limits for the nodes
  # optional section for specifying tolerations per node.
  # the __default__ section will be loaded if nothing is specified for a particular node.
  tolerations:
    __default__:
    - key: "dedicated"
      operator: "Equal"
      value: "ml-ops"
      effect: "NoSchedule"
    node_a:
    - key: "gpu_resource"
      operator: "Equal"
      value: "voltaire"
      effect: "NoSchedule"
"""


class DefaultConfigDict(defaultdict):
    def __getitem__(self, key):
        defaults: BaseModel = super().__getitem__("__default__")
        this: BaseModel = super().__getitem__(key)
        return defaults.copy(update=this.dict(exclude_none=True)) if defaults else this


class ResourceConfig(dict):
    def __getitem__(self, key):
        defaults: dict = super().get("__default__")
        this: dict = super().get(key, {})
        updated_defaults = defaults.copy()
        updated_defaults.update(this)
        return updated_defaults


class TolerationConfig(BaseModel):
    key: str
    operator: str
    value: Optional[str] = None
    effect: str


class RetryPolicyConfig(BaseModel):
    num_retries: int
    backoff_duration: str
    backoff_factor: int


class VolumeConfig(BaseModel):
    storageclass: Optional[str] = None
    size: str = "1Gi"
    access_modes: List[str] = ["ReadWriteOnce"]
    skip_init: bool = False
    keep: bool = False
    owner: int = 0


class NodeMergeStrategyEnum(str, Enum):
    none = "none"
    full = "full"


class ObjectKwargs(BaseModel):
    cls: str
    params: Dict[str, Union["ObjectKwargs", Any]]


class ExtraVolumeConfig(BaseModel):
    volume: Dict[str, Union[ObjectKwargs, List[ObjectKwargs], Any]]
    mount_path: str

    def as_v1volume(self) -> V1Volume:
        return self._construct_v1_volume(self.volume)

    @staticmethod
    def _resolve_cls(cls_name):
        if hasattr(k8s_client, cls_name):
            return getattr(k8s_client, cls_name, None)
        else:
            module_name, class_name = cls_name.rsplit(".", 1)
            module = import_module(module_name)
            return getattr(module, class_name, None)

    @staticmethod
    def _construct(value: Union[ObjectKwargs, Any]):
        if isinstance(value, ObjectKwargs):
            assert (
                actual_cls := ExtraVolumeConfig._resolve_cls(value.cls)
            ) is not None, f"Cannot import class {value.cls}"
            return actual_cls(**{k: ExtraVolumeConfig._construct(v) for k, v in value.params.items()})
        elif isinstance(value, list):
            return [ExtraVolumeConfig._construct(ObjectKwargs.parse_obj(v)) for v in value]
        else:
            return value

    @classmethod
    def _construct_v1_volume(cls, value: dict):
        return V1Volume(**{k: ExtraVolumeConfig._construct(v) for k, v in value.items()})

    @validator("volume")
    def volume_validator(cls, value):
        try:
            cls._construct_v1_volume(value)
        except Exception as ex:
            logger.exception(
                "Cannot construct kubernetes.client.models.v1_volume.V1Volume " "from the passed `volume` field",
            )
            raise ex
        return value


class RunConfig(BaseModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if "scheduled_run_name" not in kwargs:
            self.scheduled_run_name = kwargs["run_name"]

    @staticmethod
    def _create_default_dict_with(value: dict, default, dict_cls: Type = DefaultConfigDict):
        default_value = (value := value or {}).get("__default__", default)
        return dict_cls(lambda: default_value, value)

    @validator("resources", always=True)
    def _validate_resources(cls, value):
        default = ResourceConfig({"__default__": {"cpu": "500m", "memory": "1024Mi"}})
        if isinstance(value, dict):
            default.update(value)
        elif value is not None:
            logger.error(f"Unknown type for resource config {type(value)}")
            raise TypeError(f"Unknown type for resource config {type(value)}")
        return default

    @validator("retry_policy", always=True)
    def _validate_retry_policy(cls, value):
        return RunConfig._create_default_dict_with(value, None)

    @validator("tolerations", always=True)
    def _validate_tolerations(cls, value):
        return RunConfig._create_default_dict_with(value, [], defaultdict)

    @validator("extra_volumes", always=True)
    def _validate_extra_volumes(cls, value):
        return RunConfig._create_default_dict_with(value, [], defaultdict)

    image: str
    image_pull_policy: str = "IfNotPresent"
    root: Optional[str]
    experiment_name: str
    run_name: str
    scheduled_run_name: Optional[str]
    description: Optional[str] = None
    resources: Optional[Dict[str, ResourceConfig]]
    tolerations: Optional[Dict[str, List[TolerationConfig]]]
    retry_policy: Optional[Dict[str, Optional[RetryPolicyConfig]]]
    volume: Optional[VolumeConfig] = None
    extra_volumes: Optional[Dict[str, List[ExtraVolumeConfig]]] = None
    wait_for_completion: bool = False
    store_kedro_outputs_as_kfp_artifacts: bool = True
    max_cache_staleness: Optional[str] = None
    ttl: int = 3600 * 24 * 7
    on_exit_pipeline: Optional[str] = None
    node_merge_strategy: NodeMergeStrategyEnum = NodeMergeStrategyEnum.none


class PluginConfig(BaseModel):
    host: str
    run_config: RunConfig

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
