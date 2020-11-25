import click
from kedro.cli import get_project_context
from kedro.config import MissingConfigException
from kfp import Client


@click.group("K")
def commands():
    """Kedro plugin adding support for Kubeflow Pipelines"""
    pass


@commands.group(name="kubeflow", context_settings=dict(help_option_names=["-h", "--help"]))
def kubeflow_group():
    """Interact with Kubeflow Pipelines"""
    if 'host' not in _get_config().keys():
        raise MissingConfigException("No kubeflow pipelines host defined")


@kubeflow_group.command()
def list_pipelines():
    client = Client(host=_get_config()['host'])
    print(client.list_pipelines())


@commands.command()
@click.option("-i", "--image", type=str, required=True)
@click.option("-e", "--env", "env", type=str, default="base")
def run_experiment(image: str, host: str, pipeline: str, branch: str, run: str, env: str):
    pass


def _get_config():
    ctx = get_project_context()
    return ctx.config_loader.get("kubeflow*")
