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

`init` command takes one argument (that is the kubeflow pipelines root url) and generates sample configuration file in `conf/base/kubeflow.yaml`. The YAML file content is described in the [Configuration section](../02_installation/02_configuration.md).

### `ui`

`ui` command opens a web browser pointing to the currently configured Kubeflow Pipelines UI. It's super useful for debugging, especially while working on multiple Kubeflow installations.

### `list-pipelines`

`list-pipelines` uses Kubeflow Pipelines to retrieve all registered pipelines

### `compile`

`compile` transforms Kedro pipeline into Argo workflow (Argo is the engine that powers Kubeflow Pipelines). The resulting `yaml` file can be uploaded to Kubeflow Pipelines via web UI.

### `upload-pipeline`

`upload-pipeline` compiles the pipeline and uploads it as a new pipeline version. The pipeline name is equal to the project name for simplicity.

### `schedule`

`schedule` creates recurring run of the previously uploaded pipeline. The cron expression (required parameter) is used to define at what schedule the pipeline should run.

### `run-once`

`run-once` is all-in-one command to compile the pipeline and run it in the Kubeflow environment.

### `mlflow-start`

`mlflow-start` is internal command to be used as a pipeline starting point with enabled Mlflow support. It should not be called by the users.
