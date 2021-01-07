
## PR Guidelines
1. Fork branch from `develop`.
1. Ensure to provide unit tests for new functionality.
1. Install pre-commit: `pip install pre-commit` and setup a hook: `pre-commit install`
1. Update documentation accordingly.
1. Update [changelog](CHANGELOG.md) according to ["Keep a changelog"](https://keepachangelog.com/en/1.0.0/) guidelines.
1. Squash changes with a single commit as much as possible and ensure verbose PR name.
1. Open a PR against `develop`

*We reserve the right to take over and modify or abandon PRs that do not match the workflow or are abandoned.* 

## Release workflow

1. Create the release candidate:
    - Go to the [Prepare release](https://github.com/getindata/kedro-kubeflow/actions?query=workflow%3A%22Prepare+release%22) action.
    - Click "Run workflow"
    - Enter the part of the version to bump (one of `<major>.<minor>.<patch>`). Minor (x.**x**.x) is a default. 
2. If the workflow has run sucessfully:
    - Go to the newly openened PR named `Release candidate `<version>`
    - Check that changelog and version have been properly updated. If not pull the branch and apply manual changes if necessary.
    - Merge the PR to master
3. Checkout the [Publish](https://github.com/getindata/kedro-kubeflow/actions?query=workflow%3APublish) workflow to see if:
    - The package has been uploaded on PyPI successfully
    - The changes have been merged back to develop
