"""Test generator"""

import unittest
from inspect import signature

import kfp
from kedro.pipeline import Pipeline, node

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.generator import PipelineGenerator


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
            "pipeline", "unittest-image", "Never"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert dsl_pipeline.ops["node1"].container.image == "unittest-image"
        assert dsl_pipeline.ops["node1"].container.image_pull_policy == "Never"

    def test_should_support_inter_steps_volume_with_defaults(self):
        # given
        self.create_generator(config={"volume": {}})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "IfNotPresent"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert len(dsl_pipeline.ops) == 4
        volume_spec = dsl_pipeline.ops["data-volume-create"].k8s_resource.spec
        assert volume_spec.resources.requests["storage"] == "1Gi"
        assert volume_spec.access_modes == ["ReadWriteOnce"]
        assert volume_spec.storage_class_name is None
        volume_init_spec = dsl_pipeline.ops["data-volume-init"].container
        assert volume_init_spec.image == "unittest-image"
        assert volume_init_spec.image_pull_policy == "IfNotPresent"
        assert volume_init_spec.security_context.run_as_user == 0
        assert volume_init_spec.args[0].startswith("cp --verbose -r")
        for node_name in ["data-volume-init", "node1", "node2"]:
            volumes = dsl_pipeline.ops[node_name].container.volume_mounts
            assert len(volumes) == 1
            assert volumes[0].name == "data-volume-create"
            assert (
                dsl_pipeline.ops[
                    node_name
                ].container.security_context.run_as_user
                == 0
            )

    def test_should_support_inter_steps_volume_with_given_spec(self):
        # given
        self.create_generator(
            config={
                "volume": {
                    "storageclass": "nfs",
                    "size": "1Mi",
                    "access_modes": ["ReadWriteOnce"],
                }
            }
        )

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert len(dsl_pipeline.ops) == 4
        volume_spec = dsl_pipeline.ops["data-volume-create"].k8s_resource.spec
        assert volume_spec.resources.requests["storage"] == "1Mi"
        assert volume_spec.access_modes == ["ReadWriteOnce"]
        assert volume_spec.storage_class_name == "nfs"

    def test_should_change_effective_user_if_to_volume_owner(self):
        # given
        self.create_generator(
            config={
                "volume": {
                    "storageclass": "nfs",
                    "size": "1Mi",
                    "access_modes": ["ReadWriteOnce"],
                    "owner": 47,
                }
            }
        )

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        volume_init_spec = dsl_pipeline.ops["data-volume-init"].container
        assert volume_init_spec.security_context.run_as_user == 47
        for node_name in ["data-volume-init", "node1", "node2"]:
            assert (
                dsl_pipeline.ops[
                    node_name
                ].container.security_context.run_as_user
                == 47
            )

    def test_should_add_mlflow_init_step_if_enabled(self):
        # given
        self.create_generator()
        self.mock_mlflow(True)

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert len(dsl_pipeline.ops) == 3
        init_step = dsl_pipeline.ops["mlflow-start-run"].container
        assert init_step.image == "unittest-image"
        assert init_step.args == [
            "kubeflow",
            "mlflow-start",
            "{{workflow.uid}}",
        ]
        for node_name in ["node1", "node2"]:
            env = dsl_pipeline.ops[node_name].container.env
            assert env[1].name == "MLFLOW_RUN_ID"
            assert (
                env[1].value
                == "{{pipelineparam:op=mlflow-start-run;name=mlflow_run_id}}"
            )

    def test_should_skip_volume_init_if_requested(self):
        # given
        self.create_generator(config={"volume": {"skip_init": True}})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        # then
        assert len(dsl_pipeline.ops) == 3
        assert "data-volume-init" not in dsl_pipeline.ops
        for node_name in ["node1", "node2"]:
            volumes = dsl_pipeline.ops[node_name].container.volume_mounts
            assert len(volumes) == 1
            assert volumes[0].name == "data-volume-create"

    def test_should_support_params_and_inject_them_to_the_nodes(self):
        # given
        self.create_generator(params={"param1": 0.3, "param2": 42})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            default_params = signature(pipeline).parameters
            pipeline()

        # then
        assert len(default_params) == 2
        assert default_params["param1"].default == 0.3
        assert default_params["param2"].default == 42
        for node_name in ["node1", "node2"]:
            args = dsl_pipeline.ops[node_name].container.args
            assert args == [
                "run",
                "--params",
                "param1:{{pipelineparam:op=;name=param1}},"
                "param2:{{pipelineparam:op=;name=param2}}",
                "--node",
                node_name,
            ]

    def test_should_not_add_resources_spec_if_not_requested(self):
        # given
        self.create_generator(config={})

        # when
        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always"
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
            "pipeline", "unittest-image", "Always"
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

    def create_generator(self, config={}, params={}):
        project_name = "my-awesome-project"
        context = type(
            "obj",
            (object,),
            {
                "params": params,
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
        self.generator_under_test = PipelineGenerator(
            PluginConfig({"host": "http://unittest", "run_config": config}),
            project_name,
            context,
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
