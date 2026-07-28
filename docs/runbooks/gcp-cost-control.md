# GCP Cost Control Runbook

This runbook covers the temporary GCP single-node checkpoint. A Google Cloud
budget sends notifications but does not stop resources or cap spending.

## Current Budget

- Monthly budget: VND 3,000,000.
- Scope: the Free Trial billing account containing the KubeRAG project.
- Alert thresholds: 50%, 90%, 100%, and 150%.
- Review Billing reports after each infrastructure checkpoint because cost data
  can be delayed.

## Daily Stop

Stop the VM outside working hours. Stopping removes vCPU and memory runtime
charges, but attached disks and reserved external IP resources can still incur
charges.

```bash
gcloud compute instances stop kuberag-server \
  --project=kube-rag-platform \
  --zone=asia-southeast1-b
```

Confirm the state:

```bash
gcloud compute instances describe kuberag-server \
  --project=kube-rag-platform \
  --zone=asia-southeast1-b \
  --format='value(status)'
```

Expected state: `TERMINATED`.

## Start

```bash
gcloud compute instances start kuberag-server \
  --project=kube-rag-platform \
  --zone=asia-southeast1-b
```

After the VM is `RUNNING`, verify SSH, the k3s service, node readiness, and the
Envoy smoke endpoint before continuing work.

Connect through IAP using the local SSH configuration:

```bash
ssh kuberag-gcp
```

The alias uses `gcloud compute start-iap-tunnel`; it does not depend on direct
TCP `22` reachability to the VM's external address.

## Destroy

Use Terraform from the same working directory and state that created the
resources. Review the destroy plan before approving it.

```bash
terraform -chdir=infra/terraform plan -destroy
terraform -chdir=infra/terraform destroy
```

Destroy is intentionally manual. Confirm that Compute Engine instances,
persistent disks, reserved addresses, and unexpected billable resources are no
longer present in the project after Terraform completes.

Do not delete or edit Terraform state manually, and never commit state or
credential files.
