# Changelog

## [Unreleased]
- Added templating capabilities to docs generator and used them in the docs for kedro versioning
- Added pre-commit hook for pyspelling check
- Changed sphinx markdown engine to myst
- Added CI for spellchecking the documentation with configuration for myst
- Updated documentation quickstart to workaround known issues and make it work on local kind cluster
- Updated documentation - added contributing guidelines and setup tips
- Added --wait-for-completion and --timeout for `kedro kubeflow run-once` command
- Added e2e tests github action for pull requests with kubeflow setup in gcp
- Added support for extra volumes per node 
- Refactored configuration classes to Pydantic

## [0.6.4] - 2022-06-01

-   Added support for specifying tolerations

## [0.6.3] - 2022-05-10

-   KFP SDK version bumped to 1.8.11 in order to fix misbehaving TTL issue
-   Dropped support for VertexAI, please use [kedro-vertexi](https://kedro-kubeflow.readthedocs.io/en/latest/index.html) instead
-   Add Kedro environment name to the pipeline name during upload

## [0.6.2] - 2022-03-10

-   Added support for defining retry policy for the Kubeflow Pipelines nodes

## [0.6.1] - 2022-03-07

-   Fixed support for parameters of type `datetime.date`

## [0.6.0] - 2022-02-18

-   Kedro pipeline name is now added into Kubeflow pipeline name during upload
-   Project hook that injected environmental variables values into all the configuration files is dropped, with backward compatibility to support these in `kubeflow.yaml`
-   Added missing on-exit-handler for `node_merge_strategy: full`
-   Handle `KEDRO_ENV` enviroment variable

## [0.5.1] - 2022-01-28

-   Possibility to run custom Kedro pipeline as on-exit-handler

## [0.5.0] - 2022-01-27

-   Kedro paramters of complex types (lists and dicts) are now supported
-   `run_once` and `schedule` accepts Kedro parameters override
-   Names of the one-off runs and scheduled runs are templated with parameters

## [0.4.8] - 2022-01-10

## [0.4.7] - 2022-01-05

-   Add `kubeflow_run_id` tag to MLFlow run when `full` node merge strategy is used

## [0.4.6] - 2021-12-23

-   Passing all `KEDRO_CONFIG_` environment variables to the pipeline nodes

## [0.4.5] - 2021-12-22

-   Add `node_merge_strategy` alongside with `full` option to run a whole pipeline in one pod

## [0.4.4] - 2021-09-29

-   Custom networking setup for Vertex AI pipelines run

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

[Unreleased]: https://github.com/getindata/kedro-kubeflow/compare/0.6.4...HEAD

[0.6.4]: https://github.com/getindata/kedro-kubeflow/compare/0.6.3...0.6.4

[0.6.3]: https://github.com/getindata/kedro-kubeflow/compare/0.6.2...0.6.3

[0.6.2]: https://github.com/getindata/kedro-kubeflow/compare/0.6.1...0.6.2

[0.6.1]: https://github.com/getindata/kedro-kubeflow/compare/0.6.0...0.6.1

[0.6.0]: https://github.com/getindata/kedro-kubeflow/compare/0.5.1...0.6.0

[0.5.1]: https://github.com/getindata/kedro-kubeflow/compare/0.5.0...0.5.1

[0.5.0]: https://github.com/getindata/kedro-kubeflow/compare/0.4.8...0.5.0

[0.4.8]: https://github.com/getindata/kedro-kubeflow/compare/0.4.7...0.4.8

[0.4.7]: https://github.com/getindata/kedro-kubeflow/compare/0.4.6...0.4.7

[0.4.6]: https://github.com/getindata/kedro-kubeflow/compare/0.4.5...0.4.6

[0.4.5]: https://github.com/getindata/kedro-kubeflow/compare/0.4.4...0.4.5

[0.4.4]: https://github.com/getindata/kedro-kubeflow/compare/0.4.3...0.4.4

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
