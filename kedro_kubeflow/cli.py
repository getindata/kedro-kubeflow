import logging
import os
import webbrowser
from pathlib import Path

import click

from .auth import AuthHandler
from .config import PluginConfig
from .context_helper import ContextHelper

LOG = logging.getLogger(__name__)


@click.group("Kubeflow")
def commands():
    """Kedro plugin adding support for Kubeflow Pipelines"""
    pass


@commands.group(
    name="kubeflow", context_settings=dict(help_option_names=["-h", "--help"])
)
@click.option(
    "-e", "--env", "env", type=str, default="local", help="Environment to use."
)
@click.pass_obj
@click.pass_context
def kubeflow_group(ctx, metadata, env):
    """Interact with Kubeflow Pipelines"""
    ctx.ensure_object(dict)
    ctx.obj["context_helper"] = ContextHelper.init(
        metadata,
        env,
    )


@kubeflow_group.command()
@click.pass_context
def list_pipelines(ctx):
    """List deployed pipeline definitions"""
    context_helper = ctx.obj["context_helper"]
    click.echo(context_helper.kfp_client.list_pipelines())


@kubeflow_group.command()
@click.option(
    "-i",
    "--image",
    type=str,
    help="Docker image to use for pipeline execution.",
)
@click.option(
    "-p",
    "--pipeline",
    "pipeline",
    type=str,
    help="Name of pipeline to run",
    default="__default__",
)
@click.option(
    "-en",
    "--experiment-namespace",
    "experiment_namespace",
    type=str,
    default=None,
    help="Namespace where pipeline experiment run should be deployed to. Not needed "
    "if provided experiment name already exists.",
)
@click.pass_context
def run_once(ctx, image: str, pipeline: str, experiment_namespace: str):
    """Deploy pipeline as a single run within given experiment.
    Config can be specified in kubeflow.yml as well."""
    context_helper = ctx.obj["context_helper"]
    config = context_helper.config.run_config

    context_helper.kfp_client.run_once(
        pipeline=pipeline,
        image=image if image else config.image,
        experiment_name=config.experiment_name,
        experiment_namespace=experiment_namespace,
        run_name=config.run_name,
        wait=config.wait_for_completion,
        image_pull_policy=config.image_pull_policy,
    )


@kubeflow_group.command()
@click.pass_context
def ui(ctx) -> None:
    """Open Kubeflow Pipelines UI in new browser tab"""
    host = ctx.obj["context_helper"].config.host
    webbrowser.open_new_tab(host)


@kubeflow_group.command()
@click.option(
    "-i",
    "--image",
    type=str,
    help="Docker image to use for pipeline execution.",
)
@click.option(
    "-p",
    "--pipeline",
    "pipeline",
    type=str,
    help="Name of pipeline to run",
    default="__default__",
)
@click.option(
    "-o",
    "--output",
    type=str,
    default="pipeline.yml",
    help="Pipeline YAML definition file.",
)
@click.pass_context
def compile(ctx, image, pipeline, output) -> None:
    """Translates Kedro pipeline into YAML file with Kubeflow Pipeline definition"""
    context_helper = ctx.obj["context_helper"]
    config = context_helper.config.run_config

    context_helper.kfp_client.compile(
        pipeline=pipeline,
        image_pull_policy=config.image_pull_policy,
        image=image if image else config.image,
        output=output,
    )


@kubeflow_group.command()
@click.option(
    "-i",
    "--image",
    type=str,
    help="Docker image to use for pipeline execution.",
)
@click.option(
    "-p",
    "--pipeline",
    "pipeline",
    type=str,
    help="Name of pipeline to upload",
    default="__default__",
)
@click.pass_context
def upload_pipeline(ctx, image, pipeline) -> None:
    """Uploads pipeline to Kubeflow server"""
    context_helper = ctx.obj["context_helper"]
    config = context_helper.config.run_config

    context_helper.kfp_client.upload(
        pipeline=pipeline,
        image=image if image else config.image,
        image_pull_policy=config.image_pull_policy,
    )


@kubeflow_group.command()
@click.option(
    "-p",
    "--pipeline",
    "pipeline",
    type=str,
    help="Name of pipeline to run",
    default="__default__",
)
@click.option(
    "-c",
    "--cron-expression",
    type=str,
    help="Cron expression for recurring run",
    required=True,
)
@click.option(
    "-x",
    "--experiment-name",
    "experiment_name",
    type=str,
    help="Name of experiment associated with this run.",
)
@click.option(
    "-en",
    "--experiment-namespace",
    "experiment_namespace",
    type=str,
    default=None,
    help="Namespace where pipeline experiment run should be deployed to. Not needed "
    "if provided experiment name already exists.",
)
@click.pass_context
def schedule(
    ctx,
    pipeline: str,
    experiment_namespace: str,
    experiment_name: str,
    cron_expression: str,
):
    """Schedules recurring execution of latest version of the pipeline"""
    context_helper = ctx.obj["context_helper"]
    config = context_helper.config.run_config
    experiment = experiment_name if experiment_name else config.experiment_name

    context_helper.kfp_client.schedule(
        pipeline, experiment, experiment_namespace, cron_expression
    )


@kubeflow_group.command()
@click.argument("kfp_url", type=str)
@click.option("--with-github-actions", is_flag=True, default=False)
@click.pass_context
def init(ctx, kfp_url: str, with_github_actions: bool):
    """Initializes configuration for the plugin"""
    context_helper = ctx.obj["context_helper"]
    project_name = context_helper.context.project_path.name
    if with_github_actions:
        image = f"gcr.io/${{google_project_id}}/{project_name}:${{commit_id}}"
        run_name = f"{project_name}:${{commit_id}}"
    else:
        image = project_name
        run_name = project_name

    sample_config = PluginConfig.sample_config(
        url=kfp_url, image=image, project=project_name, run_name=run_name
    )
    config_path = Path.cwd().joinpath("conf/base/kubeflow.yaml")
    with open(config_path, "w") as f:
        f.write(sample_config)

    click.echo(f"Configuration generated in {config_path}")

    if with_github_actions:
        PluginConfig.initialize_github_actions(
            project_name,
            where=Path.cwd(),
            templates_dir=Path(__file__).parent / "templates",
        )


@kubeflow_group.command(hidden=True)
@click.argument("kubeflow_run_id", type=str)
@click.option(
    "--output",
    type=str,
    default="/tmp/mlflow_run_id",
)
@click.pass_context
def mlflow_start(ctx, kubeflow_run_id: str, output: str):
    import mlflow
    from kedro_mlflow.framework.context import get_mlflow_config

    token = AuthHandler().obtain_id_token()
    if token:
        os.environ["MLFLOW_TRACKING_TOKEN"] = token
        LOG.info("Configuring MLFLOW_TRACKING_TOKEN")

    try:
        kedro_context = ctx.obj["context_helper"].context
        mlflow_conf = get_mlflow_config(kedro_context)
        mlflow_conf.setup(kedro_context)
    except AttributeError:
        kedro_session = ctx.obj["context_helper"].session
        with kedro_session:
            mlflow_conf = get_mlflow_config(kedro_session)
            mlflow_conf.setup()

    run = mlflow.start_run(
        experiment_id=mlflow_conf.experiment.experiment_id, nested=False
    )
    mlflow.set_tag("kubeflow_run_id", kubeflow_run_id)
    with open(output, "w") as f:
        f.write(run.info.run_id)
    click.echo(f"Started run: {run.info.run_id}")
