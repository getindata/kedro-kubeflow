# Introduction

## What is Kubeflow Pipelines?

[Kubeflow Pipelines](https://www.kubeflow.org/docs/pipelines/) is a platform for
building and deploying portable, scalable machine learning (ML) workflows based 
on Docker containers. It works by defining pipelines with nodes (Kubernetes objects, 
like pod or volume) and edges (dependencies between the nodes, like passing output 
data as input). The pipelines are stored in the versioned database, allowing user 
to run the pipeline once or schedule the recurring run.

## Why integrate a Kedro project with Pipelines?

Kubeflow Pipelines' main attitude is the portability. Once you define a pipeline,
it can be started on any Kubernetes cluster. The code to execute is stored inside 
docker images that cover not only the source itself, but also all the libraries and 
entire execution environment. Portability is also one of the key Kedro qualities, as 
the pipelines must be versionable and packageable. Kedro, with 
[Kedro-Docker](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) plugin does a fantastic 
job to achieve this and Kubeflow looks like a nice add-on to run the pipelines 
on powerful remote Kubernetes clusters.
