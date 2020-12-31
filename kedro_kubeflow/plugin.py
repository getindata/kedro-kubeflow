import click
from kedro.framework.cli import get_project_context
from kedro.config import MissingConfigException
from .kfpclient import KubeflowClient


CONFIG_FILE_PATTERN = "kubeflow*"


@click.group("Kubeflow")
def commands():
    """Kedro plugin adding support for Kubeflow Pipelines"""
    pass


@commands.group(name="kubeflow", context_settings=dict(help_option_names=["-h", "--help"]))
def kubeflow_group():
    """Interact with Kubeflow Pipelines"""
    if 'host' not in config().keys():
        raise MissingConfigException("No 'host' defined in kubeflow.yml")


@kubeflow_group.command()
def list_pipelines():
    """List deployed pipeline definitions"""
    client = KubeflowClient(config())
    click.echo(client.list_pipelines())


@kubeflow_group.command()
@click.option("-i", "--image", type=str, help="Docker image to use for pipeline execution.")
@click.option("-p", "--pipeline", "pipeline", type=str, help="Name of pipeline to run", default="__default__")
@click.option("-x", "--experiment-name", "experiment_name", type=str, help="Name of experiment associated with this run.")
@click.option("-r", "--run-name", "run_name", type=str, help="Name for this run.")
@click.option("-e", "--env", "env", type=str, default="base", help="Environment to use.")
@click.option("-w", "--wait", "wait", type=bool, help="Wait for completion.")
@click.option("--image-pull-policy", type=str, default="IfNotPresent", help="Image pull policy.")
def run_once(image: str, pipeline: str, experiment_name: str, run_name: str, env: str, wait: bool, image_pull_policy: str):
    """Deploy pipeline as a single run within given experiment. Config can be specified in kubeflow.yml as well."""
    conf = config()
    run_conf = conf.get("run_config", {})
    image = image if image else run_conf['image']
    experiment_name = experiment_name if experiment_name else run_conf['experiment_name']
    run_name = run_name if run_name else run_conf['run_name']
    wait = wait if wait is not None else bool(run_conf["wait_for_completion"])
    image_pull_policy = run_conf.get('image_pull_policy', image_pull_policy)

    client = KubeflowClient(config())
    client.run_once(pipeline, image, experiment_name, run_name, env, wait, image_pull_policy)


@kubeflow_group.command()
def ui() -> None:
    """Open Kubeflow Pipelines UI in new browser tab"""
    import webbrowser
    host = config()['host']
    webbrowser.open_new_tab(host)


@kubeflow_group.command()
@click.option("-i", "--image", type=str, help="Docker image to use for pipeline execution.")
@click.option("-p", "--pipeline", "pipeline", type=str, help="Name of pipeline to run", default="__default__")
@click.option("-e", "--env", "env", type=str, default="base", help="Environment to use.")
@click.option("-o", "--output", type=str, default="pipeline.yml", help="Pipeline YAML definition file.")
@click.option("--image-pull-policy", type=str, default="IfNotPresent", help="Image pull policy.")
def compile(image, pipeline, env, output, image_pull_policy) -> None:
    conf = config()
    run_conf = conf.get("run_config", {})
    image = image if image else run_conf['image']
    KubeflowClient(conf).compile(pipeline, image, env, output, image_pull_policy)


@kubeflow_group.command()
@click.option("-i", "--image", type=str, help="Docker image to use for pipeline execution.")
@click.option("-p", "--pipeline", "pipeline", type=str, help="Name of pipeline to upload", default="__default__")
@click.option("-e", "--env", "env", type=str, default="base", help="Environment to use.")
@click.option("-o", "--output", type=str, default="pipeline.yml", help="Pipeline YAML definition file.")
@click.option("--image-pull-policy", type=str, default="IfNotPresent", help="Image pull policy.")
def upload_pipeline(image, pipeline, env, output, image_pull_policy) -> None:
    """Uploads pipeline to Kubeflow"""
    conf = config()
    run_conf = conf.get("run_config", {})
    image = image if image else run_conf['image']
    KubeflowClient(conf).upload(pipeline, image, env, output, image_pull_policy)


@kubeflow_group.command()
@click.option("-c", "--cron-expression", type=str, help="Cron expression for recurring run", required=True)
@click.option("-x", "--experiment-name", "experiment_name", type=str, help="Name of experiment associated with this run.")
@click.option("-e", "--env", "env", type=str, default="base", help="Environment to use.")
def schedule(experiment_name: str, cron_expression: str, env: str):
    """Schedules recurring execution of latest version of the pipeline"""
    conf = config()
    run_conf = conf.get("run_config", {})
    experiment_name = experiment_name if experiment_name else run_conf['experiment_name']

    KubeflowClient(config()).schedule(env, experiment_name, cron_expression)


def config():
    ctx = get_project_context()
    return ctx.config_loader.get(CONFIG_FILE_PATTERN)
