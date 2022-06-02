# import os
# from collections import defaultdict
# from enum import Enum
# from typing import Dict, List, Optional
#
# from kubernetes.client import V1Volume
# from pydantic import BaseModel, validator, ValidationError
# from pydantic.fields import ModelField
#
#
# class ResourcesConfig(BaseModel):
#     cpu: Optional[str]
#     memory: Optional[str]
#
#
# class TolerationConfig(BaseModel):
#     key: str
#     operator: str
#     value: Optional[str] = None
#     effect: str
#
#
# class RetryPolicyConfig(BaseModel):
#     num_retries: int
#     backoff_duration: str
#     backoff_factor: float
#
#
# class VolumeConfig(BaseModel):
#     storageclass: Optional[str] = None
#     size: str = "1Gi"
#     access_modes: List[str] = ["ReadWriteOnce"]
#     skip_init: bool = False
#     keep: bool = False
#     owner: int = 0
#
#
# class NodeMergeStrategyEnum(str, Enum):
#     none = "none"
#     full = "full"
#
#
# class ExtraVolumeConfig(BaseModel):
#     volume: dict
#     mount_path: str
#
#     @validator("volume")
#     def volume_validator(cls, value):
#         try:
#             V1Volume(**value)
#         except:
#             raise ValueError(
#                 "Cannot construct kubernetes.client.models.v1_volume.V1Volume from the passed `volume` field"
#             )
#         return value
#
#
# class RunConfig(BaseModel):
#     image: str
#     image_pull_policy: str = "IfNotPresent"
#     root: Optional[str]
#     experiment_name: str
#     run_name: str
#     scheduled_run_name: Optional[str]
#     description: Optional[str] = None
#     resources: Optional[Dict[str, ResourcesConfig]] = dict(
#         __default__=ResourcesConfig(cpu="500m", memory="1024Mi")
#     )
#     tolerations: Optional[Dict[str, List[TolerationConfig]]] = None
#     retry_policy: Optional[Dict[str, RetryPolicyConfig]] = None
#     volume: Optional[VolumeConfig] = None
#     extra_volumes: Optional[Dict[str, List[ExtraVolumeConfig]]] = defaultdict(
#         lambda: []
#     )
#     wait_for_completion: bool = False
#     store_kedro_outputs_as_kfp_artifacts: bool = True
#     max_cache_staleness: Optional[str] = None
#     ttl: int = 3600 * 24 * 7
#     on_exit_pipeline: Optional[str] = None
#     node_merge_strategy: NodeMergeStrategyEnum = NodeMergeStrategyEnum.none
#
#
# class PluginConfig(BaseModel):
#     host: str
#     run_config: RunConfig
#     project_id: str
#     region: str
#
#     @staticmethod
#     def sample_config(**kwargs):
#         return DEFAULT_CONFIG_TEMPLATE.format(**kwargs)
#
#     @staticmethod
#     def initialize_github_actions(project_name, where, templates_dir):
#         os.makedirs(where / ".github/workflows", exist_ok=True)
#         for template in ["on-merge-to-master.yml", "on-push.yml"]:
#             file_path = where / ".github/workflows" / template
#             template_file = templates_dir / f"github-{template}"
#             with open(template_file, "r") as tfile, open(file_path, "w") as f:
#                 f.write(tfile.read().format(project_name=project_name))
