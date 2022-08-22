(local-testing)=
# Local testing

## Unit tests

The plugin has unit tests that can be run with `tox`, for example for python 3.8:
```console
$ pip install tox-pip-version
$ tox -v -e py38
```

List available python environments to test with using `tox -l`.

You can also run them manually by executing `python -m unittest` in the root folder. They are also executed with github action on pull requests to test the stability of new changes. See `.github/workflows/python-package.yml`.

## E2E tests

There is also a set up with Kubeflow running on team-maintained Google Cloud Platform. It tests the execution on said Kubeflow platform with `spaceflight` kedro starter. They are also automated with github action. See `.github/workflows/e2e-tests.yml`. 
