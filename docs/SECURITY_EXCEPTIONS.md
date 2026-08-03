# Security scan exceptions

Exceptions must be narrow, version-controlled, and tied to a verification that
proves the unsafe construct cannot reach a normal deployment.

## PSS negative fixture

`deploy/kustomize/examples/unsafe-root-pod.yaml` intentionally specifies
`privileged: true` and `runAsUser: 0`. It is the negative input for
`make gcp-unsafe-check` and `make k3s-unsafe-check`: Kubernetes Pod Security
Standards `restricted` admission must reject it. The file is not referenced by
any Kustomize overlay, Helm values, or release manifest.

Semgrep excludes only this fixture through `.semgrepignore`. The exception does
not apply to any deployable manifest. Removing the fixture requires replacing
the PSS rejection verification with an equivalent negative test.
