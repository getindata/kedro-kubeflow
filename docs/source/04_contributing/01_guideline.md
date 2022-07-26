# Contributing guidelines 

Everyone is welcome to contribute to the code of this plugin, however we have some automation and guidelines you should get familiar with first.

There are few things that you should know about our workflow:
- All changes should be made as pull requests to develop branch.
- On release versions from develop branch are tagged and pulled to the master branch.
- For commits we follow [angular commit messages guideline](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit).

## Updating the documentation

For documentation updates we have `docs/Makefile` that runs `Sphinx` to update the `readthedocs`.

There is automation using github actions that checks the spelling of the docs. [Links](), `blocks escaped with back ticks` \`...\` are omitted. In order to add new spelling exceptions, append them to the `docs/spellcheck_exceptions.txt` file.

## Github hooks

For linting and keeping code clean we use pre-commit package to join with github hooks. Use it by doing:

```bash
pip install pre-commit
pre-commit install
```

## Releasing new versions

TBD