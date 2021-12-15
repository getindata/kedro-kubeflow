import logging
import os
from typing import Dict

import kubernetes.client as k8s
from kfp import dsl

from ..auth import IAP_CLIENT_ID
from ..utils import clean_name, is_mlflow_enabled
from .utils import create_params, maybe_add_params


class OnePodPipelineGenerator(object):
    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.project_name = project_name
        self.context = context
        dsl.ContainerOp._DISABLE_REUSABLE_COMPONENT_WARNING = True
        self.run_config = config.run_config
        self.catalog = context.config_loader.get("catalog*")

    def generate_pipeline(self, pipeline, image, image_pull_policy):
        @dsl.pipeline(self.project_name, self.run_config.description)
        @maybe_add_params(self.context.params)
        def convert_kedro_pipeline_to_kfp() -> None:
            dsl.get_pipeline_conf().set_ttl_seconds_after_finished(
                self.run_config.ttl
            )
            kfp_ops = self._build_kfp_ops(pipeline, image, image_pull_policy)

            for _, op in kfp_ops.items():
                op.execution_options.caching_strategy.max_cache_staleness = (
                    self.run_config.max_cache_staleness
                )

        return convert_kedro_pipeline_to_kfp

    def _build_kfp_ops(
        self,
        pipeline,
        image,
        image_pull_policy,
    ) -> Dict[str, dsl.ContainerOp]:
        """Build kfp container graph from Kedro node dependencies."""
        kfp_ops = {}

        nodes_env = [
            k8s.V1EnvVar(
                name=IAP_CLIENT_ID, value=os.environ.get(IAP_CLIENT_ID, "")
            )
        ]

        if is_mlflow_enabled():
            print("MLFLOW enabled")
            kfp_ops["mlflow-start-run"] = dsl.ContainerOp(
                name="mlflow-start-run",
                image=image,
                command=["kedro"],
                arguments=[
                    "kubeflow",
                    "--env",
                    self.context.env,
                    "mlflow-start",
                    dsl.RUN_ID_PLACEHOLDER,
                ],
                container_kwargs={
                    "env": nodes_env,
                    "image_pull_policy": image_pull_policy,
                },
                file_outputs={"mlflow_run_id": "/tmp/mlflow_run_id"},
            )

            nodes_env.append(
                k8s.V1EnvVar(
                    "MLFLOW_RUN_ID", kfp_ops["mlflow-start-run"].output
                )
            )

        kwargs = {"env": nodes_env, "image_pull_policy": image_pull_policy}
        default_resources = self.run_config.resources.get_for("__default__")
        if default_resources:
            kwargs["resources"] = k8s.V1ResourceRequirements(
                limits=default_resources, requests=default_resources
            )

        kfp_ops[self.project_name] = dsl.ContainerOp(
            name=clean_name(pipeline),
            image=image,
            command=["kedro"],
            arguments=[
                "run",
                "--env",
                self.context.env,
                "--params",
                create_params(self.context.params.keys()),
                "--pipeline",
                pipeline,
            ],
            container_kwargs=kwargs,
            file_outputs={
                output: f"/home/kedro/{self.catalog[output]['filepath']}"
                for output in self.catalog
                if "filepath" in self.catalog[output]
                and self.run_config.store_kedro_outputs_as_kfp_artifacts
            },
        )

        return kfp_ops
