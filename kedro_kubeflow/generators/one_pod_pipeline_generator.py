import logging

from kedro.framework.context import KedroContext
from kfp import dsl

from ..utils import clean_name
from .utils import (
    create_arguments_from_parameters,
    create_command_using_params_dumper,
    create_container_environment,
    create_pipeline_exit_handler,
    customize_op,
    is_local_fs,
    maybe_add_params,
    merge_namespaced_params_to_dict,
)


class OnePodPipelineGenerator(object):
    log = logging.getLogger(__name__)

    def __init__(self, config, project_name, context):
        self.project_name = project_name
        self.context: KedroContext = context
        dsl.ContainerOp._DISABLE_REUSABLE_COMPONENT_WARNING = True
        self.run_config = config.run_config
        self.catalog = context.config_loader.get("catalog")

    def generate_pipeline(self, pipeline, image, image_pull_policy):
        merged_params = merge_namespaced_params_to_dict(self.context.params)

        @dsl.pipeline(self.project_name, self.run_config.description)
        @maybe_add_params(merged_params)
        def convert_kedro_pipeline_to_kfp() -> None:
            dsl.get_pipeline_conf().set_ttl_seconds_after_finished(self.run_config.ttl)
            with create_pipeline_exit_handler(
                pipeline,
                image,
                image_pull_policy,
                self.run_config,
                self.context,
            ):
                self._build_kfp_op(pipeline, merged_params, image, image_pull_policy)

        return convert_kedro_pipeline_to_kfp

    def _build_kfp_op(
        self,
        pipeline,
        params,
        image,
        image_pull_policy,
    ) -> dsl.ContainerOp:
        container_op = dsl.ContainerOp(
            name=clean_name(pipeline),
            image=image,
            command=create_command_using_params_dumper(
                "kedro " "run " f"--env {self.context.env} " f"--pipeline {pipeline} " f"--config config.yaml"
            ),
            arguments=create_arguments_from_parameters(params.keys()),
            container_kwargs={"env": create_container_environment()},
            file_outputs={
                output: f"/home/kedro/{self.catalog[output]['filepath']}"
                for output in self.catalog
                if "filepath" in self.catalog[output]
                and is_local_fs(self.catalog[output]["filepath"])
                and self.run_config.store_kedro_outputs_as_kfp_artifacts
            },
        )

        container_op.execution_options.caching_strategy.max_cache_staleness = self.run_config.max_cache_staleness

        return customize_op(container_op, image_pull_policy, self.run_config)
