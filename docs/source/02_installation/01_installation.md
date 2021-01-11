# Installation guide

## Kedro setup

First, you need to install base Kedro backage in ``<17.0`` version

> Kedro 17.0 is supported by kedro-kubeflow, but [not by kedro-mlflow](https://github.com/Galileo-Galilei/kedro-mlflow/issues/144) yet, so the latest version from 0.16.5 is recommended.

```console
$ pip install 'kedro<0.17'
```

## Plugin installation

### Install from PyPI

You can install ``kedro-kubeflow`` plugin from ``PyPi`` with `pip`:

```console
pip install --upgrade kedro-kubeflow
```

### Install from sources

You may want to install the develop branch which has unreleased features:

```console
pip install git+https://github.com/getindata/kedro-kubeflow.git@develop
```

## Available commands

You can check available commands by going into project directory and runnning:

```console
$ kedro kubeflow
Usage: kedro kubeflow [OPTIONS] COMMAND [ARGS]...

  Interact with Kubeflow Pipelines

Options:
  -e, --env TEXT  Environment to use.
  -h, --help      Show this message and exit.

Commands:
  compile          Translates Kedro pipeline into YAML file with Kubeflow...
  init             Initializes configuration for the plugin
  list-pipelines   List deployed pipeline definitions
  mlflow-start
  run-once         Deploy pipeline as a single run within given experiment.
  schedule         Schedules recurring execution of latest version of the...
  ui               Open Kubeflow Pipelines UI in new browser tab
  upload-pipeline  Uploads pipeline to Kubeflow server
```

### `init`

`init` command takes one argument (that is the kubeflow pipelines root url) and generates sample configuration file in `conf/base/kubeflow.yaml`. The YAML file content is described in the [Configuration section](02_installation/02_configuration.html)
