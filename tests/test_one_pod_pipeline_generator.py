"""Test generator"""

import os
import unittest
from inspect import signature
from unittest.mock import MagicMock

import kfp
from kedro.pipeline import Pipeline, node

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.generators.one_pod_pipeline_generator import (
    OnePodPipelineGenerator,
)


def identity(input1: str):
    return input1  # pragma: no cover


class TestGenerator(unittest.TestCase):
    def test_support_modification_of_pull_policy(self):
        # given
        self.create_generator()

        # when
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Never"
            )()

        # then
        assert len(dsl_pipeline.ops) == 1
        assert dsl_pipeline.ops["pipeline"].container.image == "unittest-image"
        assert (
            dsl_pipeline.ops["pipeline"].container.image_pull_policy == "Never"
        )

    def test_should_support_params_and_inject_them_to_the_node(self):
        # given
        self.create_generator(params={"param1": 0.3, "param2": 42})

        # when
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            default_params = signature(pipeline).parameters
            pipeline()

        # then
        assert len(default_params) == 2
        assert default_params["param1"].default == 0.3
        assert default_params["param2"].default == 42
        assert dsl_pipeline.ops["pipeline"].container.args == [
            "run",
            "--env",
            "unittests",
            "--params",
            "param1:{{pipelineparam:op=;name=param1}},"
            "param2:{{pipelineparam:op=;name=param2}}",
            "--pipeline",
            "pipeline",
        ]

    def test_should_not_add_resources_spec_if_not_requested(self):
        # given
        self.create_generator(config={})

        # when
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )()

        # then
        assert dsl_pipeline.ops["pipeline"].container.resources is None

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
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )()

        # then
        resources = dsl_pipeline.ops["pipeline"].container.resources
        assert resources.limits == {"cpu": "100m", "memory": "8Gi"}
        assert resources.requests == {"cpu": "100m", "memory": "8Gi"}

    def test_should_set_description(self):
        # given
        self.create_generator(config={"description": "DESC"})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Never"
        )

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
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )()

        # then
        assert dsl_pipeline.ops["pipeline"].file_outputs == {
            "B": "/home/kedro/data/02_intermediate/b.csv"
        }

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
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )()

        # then
        assert dsl_pipeline.ops["pipeline"].file_outputs == {}

    def test_should_pass_kedro_config_env_to_nodes(self):
        # given
        self.create_generator(params={"param1": 0.3, "param2": 42})
        os.environ["KEDRO_CONFIG_MY_KEY"] = "42"
        os.environ["SOME_VALUE"] = "100"

        try:
            # when
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                self.generator_under_test.generate_pipeline(
                    "pipeline", "unittest-image", "Always"
                )()

            # then
            env_values = {
                e.name: e.value
                for e in dsl_pipeline.ops["pipeline"].container.env
            }
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
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )()

        # then
        env_values = {
            e.name: e.value for e in dsl_pipeline.ops["pipeline"].container.env
        }
        assert "KUBEFLOW_RUN_ID" in env_values
        assert env_values["KUBEFLOW_RUN_ID"] == "{{workflow.uid}}"

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
                "pipelines": {
                    "pipeline": Pipeline(
                        [
                            node(identity, "A", "B", name="node1"),
                            node(identity, "B", "C", name="node2"),
                        ]
                    )
                },
            },
        )
        self.generator_under_test = OnePodPipelineGenerator(
            config=PluginConfig(
                {"host": "http://unittest", "run_config": config}
            ),
            project_name="my-awesome-project",
            context=context,
        )
