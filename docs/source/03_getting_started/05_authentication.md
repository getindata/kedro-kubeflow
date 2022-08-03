# Authenticating to Kubeflow Pipelines API

Plugin supports 2 ways of authenticating to Kubeflow Pipelines API:

## 1. KFP behind IAP proxy on Google Cloud

It's already described in [GCP AI Platform support](02_gcp.md) chapter.

## 2. KFP behind Dex with `authservice`

Dex is the recommended authentication mechanism for on-premise Kubeflow clusters. The usual setup looks in a way that:

* [oidc-autheservice](https://github.com/arrikto/oidc-authservice) redirect unauthenticated users to Dex,
* [Dex](https://github.com/dexidp/dex) authenticates user in remote system, like LDAP or OpenID and also acts as OpenID provider,
* `oidc-autheservice` asks Dex for a token and creates the session used across entire Kubeflow.

In order to use `kedro-kubeflow` behind Dex-secured clusters, use the following manual:

1. Setup [staticPassword](https://github.com/dexidp/dex/blob/b79d9a84bc0c35e13a9d5141e95b641af0f81c8f/cmd/dex/config_test.go#L105) authentication method and add a user that you're going to use as CI/CD account.
2. Point your Kedro project to `/pipeline` API on Kubeflow, for example: `https://kubeflow.local/pipeline`
3. Set environment variables `DEX_USERNAME` and `DEX_PASSWORD` before calling `kedro kubeflow`
