# Kedro Kubeflow Plugin

[![Python Version](https://img.shields.io/badge/python-3.7%20%7C%203.8-blue.svg)](https://github.com/getindata/kedro-kubeflow)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) 
[![SemVer](https://img.shields.io/badge/semver-2.0.0-green)](https://semver.org/)
[![PyPI version](https://badge.fury.io/py/kedro-kubeflow.svg)](https://pypi.org/project/kedro-kubeflow/)
[![Downloads](https://pepy.tech/badge/kedro-kubeflow)](https://pepy.tech/project/kedro-kubeflow) 

[![Maintainability](https://api.codeclimate.com/v1/badges/fff07cbd2e5012a045a3/maintainability)](https://codeclimate.com/github/getindata/kedro-kubeflow/maintainability) 
[![Test Coverage](https://api.codeclimate.com/v1/badges/fff07cbd2e5012a045a3/test_coverage)](https://codeclimate.com/github/getindata/kedro-kubeflow/test_coverage)
## About

The main purpose of this plugin is to enable running kedro pipeline on Kubeflow Pipelines. It supports translation from 
Kedro pipeline DSL to [kfp](https://www.kubeflow.org/docs/pipelines/sdk/sdk-overview/) (pipelines SDK) and deployment to 
a running kubeflow cluster with some convenient commands.

The plugin can be used together with `kedro-docker` to simplify preparation of docker image for pipeline execution.   

## Usage guide

```
Usage: kedro kubeflow [OPTIONS] COMMAND [ARGS]...
 
   Interact with Kubeflow Pipelines
 
 Options:
   -h, --help  Show this message and exit.
 
 Commands:
   compile          Translates Kedro pipeline into YAML file with Kubeflow pipeline definition
   init             Initializes configuration for the plugin
   list-pipelines   List deployed pipeline definitions
   run-once         Deploy pipeline as a single run within given experiment.
   schedule         Schedules recurring execution of latest version of the pipeline
   ui               Open Kubeflow Pipelines UI in new browser tab
   upload-pipeline  Uploads pipeline to Kubeflow server
```

## Configuration file

`kedro init` generates configuration file for the plugin, but users may want
to adjust it to the requirements of the environment:

```
host: http://10.43.77.224

run_config:
  image: new-kedro-project
  experiment_name: New Kedro Project
  run_name: New Kedro Project
  wait_for_completion: False
  volume:
    storageclass: # default
    size: 1Gi
    access_modes: [ReadWriteOnce]
    skip_init: False
```
