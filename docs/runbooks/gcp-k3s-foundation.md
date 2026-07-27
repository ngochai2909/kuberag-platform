# GCP Single-Node k3s Foundation

This runbook installs the temporary all-in-one k3s server on the Terraform VM.
It does not create the final 1 server + 2 worker topology.

## Network And Storage Decisions

- VPC subnet: `10.42.0.0/24`.
- k3s Pod CIDR: `10.52.0.0/16`.
- k3s Service CIDR: `10.53.0.0/16`.
- Persistent disk device: `/dev/disk/by-id/google-kuberag-data`.
- Persistent mount: `/var/lib/kuberag`.
- k3s data directory: `/var/lib/kuberag/k3s`.

The explicit k3s CIDRs prevent overlap with the GCP subnet. The stable GCE disk
alias prevents the playbook from relying on a mutable name such as `/dev/sdb`.

## Preflight

The local SSH alias must connect through IAP:

```bash
ssh kuberag-gcp
```

Check Ansible syntax and connectivity without changing the VM:

```bash
make gcp-k3s-syntax
ansible k3s_server \
  -i infra/ansible/inventory/gcp.ini \
  -m ansible.builtin.ping
```

## Privileged Install

This command can format an empty 150 GiB disk, update `/etc/fstab`, mount the
disk, and install a system service. Run it only after reviewing the playbook and
giving immediate explicit approval:

```bash
make gcp-k3s-install
```

The playbook refuses to overwrite a filesystem other than `ext4`. A second run
must not format the disk again and should report no unexpected changes.

Verified on 2026-07-27:

- the disk is ext4 and mounted at `/var/lib/kuberag`;
- the k3s node reports `Ready` on `v1.35.5+k3s1`;
- the second playbook run reports `changed=0` and `failed=0`.

## Local kubectl Access

The fetched kubeconfig is written to `~/.kube/kuberag-gcp.yaml` and points to
local port `16443`. Keep this tunnel open in a separate terminal:

```bash
make gcp-k3s-tunnel
```

Then verify the cloud node from another terminal:

```bash
make gcp-k3s-status
```

The tunnel forwards local port `16443` through SSH/IAP to the Kubernetes API on
the VM. It avoids exposing an additional IAP port and does not conflict with the
local k3s API on port `6443`.

## Envoy And Kubernetes Foundation

Keep `make gcp-k3s-tunnel` running in one terminal. The commands below mutate
the GCP Kubernetes cluster but do not create another VM or disk.

Install the third-party Envoy Gateway controller and Gateway API CRDs with Helm:

```bash
make gcp-envoy-install
```

Apply the project-owned namespaces, Pod Security labels, restricted smoke
Deployment, Service, GatewayClass, Gateway, and HTTPRoute with Kustomize:

```bash
make gcp-foundation-apply
make gcp-foundation-status
make gcp-foundation-smoke
make gcp-unsafe-check
```

The GCP overlay listens on host port `8080`, matching the restricted Terraform
firewall rule. The smoke test resolves the static external IP from Terraform
output and requests `/hostname` through this path:

```text
Local curl -> GCP firewall :8080 -> Envoy data plane -> Service -> smoke Pod
```

The smoke backend is temporary. It proves networking and Pod Security before
the React frontend and FastAPI Service replace the smoke route.
