"""Test generator"""

import os
import unittest
from inspect import signature
from unittest.mock import MagicMock, patch

import kfp
from kedro.pipeline import Pipeline, node

from kedro_kubeflow.config import PluginConfig
from kedro_kubeflow.generators.pod_per_node_pipeline_generator import (
    PodPerNodePipelineGenerator,
)
from tests.common import MinimalConfigMixin


def identity(input1: str):
    return input1  # pragma: no cover


class TestGenerator(unittest.TestCase, MinimalConfigMixin):
    def test_support_modification_of_pull_policy(self):
        # given
        self.create_generator()

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Never"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Never"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert (
                dsl_pipeline.ops["node1"].container.image == "unittest-image"
            )
            assert (
                dsl_pipeline.ops["node1"].container.image_pull_policy
                == "Never"
            )

    def test_should_support_inter_steps_volume_with_defaults(self):
        # given
        self.create_generator(config={"volume": {}})

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "IfNotPresent"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "IfNotPresent"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert len(dsl_pipeline.ops) == 5
            assert "on-exit" in dsl_pipeline.ops
            assert (
                dsl_pipeline.ops["on-exit"]
                .container.command[-1]
                .endswith(
                    "kedro kubeflow delete-pipeline-volume "
                    "{{workflow.name}}-pipeline-data-volume"
                )
            )
            volume_spec = dsl_pipeline.ops[
                "data-volume-create"
            ].k8s_resource.spec
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

    def test_should_generate_on_exit_pipeline_run(self):
        # given
        self.create_generator(config={"on_exit_pipeline": "notify_via_slack"})

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "IfNotPresent"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "IfNotPresent"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert "on-exit" in dsl_pipeline.ops
            assert (
                dsl_pipeline.ops["on-exit"]
                .container.command[-1]
                .endswith(
                    "kedro run --config config.yaml "
                    "--env unittests --pipeline notify_via_slack"
                )
            )

    def test_should_generate_volume_removal_and_on_exit_pipeline_run(self):
        # given
        self.create_generator(
            config={"volume": {}, "on_exit_pipeline": "notify_via_slack"}
        )

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "IfNotPresent"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "IfNotPresent"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert "on-exit" in dsl_pipeline.ops
            assert (
                dsl_pipeline.ops["on-exit"]
                .container.command[-1]
                .endswith(
                    "kedro kubeflow delete-pipeline-volume "
                    "{{workflow.name}}-pipeline-data-volume;"
                    "kedro run --config config.yaml "
                    "--env unittests --pipeline notify_via_slack"
                )
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
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert len(dsl_pipeline.ops) == 5
            assert "on-exit" in dsl_pipeline.ops
            volume_spec = dsl_pipeline.ops[
                "data-volume-create"
            ].k8s_resource.spec
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
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
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
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
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
                "--env",
                "unittests",
                "mlflow-start",
                "{{workflow.uid}}",
            ]
            assert "MLFLOW_RUN_ID" not in {e.name for e in init_step.env}
            for node_name in ["node1", "node2"]:
                env = {
                    e.name: e.value
                    for e in dsl_pipeline.ops[node_name].container.env
                }
                assert "MLFLOW_RUN_ID" in env
                assert (
                    env["MLFLOW_RUN_ID"]
                    == "{{pipelineparam:op=mlflow-start-run;name=mlflow_run_id}}"
                )

    def test_should_skip_volume_init_if_requested(self):
        # given
        self.create_generator(config={"volume": {"skip_init": True}})

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert len(dsl_pipeline.ops) == 4
            assert "data-volume-create" in dsl_pipeline.ops
            assert "on-exit" in dsl_pipeline.ops
            assert "data-volume-init" not in dsl_pipeline.ops
            for node_name in ["node1", "node2"]:
                volumes = dsl_pipeline.ops[node_name].container.volume_mounts
                assert len(volumes) == 1
                assert volumes[0].name == "data-volume-create"

    def test_should_support_params_and_inject_them_to_the_nodes(self):
        # given
        self.create_generator(params={"param1": 0.3, "param2": 42})

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     default_params = signature(pipeline).parameters
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
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
                    "_",
                    "param1",
                    "{{pipelineparam:op=;name=param1}}",
                    "param2",
                    "{{pipelineparam:op=;name=param2}}",
                ]

    def test_should_fallbackto_default_resources_spec_if_not_requested(self):
        # given
        self.create_generator(config={})

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
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
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
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

    def test_can_add_extra_volumes(self):
        self.create_generator(
            config={
                "extra_volumes": {
                    "node1": [
                        {
                            "mount_path": "/my/volume",
                            "volume": {
                                "name": "my_volume",
                                "empty_dir": {
                                    "cls": "V1EmptyDirVolumeSource",
                                    "params": {"medium": "Memory"},
                                },
                            },
                        }
                    ]
                }
            }
        )

        pipeline = self.generator_under_test.generate_pipeline(
            "pipeline", "unittest-image", "Always"
        )
        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            pipeline()

        volume_mounts = dsl_pipeline.ops["node1"].container.volume_mounts
        assert len(volume_mounts) == 1

    def test_should_not_add_retry_policy_if_not_requested(self):
        # given
        self.create_generator(config={})

        # when
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     self.generator_under_test.generate_pipeline(
        #         "pipeline", "unittest-image", "Always"
        #     )()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            for node_name in ["node1", "node2"]:
                op = dsl_pipeline.ops[node_name]
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
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     self.generator_under_test.generate_pipeline(
        #         "pipeline", "unittest-image", "Always"
        #     )()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            op1 = dsl_pipeline.ops["node1"]
            assert op1.num_retries == 100
            assert op1.retry_policy == "Always"
            assert op1.backoff_factor == 1
            assert op1.backoff_duration == "5m"
            assert op1.backoff_max_duration is None
            op2 = dsl_pipeline.ops["node2"]
            assert op2.num_retries == 4
            assert op2.retry_policy == "Always"
            assert op2.backoff_factor == 2
            assert op2.backoff_duration == "60s"
            assert op2.backoff_max_duration is None

    def test_should_add_max_cache_staleness(self):
        self.create_generator(config={"max_cache_staleness": "P0D"})

        with kfp.dsl.Pipeline(None) as dsl_pipeline:
            self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )()

        op1 = dsl_pipeline.ops["node1"]
        assert (
            op1.execution_options.caching_strategy.max_cache_staleness == "P0D"
        )

    def test_should_set_description(self):
        # given
        self.create_generator(config={"description": "DESC"})

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Never"
        # )
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Never"
            )
            # with kfp.dsl.Pipeline(None) as dsl_pipeline:
            #     pipeline()

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
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            outputs1 = dsl_pipeline.ops["node1"].file_outputs
            assert len(outputs1) == 1
            assert "B" in outputs1
            assert outputs1["B"] == "/home/kedro/data/02_intermediate/b.csv"
            outputs2 = dsl_pipeline.ops["node2"].file_outputs
            assert len(outputs2) == 0  # output "C" is missing in the catalog

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
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            outputs1 = dsl_pipeline.ops["node1"].file_outputs
            assert len(outputs1) == 0

    def test_should_skip_volume_removal_if_requested(self):
        # given
        self.create_generator(config={"volume": {"keep": True}})

        # when
        # pipeline = self.generator_under_test.generate_pipeline(
        #     "pipeline", "unittest-image", "Always"
        # )
        # with kfp.dsl.Pipeline(None) as dsl_pipeline:
        #     pipeline()
        with patch(
            "kedro.framework.project.pipelines",
            new=self.pipelines_under_test,
        ):
            pipeline = self.generator_under_test.generate_pipeline(
                "pipeline", "unittest-image", "Always"
            )
            with kfp.dsl.Pipeline(None) as dsl_pipeline:
                pipeline()

            # then
            assert "schedule-volume-termination" not in dsl_pipeline.ops

    def test_should_pass_kedro_config_env_to_nodes(self):
        # given
        self.create_generator()
        os.environ["KEDRO_CONFIG_MY_KEY"] = "42"
        os.environ["SOME_VALUE"] = "100"

        try:
            # when
            # with kfp.dsl.Pipeline(None) as dsl_pipeline:
            #     self.generator_under_test.generate_pipeline(
            #         "pipeline", "unittest-image", "Always"
            #     )()
            with patch(
                "kedro.framework.project.pipelines",
                new=self.pipelines_under_test,
            ):
                pipeline = self.generator_under_test.generate_pipeline(
                    "pipeline", "unittest-image", "Always"
                )
                with kfp.dsl.Pipeline(None) as dsl_pipeline:
                    pipeline()

                # then
                for node_name in ["node1", "node2"]:
                    env_values = {
                        e.name: e.value
                        for e in dsl_pipeline.ops[node_name].container.env
                    }
                    assert "KEDRO_CONFIG_MY_KEY" in env_values
                    assert env_values["KEDRO_CONFIG_MY_KEY"] == "42"
                    assert "SOME_VALUE" not in env_values
        finally:
            del os.environ["KEDRO_CONFIG_MY_KEY"]
            del os.environ["SOME_VALUE"]

    def create_generator(self, config=None, params=None, catalog=None):
        project_name = "my-awesome-project"
        config_loader = MagicMock()
        config_loader.get.return_value = catalog or {}
        context = type(
            "obj",
            (object,),
            {
                "env": "unittests",
                "params": params or {},
                "config_loader": config_loader,
                # "pipelines": {
                #     "pipeline": Pipeline(
                #         [
                #             node(identity, "A", "B", name="node1"),
                #             node(identity, "B", "C", name="node2"),
                #         ]
                #     )
                # },
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
        self.generator_under_test = PodPerNodePipelineGenerator(
            PluginConfig(
                **self.minimal_config(
                    {"host": "http://unittest", "run_config": config or {}}
                )
            ),
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
