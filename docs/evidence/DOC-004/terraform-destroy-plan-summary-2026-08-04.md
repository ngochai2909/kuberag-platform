# DOC-004 — Terraform destroy plan summary (2026-08-04)

Scope: **compute/network only**. Artifact Registry, Workload Identity, and
service accounts are intentionally retained so immutable release digests remain
pullable after recreate.

```text
Terraform will perform the following actions:
  # google_compute_address.kuberag will be destroyed
  # google_compute_disk.data will be destroyed
  # google_compute_disk.worker_data["application"] will be destroyed
  # google_compute_disk.worker_data["observability"] will be destroyed
  # google_compute_firewall.admin will be destroyed
  # google_compute_firewall.gateway will be destroyed
  # google_compute_firewall.iap_ssh will be destroyed
  # google_compute_firewall.internal will be destroyed
  # google_compute_instance.kuberag will be destroyed
  # google_compute_instance.worker["application"] will be destroyed
  # google_compute_instance.worker["observability"] will be destroyed
  # google_compute_network.kuberag will be destroyed
  # google_compute_router.kuberag will be destroyed
  # google_compute_router_nat.kuberag will be destroyed
  # google_compute_subnetwork.kuberag will be destroyed
Plan: 0 to add, 0 to change, 15 to destroy.
│ Warning: Resource targeting is in effect
```
