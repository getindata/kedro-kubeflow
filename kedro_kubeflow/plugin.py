from pathlib import Path

import click
from kedro import __version__ as kedro_version
from kedro.config import MissingConfigException
from semver import VersionInfo

from .kfpclient import KubeflowClient
from .utils import strip_margin

KEDRO_VERSION = VersionInfo.parse(kedro_version)

if KEDRO_VERSION.match(">=0.17.0"):
    from kedro.framework.session import KedroSession

    def get_context(metadata, env):
        return KedroSession.create(
            metadata.package_name, env=env
        ).load_context()

    def get_project_name(metadata, env):
        return metadata.project_name


else:  # <0.17
    from kedro.framework.context import load_context

    def get_context(metadata, env):
        return load_context(Path.cwd(), env=env)

    def get_project_name(metadata, env):
        return get_context(metadata, env).project_name


CONFIG_FILE_PATTERN = "kubeflow*"


@click.group("Kubeflow")
def commands():
    """Kedro plugin adding support for Kubeflow Pipelines"""
    pass


@commands.group(
    name="kubeflow", context_settings=dict(help_option_names=["-h", "--help"])
)
@click.option(
    "-e", "--env", "env", type=str, default="base", help="Environment to use."
)
@click.pass_obj
@click.pass_context
def kubeflow_group(ctx, metadata, env):
    """Interact with Kubeflow Pipelines"""
    ctx.ensure_object(dict)
    ctx.obj["kedro_ctx"] = get_context(metadata, env)
    ctx.obj["project_name"] = get_project_name(metadata, env)


def setup_context(ctx):
    ctx.obj["config"] = ctx.obj["kedro_ctx"].config_loader.get(
        CONFIG_FILE_PATTERN
    )
    if "host" not in ctx.obj["config"].keys():
        raise MissingConfigException("No 'host' defined in kubeflow.yml")

    ctx.obj["kfp_client"] = KubeflowClient(
        ctx.obj["config"], ctx.obj["project_name"], ctx.obj["kedro_ctx"]
    )


@kubeflow_group.command()
@click.pass_context
def list_pipelines(ctx):
    """List deployed pipeline definitions"""
    setup_context(ctx)
    click.echo(ctx.obj["kfp_client"].list_pipelines())


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
    "-x",
    "--experiment-name",
    "experiment_name",
    type=str,
    help="Name of experiment associated with this run.",
)
@click.option(
    "-r", "--run-name", "run_name", type=str, help="Name for this run."
)
@click.option("-w", "--wait", "wait", type=bool, help="Wait for completion.")
@click.option(
    "--image-pull-policy",
    type=str,
    default="IfNotPresent",
    help="Image pull policy.",
)
@click.pass_context
def run_once(
    ctx,
    image: str,
    pipeline: str,
    experiment_name: str,
    run_name: str,
    wait: bool,
    image_pull_policy: str,
):
    """Deploy pipeline as a single run within given experiment.
    Config can be specified in kubeflow.yml as well."""
    setup_context(ctx)
    conf = ctx.obj["config"]
    run_conf = conf.get("run_config", {})
    image = image if image else run_conf["image"]
    experiment_name = (
        experiment_name if experiment_name else run_conf["experiment_name"]
    )
    run_name = run_name if run_name else run_conf["run_name"]
    wait = wait if wait is not None else bool(run_conf["wait_for_completion"])
    image_pull_policy = run_conf.get("image_pull_policy", image_pull_policy)

    ctx.obj["kfp_client"].run_once(
        pipeline, image, experiment_name, run_name, wait, image_pull_policy
    )


@kubeflow_group.command()
@click.pass_context
def ui(ctx) -> None:
    """Open Kubeflow Pipelines UI in new browser tab"""
    setup_context(ctx)
    import webbrowser

    host = ctx.obj["config"]["host"]
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
@click.option(
    "--image-pull-policy",
    type=str,
    default="IfNotPresent",
    help="Image pull policy.",
)
@click.pass_context
def compile(ctx, image, pipeline, output, image_pull_policy) -> None:
    """Translates Kedro pipeline into YAML file with Kubeflow Pipeline definition"""
    setup_context(ctx)
    conf = ctx.obj["config"]
    run_conf = conf.get("run_config", {})
    image = image if image else run_conf["image"]
    ctx.obj["kfp_client"].compile(pipeline, image, output, image_pull_policy)


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
@click.option(
    "--image-pull-policy",
    type=str,
    default="IfNotPresent",
    help="Image pull policy.",
)
@click.pass_context
def upload_pipeline(ctx, image, pipeline, image_pull_policy) -> None:
    """Uploads pipeline to Kubeflow server"""
    setup_context(ctx)
    conf = ctx.obj["config"]
    run_conf = conf.get("run_config", {})
    image = image if image else run_conf["image"]
    ctx.obj["kfp_client"].upload(pipeline, image, image_pull_policy)


@kubeflow_group.command()
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
@click.pass_context
def schedule(ctx, experiment_name: str, cron_expression: str):
    """Schedules recurring execution of latest version of the pipeline"""
    setup_context(ctx)
    conf = ctx.obj["config"]
    run_conf = conf.get("run_config", {})
    experiment_name = (
        experiment_name if experiment_name else run_conf["experiment_name"]
    )

    ctx.obj["kfp_client"].schedule(experiment_name, cron_expression)


@kubeflow_group.command()
@click.argument("kfp_url", type=str)
@click.option(
    "-x",
    "--experiment-name",
    "experiment_name",
    type=str,
    help="Name of experiment associated with this run.",
    default="default",
)
@click.pass_context
def init(ctx, kfp_url: str, experiment_name: str):
    """Initializes configuration for the plugin"""
    image = ctx.obj["kedro_ctx"].project_path.name  # default from kedro-docker
    config = f"""
    |host: {kfp_url}
    |
    |run_config:
    |  image: {image}
    |  experiment_name: {ctx.obj['project_name']}
    |  run_name: {ctx.obj['project_name']}
    |  wait_for_completion: False
    |  volume:
    |    storageclass: # default
    |    #size: 1Gi
    |    #access_modes: [ReadWriteOnce]
    """
    config_path = Path.cwd().joinpath("conf/base/kubeflow.yaml")
    with open(config_path, "w") as f:
        f.write(strip_margin(config))

    click.echo(f"Configuration generated in {config_path}")


@kubeflow_group.command()
@click.argument("kubeflow_run_id", type=str)
@click.pass_context
def mlflow_start(ctx, kubeflow_run_id: str):
    from kedro_mlflow.framework.context import get_mlflow_config
    import mlflow

    mlflow_conf = get_mlflow_config(ctx.obj["kedro_ctx"])
    mlflow_conf.setup(ctx.obj["kedro_ctx"])
    run = mlflow.start_run(
        experiment_id=mlflow_conf.experiment.experiment_id, nested=False
    )
    mlflow.set_tag("kubeflow_run_id", kubeflow_run_id)
    with open("/tmp/mlflow_run_id", "w") as f:
        f.write(run.info.run_id)
    click.echo(f"Started run: {run.info.run_id}")
