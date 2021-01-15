# Kedro Kubeflow Plugin

[![Python Version](https://img.shields.io/badge/python-3.7%20%7C%203.8-blue.svg)](https://github.com/getindata/kedro-kubeflow)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) 
[![SemVer](https://img.shields.io/badge/semver-2.0.0-green)](https://semver.org/)
[![PyPI version](https://badge.fury.io/py/kedro-kubeflow.svg)](https://pypi.org/project/kedro-kubeflow/)
[![Downloads](https://pepy.tech/badge/kedro-kubeflow)](https://pepy.tech/project/kedro-kubeflow) 

[![Maintainability](https://api.codeclimate.com/v1/badges/fff07cbd2e5012a045a3/maintainability)](https://codeclimate.com/github/getindata/kedro-kubeflow/maintainability) 
[![Test Coverage](https://api.codeclimate.com/v1/badges/fff07cbd2e5012a045a3/test_coverage)](https://codeclimate.com/github/getindata/kedro-kubeflow/test_coverage)
[![Documentation Status](https://readthedocs.org/projects/kedro-kubeflow/badge/?version=latest)](https://kedro-kubeflow.readthedocs.io/en/latest/?badge=latest)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fgetindata%2Fkedro-kubeflow.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fgetindata%2Fkedro-kubeflow?ref=badge_shield)

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
to adjust it to the requirements of the environment:

```
# Base url of the Kubeflow Pipelines, should include the schema (http/https)
host: kubeflow-pipelines.a-domain.com

# Configuration used to run the pipeline
run_config:

  # Name of the image to run as the pipeline steps
  image: new-kedro-project

  # Pull pilicy to be used for the steps. Use Always if you push the images
  # on the same tag, or Never if you use only local images
  image_pull_policy: IfNotPresent

  # Name of the kubeflow experiment to be created
  experiment_name: New Kedro Project

  # Name of the run for run-once
  run_name: New Project Run

  # Flag indicating if the run-once should wait for the pipeline to finish
  wait_for_completion: False

  # Optional volume specification
  volume:

    # Storage class - use null (or no value) to use the default storage
    # class deployed on the Kubernetes cluster
    storageclass: # default

    # The size of the volume that is created. Applicable for some storage
    # classes
    size: 1Gi

    # Access mode of the volume used to exchange data. ReadWriteOnce doesn't
    # allos multiple nodes to bind the volume at the same time, but may be
    # the only option on some environments. Default value: ReadWriteMany
    #access_modes: [ReadWriteOnce]

    # Flag indicating if the data-volume-init step (copying raw data to the
    # fresh volume) should be skipped
    skip_init: False

    ## Allows to specify user executing pipelines within containers
    owner: 0
```
