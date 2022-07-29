# Contributing guidelines 

Everyone is welcome to contribute to the code of this plugin, however we have some automation and guidelines you should get familiar with first.

### PR Guidelines
1. Fork branch from `develop`.
1. Ensure to provide unit tests for new functionality.
1. Install dev requirements: `pip install -r requirements-dev.txt` and setup a hook: `pre-commit install`
1. For commits we follow [angular commit messages guideline](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit).
1. Update documentation accordingly.
1. Update [changelog](https://github.com/getindata/kedro-kubeflow/blob/develop/CHANGELOG.md) according to ["Keep a changelog"](https://keepachangelog.com/en/1.0.0/) guidelines.
1. Squash changes with a single commit as much as possible and ensure verbose PR name.
1. Open a PR against `develop`

*We reserve the right to take over and modify or abandon PRs that do not match the workflow or are abandoned.* 

(updating-the-documentation)=
### Updating the documentation

For documentation updates we have `docs/Makefile` that runs `Sphinx` to update the [readthedocs](https://kedro-kubeflow.readthedocs.io).

There is automation using github actions that checks the spelling of the docs. [Links](updating-the-documentation), `inline blocks escaped with back ticks` \`...\` and 
```
triple backtick blocks
```
are omitted. 
 
 In order to add new spelling exceptions, append them to the `docs/spellcheck_exceptions.txt` file.

For documentation syntax, we use Markdown with [myst](https://myst-parser.readthedocs.io/en/latest/syntax/syntax.html) parser.

##### Templating

We have `jinja` available to be used in documentation. The variables are defined in `docs/conf.py` in `myst_substitutions`. By default the following are available:

 - `release` - the package version with which it was built
 - `req_<package>` - the specification of version package requirement range in `setup.py`
 - `req_lower_<package>` - the specification of version package requirement lower bound in `setup.py`
 - `req_upper_<package>` - the specification of version package requirement upper bound in `setup.py`
 - `req_build_<package>` - the specification of version package with which it was built

### Pre-commit and github hooks

For linting and keeping code clean we use pre-commit package to join with github hooks. Use it by doing:

```console
$ pip install pre-commit
$ pre-commit install
```

You can test github actions locally with [act](https://github.com/nektos/act).

### Release workflow

1. Create the release candidate:
    - Go to the [Prepare release](https://github.com/getindata/kedro-kubeflow/actions?query=workflow%3A%22Prepare+release%22) action.
    - Click "Run workflow"
    - Enter the part of the version to bump (one of `<major>.<minor>.<patch>`). Minor (x.**x**.x) is a default. 
2. If the workflow has run successfully:
    - Go to the newly opened PR named `Release candidate <version>`
    - Check that changelog and version have been properly updated. If not pull the branch and apply manual changes if necessary.
    - Merge the PR to master
3. Checkout the [Publish](https://github.com/getindata/kedro-kubeflow/actions?query=workflow%3APublish) workflow to see if:
    - The package has been uploaded on PyPI successfully
    - The changes have been merged back to develop
