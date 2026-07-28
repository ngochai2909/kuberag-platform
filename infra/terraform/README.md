# GCP Single-Node Terraform

This root module creates the temporary Google Cloud foundation for one
all-in-one k3s node. It is the GCP equivalent of the local single-node
checkpoint; it is not the final 1 server + 2 worker topology.

## Responsibility Boundary

```text
Terraform -> VPC, subnet, firewall, static IP, VM, attached data disk
Ansible   -> OS prerequisites, data-disk mount, k3s installation, kubeconfig
Kustomize -> KubeRAG namespaces and custom workloads
Helm      -> third-party Kubernetes platforms
```

Terraform does not install k3s or deploy Kubernetes workloads. Keeping those
responsibilities separate lets the same Ansible logic later configure one
server and join two workers.

## Resources

| Resource | Current single-node purpose |
|---|---|
| Custom VPC and `/24` subnet | Isolated private network with room for the final worker nodes |
| Internal firewall | Node-to-node traffic inside only the KubeRAG subnet |
| Admin firewall | TCP `22` and `6443` from one administrator CIDR |
| IAP SSH firewall | TCP `22` from Google IAP `35.235.240.0/20`; access still requires IAM |
| Gateway firewall | TCP `8080`, restricted to the administrator CIDR by default |
| Static external IPv4 | Stable endpoint for SSH, kubectl, and Envoy |
| Compute Engine VM | `e2-custom-8-16384`: 8 vCPU and 16 GiB RAM |
| Boot disk | 30 GiB `pd-balanced`, deleted with the VM |
| Data disk | 150 GiB `pd-balanced` for models, k3s data, and persistent volumes |

The separate data disk is still managed by Terraform and is deleted by
`terraform destroy`. It remains attached and billable while the VM is stopped.
The reserved external address can also incur cost while unused.

The 150 GiB allocation leaves headroom for PostgreSQL/pgvector, one pinned GGUF
model, container images, and short-retention observability data. Ansible must
mount this disk and place k3s data on it; otherwise the 30 GiB boot disk can fill
while the data disk remains unused.

## Local Inputs

Create the ignored local variable file:

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

Replace these placeholders in `terraform.tfvars`:

- `YOUR_GCP_PROJECT_ID`: the project selected by `gcloud config get-value project`.
- `203.0.113.10/32`: the current public IPv4 address of the administrator machine.
- `REPLACE_WITH_YOUR_PUBLIC_KEY`: the full public key from
  `~/.ssh/kuberag_gcp.pub`, without changing its OpenSSH prefix.

Do not commit `terraform.tfvars`, Terraform state, ADC credentials, or private
SSH keys. The root `.gitignore` excludes the local variable and state files.

## Checkpoint 1: Initialize And Validate

These commands download the pinned provider and validate local configuration.
They do not create GCP resources or start billing:

```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
```

Commit `.terraform.lock.hcl` after `init`; it records the exact provider build
and checksums used by this root module.

## Checkpoint 2: Review The Plan

`plan` reads GCP APIs and calculates proposed changes but does not create them:

```bash
terraform -chdir=infra/terraform plan -out=tfplan
terraform -chdir=infra/terraform show tfplan
```

Review resource count, machine type, disk sizes, firewall source ranges, and
the external IP before apply. The `tfplan` file can contain infrastructure
details and must not be committed.

## Checkpoint 3: Apply

Apply creates billable cloud resources. Run it only after an immediate explicit
approval based on the reviewed plan:

```bash
terraform -chdir=infra/terraform apply tfplan
```

After apply, Terraform outputs the external IP, SSH target, Ansible inventory
host, future Kubernetes API endpoint, and future Envoy URL. These endpoints do
not work until Ansible and the Kubernetes manifests are applied.

Use IAP for SSH administration when direct TCP `22` connectivity is unavailable:

```bash
gcloud compute ssh kuberag@kuberag-server \
  --zone=asia-southeast1-b \
  --project=kube-rag-platform \
  --ssh-key-file="$HOME/.ssh/kuberag_gcp" \
  --tunnel-through-iap
```

The IAP path reaches the VM through its internal interface. Terraform enables
the IAP API and permits TCP `22` only from Google's documented IAP forwarding
range; IAM still determines who can establish the tunnel.

Use `docs/runbooks/gcp-cost-control.md` to stop, start, and destroy the VM.
Stopping the VM does not stop disk or reserved-address charges, and the billing
budget is an alert rather than a spending cap.
