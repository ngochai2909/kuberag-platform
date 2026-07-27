output "instance_name" {
  description = "Name of the temporary single-node Compute Engine instance."
  value       = google_compute_instance.kuberag.name
}

output "instance_zone" {
  description = "Zone containing the VM and data disk."
  value       = google_compute_instance.kuberag.zone
}

output "external_ip" {
  description = "Reserved external IPv4 address used by SSH, kubectl, and Envoy."
  value       = google_compute_address.kuberag.address
}

output "internal_ip" {
  description = "Private IPv4 address of the k3s node."
  value       = google_compute_instance.kuberag.network_interface[0].network_ip
}

output "ssh_target" {
  description = "SSH user and host. Supply the private key path locally when connecting."
  value       = "${var.ssh_username}@${google_compute_address.kuberag.address}"
}

output "ansible_inventory_host" {
  description = "Host entry to place in the generated local Ansible inventory."
  value       = "${local.instance_name} ansible_host=${google_compute_address.kuberag.address} ansible_user=${var.ssh_username}"
}

output "kubernetes_api_endpoint" {
  description = "Expected k3s API endpoint after Ansible installs k3s."
  value       = "https://${google_compute_address.kuberag.address}:6443"
}

output "gateway_url" {
  description = "Expected Envoy endpoint after the Kubernetes gateway workloads are deployed."
  value       = "http://${google_compute_address.kuberag.address}:${var.gateway_port}"
}

output "data_disk_device_name" {
  description = "Stable device name that Ansible will format and mount before k3s data workloads use it."
  value       = google_compute_instance.kuberag.attached_disk[0].device_name
}
