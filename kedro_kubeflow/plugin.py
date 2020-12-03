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
    print(client.list_pipelines())


@kubeflow_group.command()
@click.option("-i", "--image", type=str, help="Docker image to use for pipeline execution.")
@click.option("-p", "--pipeline", "pipeline", type=str, help="Name of pipeline to run", default="__default__")
@click.option("-x", "--experiment-name", "experiment_name", type=str, help="Name of experiment associated with this run.")
@click.option("-r", "--run-name", "run_name", type=str, help="Name for this run.")
@click.option("-e", "--env", "env", type=str, default="base", help="Environment to use.")
@click.option("-w", "--wait", "wait", type=bool, help="Wait for completion.")
def run_once(image: str, pipeline: str, experiment_name: str, run_name: str, env: str, wait: bool):
    """Deploy pipeline as a single run within given experiment. Config can be specified in kubeflow.yml as well."""
    conf = config()
    run_conf = conf.get("run_config", {})
    image = image if image else run_conf['image']
    experiment_name = experiment_name if experiment_name else run_conf['experiment_name']
    run_name = run_name if run_name else run_conf['run_name']
    wait = wait if wait is not None else bool(run_conf["wait_for_completion"])

    client = KubeflowClient(config())
    client.run_once(pipeline, image, experiment_name, run_name, env, wait)


@kubeflow_group.command()
def ui() -> None:
    import webbrowser
    host = config()['host']
    webbrowser.open_new_tab(host)


def config():
    ctx = get_project_context()
    return ctx.config_loader.get(CONFIG_FILE_PATTERN)
