"""Test generator"""

import unittest
from unittest.mock import MagicMock

import kfp
from kedro.pipeline import Pipeline, node
from kfp.dsl import PipelineParam

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.vertex_ai.generator import PipelineGenerator


def identity(input1: str):
    return input1  # pragma: no cover


class TestGenerator(unittest.TestCase):
    def create_pipeline(self):
        return Pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
            ]
        )

    def test_support_modification_of_pull_policy(self):
        # given
        self.create_generator()

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Never", "MLFLOW_TRACKING_TOKEN"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert dsl_pipeline.ops["node1"].container.image == "unittest-image"
        assert dsl_pipeline.ops["node1"].container.image_pull_policy == "Never"

    def test_should_skip_volume_init_if_requested(self):
        # given
        self.create_generator(config={"volume": {"skip_init": True}})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always", "MLFLOW_TRACKING_TOKEN"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        print(len(dsl_pipeline.ops))
        assert len(dsl_pipeline.ops) == 2
        assert "data-volume-init" not in dsl_pipeline.ops
        for node_name in ["node1", "node2"]:
            assert not dsl_pipeline.ops[node_name].container.volume_mounts

    def test_should_not_add_resources_spec_if_not_requested(self):
        # given
        self.create_generator(config={})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always", "MLFLOW_TRACKING_TOKEN"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        for node_name in ["node1", "node2"]:
            spec = dsl_pipeline.ops[node_name].container
            assert spec.resources is None

    def test_should_add_resources_spec(self):
        # given
        self.create_generator(
            config={
                "resources": {
                    "__default__": {"cpu": "100m"},
                    "node1": {"cpu": "400m", "memory": "64Gi"},
                }
            }
        )

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always", "MLFLOW_TRACKING_TOKEN"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        node1_spec = dsl_pipeline.ops["node1"].container.resources
        node2_spec = dsl_pipeline.ops["node2"].container.resources
        assert node1_spec.limits == {"cpu": "400m", "memory": "64Gi"}
        assert node1_spec.requests == {"cpu": "400m", "memory": "64Gi"}
        assert node2_spec.limits == {"cpu": "100m"}
        assert node2_spec.requests == {"cpu": "100m"}

    def test_should_set_description(self):
        # given
        self.create_generator(config={"description": "DESC"})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Never", "MLFLOW_TRACKING_TOKEN"
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
                },
                "C": {
                    "type": "pickle.PickleDataSet",
                    "filepath": "data/06_models/model.pkl",
                    "layer": "models",
                },
            }
        )

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always", "MLFLOW_TRACKING_TOKEN"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        outputs1 = dsl_pipeline.ops["node1"].outputs
        assert len(outputs1) == 2
        assert "B" in outputs1
        assert outputs1["B"] == PipelineParam(
            name="B", op_name="node1", param_type="Dataset"
        )
        outputs2 = dsl_pipeline.ops["node2"].outputs
        assert outputs2["C"].param_type == "Model"

    def test_should_skip_volume_removal_if_requested(self):
        # given
        self.create_generator(config={"volume": {"keep": True}})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always", "MLFLOW_TRACKING_TOKEN"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert "schedule-volume-termination" not in dsl_pipeline.ops

    def test_should_add_env_and_pipeline_in_the_invocations(self):
        # given
        self.create_generator()
        self.mock_mlflow(True)

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Never", "MLFLOW_TRACKING_TOKEN"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert (
            "kedro kubeflow -e unittests mlflow-start"
            in dsl_pipeline.ops["mlflow-start-run"].container.args[0]
        )
        assert (
            'kedro run -e unittests --pipeline pipeline  --node "node1"'
            in dsl_pipeline.ops["node1"].container.args[0]
        )

    def mock_mlflow(self, enabled=False):
        def fakeimport(name, *args, **kw):
            if not enabled and name == "mlflow":
                raise ImportError
            return self.realimport(name, *args, **kw)

        __builtins__["__import__"] = fakeimport

    def setUp(self):
        self.realimport = __builtins__["__import__"]
        self.mock_mlflow(False)

    def tearDown(self):
        __builtins__["__import__"] = self.realimport

    def create_generator(self, config={}, params={}, catalog={}):
        project_name = "my-awesome-project"
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
        config_with_defaults = {
            "root": "sample-bucket/sample-suffix",
            "experiment_name": "test-experiment",
            "run_name": "test-run",
        }
        config_with_defaults.update(config)
        self.generator_under_test = PipelineGenerator(
            PluginConfig(
                {"host": "http://unittest", "run_config": config_with_defaults}
            ),
            project_name,
            context,
        )
