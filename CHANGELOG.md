# Changelog

## [Unreleased]

### Added

- Ability to change the effective user id for steps if the ownership of the volume needs it
- Hook that enables TemplatedConfigLoader that supports dynamic config files. Any env variable 
named `KEDRO_CONFIG_<NAME>` can be referenced in configuration files as `${name}`
- Added IAP authentication support for MLflow
- Increased test coverage for the CLI
- Creating github actions template with `kedro kubeflow init --with-github-actions`

### Fixed

- Fixed broken `kubeflow init` command (#29)

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

[Unreleased]: https://github.com/getindata/kedro-kubeflow/compare/0.1.10...HEAD

[0.1.10]: https://github.com/getindata/kedro-kubeflow/compare/0.1.9...0.1.10

[0.1.9]: https://github.com/getindata/kedro-kubeflow/compare/0.1.8...0.1.9

[0.1.8]: https://github.com/getindata/kedro-kubeflow/compare/ea219ae5f70e726b7afc9d0864da4b6649e4deaf...0.1.8
