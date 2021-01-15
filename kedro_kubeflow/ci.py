# flake8: noqa
GITHUB = {
    "on-push": """
name: On push: build image and run on Kubeflow

on:
  push:
    branches:
      - '!master'

env:
  PROJECT_ID: ${{{{ secrets.GKE_PROJECT }}}}
  IAP_CLIENT_ID: ${{{{ secrets.IAP_CLIENT_ID }}}}
  PROJECT_NAME: {project_name}

jobs:
  build-and-run:
    name: Build image and run on Kubeflow
    runs-on: ubuntu-20.04

    steps:
    - name: Checkout
      uses: actions/checkout@v2

    - uses: google-github-actions/setup-gcloud@v0.2.0
      with:
        service_account_key: ${{{{ secrets.GKE_SA_KEY }}}}
        project_id: ${{{{ secrets.GKE_PROJECT }}}}
        export_default_credentials: true

    - name: Build
      run: |-
        pip3 install kedro-docker
        gcloud --quiet auth configure-docker
        docker pull "gcr.io/$PROJECT_ID/$PROJECT_NAME:latest" || true        
        /home/runner/.local/bin/kedro docker build --image "gcr.io/$PROJECT_ID/$PROJECT_NAME:$GITHUB_SHA" --docker-args "--cache-from gcr.io/$PROJECT_ID/$PROJECT_NAME:latest" --gid 0

    - name: Publish
      run: |-
        docker push "gcr.io/$PROJECT_ID/$PROJECT_NAME:$GITHUB_SHA"
        docker tag "gcr.io/$PROJECT_ID/$PROJECT_NAME:$GITHUB_SHA" "gcr.io/$PROJECT_ID/$PROJECT_NAME:latest"
        docker push "gcr.io/$PROJECT_ID/$PROJECT_NAME:latest"

    - name: Deploy pipeline
      run: |-
        pip3 install kedro-kubeflow
        /home/runner/.local/bin/kedro install
        sed -i -e"s/__GITHUB_SHA__/$GITHUB_SHA/" conf/base/kubeflow.yaml
        sed -i -e"s/__PROJECT_ID__/$PROJECT_ID/" conf/base/kubeflow.yaml
        /home/runner/.local/bin/kedro kubeflow run-once
""",
    "on-merge-to-master": """
name: On merge to master: build, register and schedule

on:
  push:
    branches:
      - master

env:
  PROJECT_ID: ${{{{ secrets.GKE_PROJECT }}}}
  IAP_CLIENT_ID: ${{{{ secrets.IAP_CLIENT_ID }}}}
  PROJECT_NAME: {project_name}

jobs:
  build-and-run:
    name: Build image and run on Kubeflow
    runs-on: ubuntu-20.04

    steps:
    - name: Checkout
      uses: actions/checkout@v2

    - uses: google-github-actions/setup-gcloud@v0.2.0
      with:
        service_account_key: ${{{{ secrets.GKE_SA_KEY }}}}
        project_id: ${{{{ secrets.GKE_PROJECT }}}}
        export_default_credentials: true

    - name: Build
      run: |-
        pip3 install kedro-docker
        gcloud --quiet auth configure-docker
        docker pull "gcr.io/$PROJECT_ID/$PROJECT_NAME:latest" || true        
        /home/runner/.local/bin/kedro docker build --image "gcr.io/$PROJECT_ID/$PROJECT_NAME:$GITHUB_SHA" --docker-args "--cache-from gcr.io/$PROJECT_ID/$PROJECT_NAME:latest" --gid 0

    - name: Publish
      run: |-
        docker push "gcr.io/$PROJECT_ID/$PROJECT_NAME:$GITHUB_SHA"
        docker tag "gcr.io/$PROJECT_ID/$PROJECT_NAME:$GITHUB_SHA" "gcr.io/$PROJECT_ID/$PROJECT_NAME:latest"
        docker push "gcr.io/$PROJECT_ID/$PROJECT_NAME:latest"

    - name: Deploy pipeline
      run: |-
        pip3 install kedro-kubeflow
        /home/runner/.local/bin/kedro install
        sed -i -e"s/__GITHUB_SHA__/$GITHUB_SHA/" conf/base/kubeflow.yaml
        sed -i -e"s/__PROJECT_ID__/$PROJECT_ID/" conf/base/kubeflow.yaml
        /home/runner/.local/bin/kedro kubeflow upload-pipeline
        /home/runner/.local/bin/kedro kubeflow list-pipelines
        /home/runner/.local/bin/kedro kubeflow schedule -c '0 0 4 * * *' # 04:00:00 each day
""",
}
