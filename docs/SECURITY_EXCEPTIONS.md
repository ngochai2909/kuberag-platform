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

Trivy skips the same exact file through the CI action `skip-files` input so its
intentional privilege cannot hide a finding in any other manifest.

## Temporary single-node Envoy public IP

Trivy check `GCP-0031` is ignored inline only on
`google_compute_instance.kuberag`. The required demo route is
`Client -> public Envoy :8080 -> Kubernetes Service -> Pod`; therefore the VM
needs its reserved external IP. The Terraform gateway firewall restricts source
CIDRs to `gateway_source_cidrs` (or the administrator CIDR fallback), while
observability services remain `ClusterIP` and IAP/port-forward-only.

This is not a production internet-exposure approval. A production HTTPS/domain
and authentication design must replace the temporary public demo endpoint
before broader access or final release.
