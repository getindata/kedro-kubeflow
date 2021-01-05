# Kedro Kubeflow Plugin

[![Python Version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue.svg)](https://github.com/getindata/kedro-kubeflow)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) 
[![SemVer](https://img.shields.io/badge/semver-2.0.0-green)](https://semver.org/)

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
   list-pipelines   List deployed pipeline definitions
   run-once         Deploy pipeline as a single run within given experiment.
   schedule         Schedules recurring execution of latest version of the pipeline
   ui               Open Kubeflow Pipelines UI in new browser tab
   upload-pipeline  Uploads pipeline to Kubeflow server
```
