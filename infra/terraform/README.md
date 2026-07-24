# Terraform

This phase uses local automation plus Ansible to create the temporary single-node k3s foundation. No GCP resource is created in the local foundation phase.

The GCP Terraform module will be added when the project returns to the final topology: one k3s server/control-plane VM and two k3s worker VMs in the same VPC and zone.
