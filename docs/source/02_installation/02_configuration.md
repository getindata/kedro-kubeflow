# Configuration

Plugin maintains the configuration in the `conf/base/kubeflow.yaml` file. Sample configuration can be generated using `kedro kubeflow init`:

```yaml
# Base url of the Kubeflow Pipelines, should include the schema (http/https)
host: https://kubeflow.example.com/pipelines

# Configuration used to run the pipeline
run_config:

  # Name of the image to run as the pipeline steps
  image: kubeflow-plugin-demo

  # Pull pilicy to be used for the steps. Use Always if you push the images
  # on the same tag, or Never if you use only local images
  image_pull_policy: IfNotPresent

  # Name of the kubeflow experiment to be created
  experiment_name: Kubeflow Plugin Demo [${branch_name|local}]

  # Name of the run for run-once, templated with the run-once parameters
  run_name: Kubeflow Plugin Demo Run ${pipeline_name} ${branch_name|local} ${commit_id|local}

  # Name of the scheduled run, templated with the schedule parameters
  scheduled_run_name: Kubeflow Plugin Demo Recurring Run ${pipeline_name}

  # Optional pipeline description
  description: Very Important Pipeline

  # Flag indicating if the run-once should wait for the pipeline to finish
  wait_for_completion: False

  # How long to keep underlying Argo workflow (together with pods and data
  # volume after pipeline finishes) [in seconds]. Default: 1 week
  ttl: 604800

  # What Kedro pipeline should be run as the last step regardless of the
  # pipeline status. Used to send notifications or raise the alerts
  # on_exit_pipeline: notify_via_slack

  # This sets the caching option for pipeline using
  # execution_options.caching_strategy.max_cache_staleness
  # See https://en.wikipedia.org/wiki/ISO_8601 in section 'Duration'
  #max_cache_staleness: P0D

  # Set to false to disable kfp artifacts exposal
  # This setting can be useful if you don't want to store
  # intermediate results in the MLMD
  #store_kedro_outputs_as_kfp_artifacts: True

  # Strategy used to generate Kubeflow pipeline nodes from Kedro nodes
  # Available strategies:
  #  * none (default) - nodes in Kedro pipeline are mapped to separate nodes
  #                     in Kubeflow pipelines. This strategy allows to inspect
  #                     a whole processing graph in Kubeflow UI and override
  #                     resources for each node (because they are run in separate pods)
  #                     Although, performance may not be optimal due to potential
  #                     sharing of intermediate datasets through disk.
  #  * full - nodes in Kedro pipeline are mapped to one node in Kubeflow pipelines.
  #           This strategy mitigate potential performance issues with `none` strategy
  #           but at the cost of degraded user experience within Kubeflow UI: a graph
  #           is collapsed to one node.
  #node_merge_strategy: none

  # Optional volume specification
  volume:

    # Storage class - use null (or no value) to use the default storage
    # class deployed on the Kubernetes cluster
    storageclass: # default

    # The size of the volume that is created. Applicable for some storage
    # classes
    size: 1Gi

    # Access mode of the volume used to exchange data. ReadWriteMany is
    # preferred, but it is not supported on some environements (like GKE)
    # Default value: ReadWriteOnce
    #access_modes: [ReadWriteMany]

    # Flag indicating if the data-volume-init step (copying raw data to the
    # fresh volume) should be skipped
    skip_init: False

    # Allows to specify user executing pipelines within containers
    # Default: root user (to avoid issues with volumes in GKE)
    owner: 0

    # Flak indicating if volume for inter-node data exchange should be
    # kept after the pipeline is deleted
    keep: False
    
  # Optional section allowing adjustment of the tolerations for the nodes
  tolerations:
    __default__:
    - key: "dedicated"
      operator: "Equal"
      value: "ml-ops"
      effect: "NoSchedule"
    node_a:
    - key: "dedicated"
      operator: "Equal"
      value: "gpu_workload"
      effect: "NoSchedule"

  # Optional section to allow mounting additional volumes (such as EmptyDir)
  # to specific nodes
  extra_volumes:
    tensorflow_step:
    - mount_path: /dev/shm
      volume:
        name: shared_memory
        empty_dir:
          cls: V1EmptyDirVolumeSource
          params:
            medium: Memory
            
  # Optional section allowing adjustment of the resources
  # reservations and limits for the nodes
  resources:

    # For nodes that require more RAM you can increase the "memory"
    data_import_step:
      memory: 2Gi

    # Training nodes can utilize more than one CPU if the algoritm
    # supports it
    model_training:
      cpu: 8
      memory: 1Gi

    # GPU-capable nodes can request 1 GPU slot
    tensorflow_step:
      nvidia.com/gpu: 1

    # Default settings for the nodes
    __default__:
      cpu: 200m
      memory: 64Mi

  # Optional section to provide retry policy for the steps
  # and default policy for steps with no policy specified
  retry_policy:
    # 90 retries every 5 minutes
    wait_for_partition_availability:
      num_retries: 90
      backoff_duration: 5m
      backoff_factor: 1

    # 4 retries after: 1 minute, 2 minutes, 4 minutes, 8 minutes
    __default__:
      num_retries: 4
      backoff_duration: 60s
      backoff_factor: 2
```

## Dynamic configuration support

`kedro-kubeflow` contains hook that enables [TemplatedConfigLoader](https://kedro.readthedocs.io/en/stable/kedro.config.TemplatedConfigLoader.html).
It allows passing environment variables to configuration files. It reads all environment variables following `KEDRO_CONFIG_<NAME>` pattern, which you 
can later inject in configuration file using `${name}` syntax. 

There are two special variables `KEDRO_CONFIG_COMMIT_ID`, `KEDRO_CONFIG_BRANCH_NAME` with support specifying default when variable is not set, 
e.g. `${commit_id|dirty}`   

## Extra volumes
You can mount additional volumes (such as `emptyDir`) to specific nodes by using `extra_volumes` config node.
The syntax of the configuration allows to define k8s SDK compatible class hierarchy similar to the way you would define it in the KFP DSL, e.g:
```python
# KFP DSL
volume = dsl.PipelineVolume(volume=k8s.client.V1Volume(
    name="shared_memory",
    empty_dir=k8s.client.V1EmptyDirVolumeSource(medium='Memory')))

training_op.add_pvolumes({'/dev/shm': volume})
```
will translate to the following Kedro-Kubeflow config:
```yaml
extra_volumes:
  training_op:
  - mount_path: /dev/shm
    volume:
      name: shared_memory
      empty_dir:
        cls: V1EmptyDirVolumeSource
        params:
          medium: Memory
```

In general, the `volume` key accepts a dictionary with the keys being the named parameters for the [V1Volume](https://github.com/kubernetes-client/python/blob/be9a47e57358e3701ad079c98e223d3437ba1f46/kubernetes/docs/V1Volume.md) and values being one of:
* dictionary with `cls` and `params` keys (to define nested objects) - see `kedro_kubeflow.config.ObjectKwargs`
* list of values / list of dictionaries (`kedro_kubeflow.config.ObjectKwargs`) as described above
* values (`str`, `int` etc.)
