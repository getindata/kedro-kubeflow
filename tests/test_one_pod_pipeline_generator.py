"""Test generator"""

import datetime
import os
import unittest
from inspect import signature
from unittest.mock import MagicMock, patch

import kfp
from kedro.pipeline import Pipeline, node

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.generators.one_pod_pipeline_generator import (
    OnePodPipelineGenerator,
)
from tests.common import MinimalConfigMixin


def identity(input1: str):
    return input1  # pragma: no cover


class TestGenerator(unittest.TestCase, MinimalConfigMixin):
    def test_support_modification_of_pull_policy(self):
        # given
        self.create_generator()

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Never")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert len(dsl_pipeline.ops) == 1
            assert dsl_pipeline.ops["pipeline"].container.image == "unittest-image"
            assert dsl_pipeline.ops["pipeline"].container.image_pull_policy == "Never"

    def test_should_support_params_and_inject_them_to_the_node(self):
        # given
        self.create_generator(
            params={
                "param1": 0.3,
                "param2": 42,
                "param3": datetime.date(2022, 2, 24),
            }
        )

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
                default_params = signature(pipeline).parameters
                pipeline()

            # then
            assert len(default_params) == 3
            assert default_params["param1"].default == 0.3
            assert default_params["param2"].default == 42
            assert default_params["param3"].default == "2022-02-24"
            assert dsl_pipeline.ops["pipeline"].container.args[1:] == [
                "param1",
                "{{pipelineparam:op=;name=param1}}",
                "param2",
                "{{pipelineparam:op=;name=param2}}",
                "param3",
                "{{pipelineparam:op=;name=param3}}",
            ]

    def test_should_support_nested_params_and_inject_them_to_the_node(self):
        # given
        self.create_generator(
            params={
                "param1": {"nested1": {"nested2": 1, "nested3": 2}},
                "param2": 42,
                "param3": datetime.date(2022, 2, 24),
            }
        )

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
                default_params = signature(pipeline).parameters
                pipeline()

            # then
            assert len(default_params) == 3
            assert default_params["param1"].default == {"nested1": {"nested2": 1, "nested3": 2}}
            assert default_params["param2"].default == 42
            assert default_params["param3"].default == "2022-02-24"
            assert dsl_pipeline.ops["pipeline"].container.args[1:] == [
                "param1",
                "{{pipelineparam:op=;name=param1}}",
                "param2",
                "{{pipelineparam:op=;name=param2}}",
                "param3",
                "{{pipelineparam:op=;name=param3}}",
            ]

    def test_should_support_namespaced_params_and_inject_them_to_the_node(
        self,
    ):
        # given
        self.create_generator(
            params={
                "outer_namespace.inner_namespace1.param1": "outer_namespace.inner_namespace1.param1_v",
                "outer_namespace.inner_namespace1.param2": "outer_namespace.inner_namespace1.param2_v",
                "outer_namespace.inner_namespace2.param1": "outer_namespace.inner_namespace2.param1_v",
                "outer_namespace.inner_namespace2.param2": "outer_namespace.inner_namespace2.param2_v",
                "outer_namespace.param": "outer_namespace.param",
                "param1": 42,
            }
        )

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
                default_params = signature(pipeline).parameters
                pipeline()

            # then
            assert len(default_params) == 2
            assert default_params["outer_namespace"].default == {
                "inner_namespace1": {
                    "param1": "outer_namespace.inner_namespace1.param1_v",
                    "param2": "outer_namespace.inner_namespace1.param2_v",
                },
                "inner_namespace2": {
                    "param1": "outer_namespace.inner_namespace2.param1_v",
                    "param2": "outer_namespace.inner_namespace2.param2_v",
                },
                "param": "outer_namespace.param",
            }
            assert default_params["param1"].default == 42
            assert dsl_pipeline.ops["pipeline"].container.args[1:] == [
                "outer_namespace",
                "{{pipelineparam:op=;name=outer_namespace}}",
                "param1",
                "{{pipelineparam:op=;name=param1}}",
            ]

    def test_should_use_default_resources_spec_if_not_requested(self):
        # given
        self.create_generator(config={})

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert dsl_pipeline.ops["pipeline"].container.resources is not None
            assert dsl_pipeline.ops["pipeline"].container.resources.limits["cpu"]
            assert dsl_pipeline.ops["pipeline"].container.resources.limits["memory"]

    def test_should_add_resources_spec(self):
        # given
        self.create_generator(
            config={
                "resources": {
                    "__default__": {"cpu": "100m", "memory": "8Gi"},
                    "node1": {"cpu": "400m", "memory": "64Gi"},
                }
            }
        )

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            resources = dsl_pipeline.ops["pipeline"].container.resources
            assert resources.limits == {"cpu": "100m", "memory": "8Gi"}
            assert resources.requests == {"cpu": "100m", "memory": "8Gi"}

    def test_should_not_add_retry_policy_if_not_requested(self):
        # given
        self.create_generator(config={})

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            op = dsl_pipeline.ops["pipeline"]
            assert op.num_retries == 0
            assert op.retry_policy is None
            assert op.backoff_factor is None
            assert op.backoff_duration is None
            assert op.backoff_max_duration is None

    def test_should_add_retry_policy(self):
        # given
        self.create_generator(
            config={
                "retry_policy": {
                    "__default__": {
                        "num_retries": 4,
                        "backoff_duration": "60s",
                        "backoff_factor": 2,
                    },
                    "node1": {
                        "num_retries": 100,
                        "backoff_duration": "5m",
                        "backoff_factor": 1,
                    },
                }
            }
        )

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            op = dsl_pipeline.ops["pipeline"]
            assert op.num_retries == 4
            assert op.retry_policy == "Always"
            assert op.backoff_factor == 2
            assert op.backoff_duration == "60s"
            assert op.backoff_max_duration is None

    def test_should_set_description(self):
        # given
        self.create_generator(config={"description": "DESC"})

        # when
        pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Never")

        # then
        assert pipeline._component_description == "DESC"

    def test_artifact_registration(self):
        # given
        self.create_generator(
            catalog={
                "B": {
                    "type": "pandas.CSVDataSet",
                    "filepath": "data/02_intermediate/b.csv",
                }
            }
        )

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert dsl_pipeline.ops["pipeline"].file_outputs == {"B": "/home/kedro/data/02_intermediate/b.csv"}

    def test_should_skip_artifact_registration_if_requested(self):
        # given
        self.create_generator(
            catalog={
                "B": {
                    "type": "pandas.CSVDataSet",
                    "filepath": "data/02_intermediate/b.csv",
                }
            },
            config={"store_kedro_outputs_as_kfp_artifacts": False},
        )

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert dsl_pipeline.ops["pipeline"].file_outputs == {}

    def test_should_pass_kedro_config_env_to_nodes(self):
        # given
        self.create_generator(params={"param1": 0.3, "param2": 42})
        os.environ["KEDRO_CONFIG_MY_KEY"] = "42"
        os.environ["SOME_VALUE"] = "100"

        try:
            # when
            with patch(
                "kedro.framework.project.pipelines",
                new=self.pipelines_under_test,
            ):
                pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
                with kfp.dsl.Pipeline(None) as dsl_pipeline:
                    pipeline()

                # then
                env_values = {e.name: e.value for e in dsl_pipeline.ops["pipeline"].container.env}
                assert "KEDRO_CONFIG_MY_KEY" in env_values
                assert env_values["KEDRO_CONFIG_MY_KEY"] == "42"
                assert "SOME_VALUE" not in env_values
        finally:
            del os.environ["KEDRO_CONFIG_MY_KEY"]
            del os.environ["SOME_VALUE"]

    def test_should_pass_kubeflow_run_id_to_nodes(self):
        # given
        self.create_generator(params={"param1": 0.3, "param2": 42})

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            env_values = {e.name: e.value for e in dsl_pipeline.ops["pipeline"].container.env}
            assert "KUBEFLOW_RUN_ID" in env_values
            assert env_values["KUBEFLOW_RUN_ID"] == "{{workflow.uid}}"

    def test_should_generate_exit_handler_if_requested(self):
        # given
        self.create_generator(config={"on_exit_pipeline": "notify_via_slack"})

        # when
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert len(dsl_pipeline.ops) == 2
            assert "on-exit" in dsl_pipeline.ops
            assert (
                dsl_pipeline.ops["on-exit"]
                .container.command[-1]
                .endswith("kedro run --config config.yaml " "--env unittests --pipeline notify_via_slack")
            )

    def test_should_generate_exit_handler_with_max_staleness(self):
        # given
        self.create_generator(
            config={
                "on_exit_pipeline": "notify_via_slack",
                "max_cache_staleness": "P0D",
            }
        )

        # when
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline = self.generator_under_test.generate_pipeline("pipeline", "unittest-image", "Always")
            pipeline()

            assert dsl_pipeline.ops["on-exit"].execution_options.caching_strategy.max_cache_staleness == "P0D"

    def create_generator(self, config=None, params=None, catalog=None):
        if config is None:
            config = {}
        if params is None:
            params = {}
        if catalog is None:
            catalog = {}
        config_loader = MagicMock()
        config_loader.get.return_value = catalog
        context = type(
            "obj",
            (object,),
            {
                "env": "unittests",
                "params": params,
                "config_loader": config_loader,
            },
        )
        self.pipelines_under_test = {
            "pipeline": Pipeline(
                [
                    node(identity, "A", "B", name="node1"),
                    node(identity, "B", "C", name="node2"),
                ]
            )
        }
        self.generator_under_test = OnePodPipelineGenerator(
            config=PluginConfig(**self.minimal_config({"host": "http://unittest", "run_config": config})),
            project_name="my-awesome-project",
            context=context,
        )
