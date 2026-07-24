# Local k3s Foundation Runbook

This runbook covers the temporary single-node k3s foundation. It does not create GCP resources and does not represent the final three-node topology.

## Scope

- Install one local k3s server node.
- Disable Traefik so Envoy Gateway owns project routing.
- Create project namespaces and enforce Pod Security Standards `restricted` on custom workloads.
- Install the Envoy Gateway controller with Helm.
- Apply declarative `GatewayClass`, `Gateway`, and local smoke `HTTPRoute` resources with Kustomize.
- Verify traffic reaches a small restricted smoke workload in the `rag` namespace.
- Verify that an unsafe root/privileged Pod is rejected.

## Prerequisites

- Linux host with sudo access.
- `terraform` and `ansible-playbook` for infrastructure validation and host configuration.
- `kubectl`, `helm`, and `curl` installed.
- Enough free RAM for the current foundation step. The smoke workload is intentionally tiny.

Validated local versions:

- k3s `v1.35.5+k3s1`
- Helm `v4.2.2`
- Envoy Gateway chart `v1.8.3`

## Commands

Install k3s and select its kubeconfig:

```bash
make infra-check
make k3s-install
export KUBECONFIG="$HOME/.kube/kuberag-k3s.yaml"
```

Install or reconcile the Envoy Gateway controller and Gateway API CRDs:

```bash
helm upgrade --install envoy-gateway \
  oci://docker.io/envoyproxy/gateway-helm \
  --version v1.8.3 \
  --namespace gateway-system \
  --create-namespace
kubectl wait --timeout=5m --namespace gateway-system \
  deployment/envoy-gateway --for=condition=Available
```

Apply and verify the project-owned foundation resources:

```bash
make k3s-foundation-apply
make k3s-foundation-status
make k3s-foundation-smoke
make k3s-unsafe-check
```

The base Gateway listener uses port `80`. The local overlay patches it to `8080` because Apache owns host port `80`. `make k3s-foundation-smoke` verifies the Gateway and HTTPRoute conditions, then requests `/hostname` through Envoy.

## Evidence To Capture

Save command output under `docs/evidence/` using the acceptance criterion IDs:

- `INF-003`: Ansible recap for first install.
- `INF-004`: Ansible recap for the second run.
- `K8S-001`: `kubectl get nodes -o wide`.
- `K8S-002`: `kubectl get nodes --show-labels`.
- `K8S-003`: namespace YAML showing PSS labels.
- `K8S-004`: smoke deployment status and Pod security context.
- `K8S-005`: rejection output from `make k3s-unsafe-check`.
- `NET-001`: Accepted/Programmed/resolved Gateway API conditions and successful HTTP smoke output.
- `NET-004`: no Traefik resources serving KubeRAG routes.

## Rollback

Remove the Helm release before deleting the namespaces and project manifests:

```bash
helm uninstall envoy-gateway --namespace gateway-system
make k3s-foundation-delete
```

Uninstalling k3s is a host-level destructive action. Run it manually only when you intend to remove the local cluster:

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```
