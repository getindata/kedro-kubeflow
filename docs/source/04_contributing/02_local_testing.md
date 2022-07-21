# Local testing

## Unit tests

The plugin has unit tests that can be run with `tox`:
```console
pip install tox-pip-version
tox -v -e py38
```

You can also run them manually by executing `python -m unittest` in the root folder. They are also executed with github action on pull requests to test the stability of new changes. See `.github/workflows/python-package.yml`.

## E2E tests

There is also a set up with Kubeflow running on team-maintained Google Cloud Platform. It tests the execution on said Kubeflow platform with `spaceflight` kedro starter. They are also automated with github action. See `.github/workflows/e2e-tests.yml`. 

## Local cluster testing

If you have enough RAM, there is also an option to test locally with running [Kubernetes in docker (kind)](https://getindata.com/blog/kubeflow-pipelines-running-5-minutes/). After going through that guideline you should have Kubeflow up and running available at `http://localhost:9000`.

There are few differences from (quickstart)[#Quickstart]. For `kedro init` use the `http://localhost:9000` as an endpoint.

The kind has its own docker registry that you need to upload the image to. However, since it does not have any connection to other registry we want to prevent it from trying to pull any image. In order to do that, we need to tag the built docker image with specific version.

Locate your image name (it should be the same as kedro project name) with:
```
docker images
```

Then tag your image with the following command (the version is arbitrary and can be any other version):
```
docker tag <image>:latest <image>:1.0
```

Then you need to upload the image from local registry to the kind registry. Here `kfp` is the cluster name, the same as used in guide in the link above. Default cluster name is `kind`.
```
kind load docker-image <image>:1.0 --name kfp
```

Lastly, in order to run a job or a schedule, you need to specify the image with image version, i.e:
```
kedro kubeflow run-once -i docker.io/library/<image>:1.0 
```

With that you should be able to test the plugin end to end with local sandbox Kubeflow cluster.