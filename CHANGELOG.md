# Changelog

## [Unreleased]

## [0.4.3] - 2021-09-27

-   Kedro environment used by `kedro kubeflow` invocation is passed to the steps
-   A flag to skip steps output artifacts registration in Kubeflow Metadata

## [0.4.2] - 2021-08-19

-   Improved Vertex scheduling: removal of stale schedules

## [0.4.1] - 2021-08-18

-   Passing Kedro environment and pipeline name in Vertex nodes
-   Setting artifact type based on catalog layer in Vertex pipeline
-   Added `pipeline` param to `schedule` in Vertex

## [0.4.0] - 2021-08-11

-   Support for kedro-mlflow>=0.7
-   Support of Google Vertex AI Pipelines (EXPERIMENTAL)
-   Ability to access KFP API behind Dex+authservice authentication
-   Support for multi-user KFP setup (experiment namespace passed via `run-once` or `schedule`)
-   New config param: `max_cache_staleness` to avoid caching KFP steps if required

## [0.3.1] - 2021-05-25

### Fixed

-   Prevent KeyError when catalog had entries without filepath. 

## [0.3.0] - 2021-01-29

### Added

-   Support to inject Kedro pipeline parameters for the run
-   Ability to specify resources allocation for the nodes
-   Possibility to configure the pipeline description in the config file
-   The registered output artifacts are not exposed in the Pipelines UI
-   Ability to set ttl of the workflow (how long the pods and volumes stay in the system after finish)
-   Removing the inter-steps data volume during workflow removal (with option to disable the removal in the config using flag `keep`)

## [0.2.0] - 2021-01-18

### Added

-   Ability to change the effective user id for steps if the ownership of the volume needs it
-   Hook that enables TemplatedConfigLoader that supports dynamic config files. Any env variable 
    named `KEDRO_CONFIG_<NAME>` can be referenced in configuration files as `${name}`
-   Added IAP authentication support for MLflow
-   Increased test coverage for the CLI
-   Creating github actions template with `kedro kubeflow init --with-github-actions`

### Fixed

-   Fixed broken `kubeflow init` command (#29)

## [0.1.10] - 2021-01-11

### Added

-   Added sample support for [TemplatedConfigLoader](https://kedro.readthedocs.io/en/latest/kedro.config.TemplatedConfigLoader.html)
-   MLFlow support updated to not use nested runs.
-   Simple configuration validation added.
-   Volume init step is now optional (useful, if there is raw data in the image)

## [0.1.9] - 2021-01-08

### Added

-   Support for MLFlow - if the package is installed then additional step is added with parent run init. Then all separate nodes runs register under this run.
-   Support for inter-steps volume: setup (one volume per pipeline run), initial load (the content of `data/` directory from the image and mount to all the steps for artifacts passing.
-   `kubeflow init` command added to generate sample configuration file.

## [0.1.8] - 2021-01-05

### Added

-   _Initial release_ of kedro-kubeflow plugin
-   Ability to run an anonymous pipeline once as within a specified experiment `kedro kubeflow run-once`.
-   Ability to upload pipeline `kedro kubeflow upload-pipeline`.
-   Method to schedule runs for most recent version of given pipeline `kedro kubeflow schedule` 
-   Shortcut to open UI for pipelines using `kedro kubeflow ui` 

[Unreleased]: https://github.com/getindata/kedro-kubeflow/compare/0.4.3...HEAD

[0.4.3]: https://github.com/getindata/kedro-kubeflow/compare/0.4.2...0.4.3

[0.4.2]: https://github.com/getindata/kedro-kubeflow/compare/0.4.1...0.4.2

[0.4.1]: https://github.com/getindata/kedro-kubeflow/compare/0.4.0...0.4.1

[0.4.0]: https://github.com/getindata/kedro-kubeflow/compare/0.3.1...0.4.0

[0.3.1]: https://github.com/getindata/kedro-kubeflow/compare/0.3.0...0.3.1

[0.3.0]: https://github.com/getindata/kedro-kubeflow/compare/0.2.0...0.3.0

[0.2.0]: https://github.com/getindata/kedro-kubeflow/compare/0.1.10...0.2.0

[0.1.10]: https://github.com/getindata/kedro-kubeflow/compare/0.1.9...0.1.10

[0.1.9]: https://github.com/getindata/kedro-kubeflow/compare/0.1.8...0.1.9

[0.1.8]: https://github.com/getindata/kedro-kubeflow/compare/ea219ae5f70e726b7afc9d0864da4b6649e4deaf...0.1.8
