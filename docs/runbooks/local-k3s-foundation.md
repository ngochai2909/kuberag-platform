# Local k3s Foundation Runbook

This runbook covers the temporary single-node k3s foundation. It does not create GCP resources and does not represent the final three-node topology.

## Scope

- Install one local k3s server node.
- Disable Traefik during install so project routing can be owned by Envoy Gateway in the next foundation step.
- Create project namespaces.
- Enforce Pod Security Standards `restricted` on custom workload namespaces.
- Deploy a small restricted smoke workload in the `rag` namespace.
- Verify that an unsafe root/privileged Pod is rejected.

## Prerequisites

- Linux host with sudo access.
- `terraform` for future IaC validation.
- `ansible-playbook` for local host configuration.
- `kubectl` and `helm` installed before platform chart work.
- Enough free RAM for the current foundation step. The smoke workload is intentionally tiny.

Validated local versions:

- k3s `v1.35.5+k3s1`
- Helm `v4.2.2`
- Envoy Gateway chart `v1.8.3`

## Commands

```bash
make infra-check
make k3s-install
export KUBECONFIG="$HOME/.kube/kuberag-k3s.yaml"
make k3s-foundation-apply
make k3s-foundation-status
make k3s-foundation-smoke
make k3s-unsafe-check
```

Install or reconcile the Envoy Gateway controller:

```bash
helm upgrade --install envoy-gateway \
  oci://docker.io/envoyproxy/gateway-helm \
  --version v1.8.3 \
  --namespace gateway-system
kubectl wait --timeout=5m --namespace gateway-system \
  deployment/envoy-gateway --for=condition=Available
```

The controller alone does not expose traffic. `GatewayClass`, `Gateway`, and `HTTPRoute` remain a separate declarative Kustomize step. The local Gateway listener must use port `8080` because Apache owns host port `80` outside this project.

## Evidence To Capture

Save command output under `docs/evidence/` using the acceptance criterion IDs:

- `INF-003`: Ansible recap for first install.
- `INF-004`: Ansible recap for the second run.
- `K8S-001`: `kubectl get nodes -o wide`.
- `K8S-002`: `kubectl get nodes --show-labels`.
- `K8S-003`: namespace YAML showing PSS labels.
- `K8S-004`: smoke deployment status and Pod security context.
- `K8S-005`: rejection output from `make k3s-unsafe-check`.
- `NET-001`: controller status is partial evidence only; the criterion remains pending until Gateway resources are Accepted and the route resolves.

## Rollback

Remove the smoke manifests:

```bash
make k3s-foundation-delete
```

Uninstalling k3s is a host-level destructive action. Run it manually only when you intend to remove the local cluster:

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```
