# Release workflow

1. Create the release candidate:
    - Go to the `create-release-candidate action`
    - Click "Run workflow"
    - Enter the part of the version to bump (one of `<major>.<minor>.<patch>`)
2. If the workflow has run sucessfully:
    - Go to the newly openened PR named `Release candidate `<version>`
    - Check that changelog and version have been properly updated.
    - *(If everything is normal, skip this step)* Eventually pull the branch and make changes if necessary
    - Merge the PR to master
3. Checkout the `publish workflow`to see if:
    - The package has been uploaded on PyPI sucessfully
    - The changes have been merged back to develop
4. If the pipeline has failed, please raise an issue to correct the CI, and ensure merge on develop "by hand"".
