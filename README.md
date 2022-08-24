# Kedro Kubeflow Plugin

[![Python Version](https://img.shields.io/pypi/pyversions/kedro-kubeflow)](https://github.com/getindata/kedro-kubeflow)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![SemVer](https://img.shields.io/badge/semver-2.0.0-green)](https://semver.org/)
[![PyPI version](https://badge.fury.io/py/kedro-kubeflow.svg)](https://pypi.org/project/kedro-kubeflow/)
[![Downloads](https://pepy.tech/badge/kedro-kubeflow)](https://pepy.tech/project/kedro-kubeflow)

[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=getindata_kedro-kubeflow&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=getindata_kedro-kubeflow)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=getindata_kedro-kubeflow&metric=coverage)](https://sonarcloud.io/summary/new_code?id=getindata_kedro-kubeflow)
[![Documentation Status](https://readthedocs.org/projects/kedro-kubeflow/badge/?version=latest)](https://kedro-kubeflow.readthedocs.io/en/latest/?badge=latest)

## About

The main purpose of this plugin is to enable running kedro pipeline on Kubeflow Pipelines. It supports translation from 
Kedro pipeline DSL to [kfp](https://www.kubeflow.org/docs/pipelines/sdk/sdk-overview/) (pipelines SDK) and deployment to 
a running kubeflow cluster with some convenient commands.

The plugin can be used together with `kedro-docker` to simplify preparation of docker image for pipeline execution.   

## Documentation

For detailed documentation refer to https://kedro-kubeflow.readthedocs.io/

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
to adjust it to match the run environment requirements: https://kedro-kubeflow.readthedocs.io/en/latest/source/02_installation/02_configuration.html

