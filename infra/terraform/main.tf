locals {
  instance_name = "${var.name_prefix}-server"
  resource_labels = {
    application = "kuberag"
    environment = var.environment
    managed-by  = "terraform"
    topology    = "single-node"
  }
  gateway_source_ranges = length(var.gateway_source_cidrs) == 0 ? [var.admin_source_cidr] : var.gateway_source_cidrs
}

resource "google_project_service" "iap" {
  project = var.project_id
  service = "iap.googleapis.com"

  disable_on_destroy = false
}

resource "google_compute_network" "kuberag" {
  name                    = "${var.name_prefix}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "kuberag" {
  name                     = "${var.name_prefix}-subnet"
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.kuberag.id
  private_ip_google_access = true
}

resource "google_compute_firewall" "internal" {
  name      = "${var.name_prefix}-allow-internal"
  network   = google_compute_network.kuberag.name
  direction = "INGRESS"
  priority  = 1000

  source_ranges = [var.subnet_cidr]
  target_tags   = ["${var.name_prefix}-node"]

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }
}

resource "google_compute_firewall" "admin" {
  name      = "${var.name_prefix}-allow-admin"
  network   = google_compute_network.kuberag.name
  direction = "INGRESS"
  priority  = 1000

  source_ranges = [var.admin_source_cidr]
  target_tags   = ["${var.name_prefix}-node"]

  allow {
    protocol = "tcp"
    ports    = ["22", "6443"]
  }
}

resource "google_compute_firewall" "iap_ssh" {
  name      = "${var.name_prefix}-allow-iap-ssh"
  network   = google_compute_network.kuberag.name
  direction = "INGRESS"
  priority  = 1000

  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["${var.name_prefix}-node"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  depends_on = [google_project_service.iap]
}

resource "google_compute_firewall" "gateway" {
  name      = "${var.name_prefix}-allow-gateway"
  network   = google_compute_network.kuberag.name
  direction = "INGRESS"
  priority  = 1000

  source_ranges = local.gateway_source_ranges
  target_tags   = ["${var.name_prefix}-node"]

  allow {
    protocol = "tcp"
    ports    = [tostring(var.gateway_port)]
  }
}

resource "google_compute_address" "kuberag" {
  name         = "${var.name_prefix}-external-ip"
  region       = var.region
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
}

resource "google_compute_disk" "data" {
  name = "${var.name_prefix}-data"
  type = var.disk_type
  zone = var.zone
  size = var.data_disk_size_gb

  labels = local.resource_labels
}

resource "google_compute_instance" "kuberag" {
  name         = local.instance_name
  machine_type = var.machine_type
  zone         = var.zone

  allow_stopping_for_update = true
  deletion_protection       = false

  tags   = ["${var.name_prefix}-node"]
  labels = local.resource_labels

  boot_disk {
    auto_delete = true

    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2404-lts-amd64"
      size  = var.boot_disk_size_gb
      type  = var.disk_type
    }
  }

  attached_disk {
    source      = google_compute_disk.data.id
    device_name = "${var.name_prefix}-data"
    mode        = "READ_WRITE"
  }

  network_interface {
    subnetwork = google_compute_subnetwork.kuberag.id

    access_config {
      nat_ip       = google_compute_address.kuberag.address
      network_tier = "PREMIUM"
    }
  }

  metadata = {
    block-project-ssh-keys = "TRUE"
    enable-oslogin         = "FALSE"
    ssh-keys               = "${var.ssh_username}:${trimspace(var.ssh_public_key)}"
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    provisioning_model  = "STANDARD"
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = true
    enable_vtpm                 = true
  }

  lifecycle {
    precondition {
      condition     = startswith(var.zone, "${var.region}-")
      error_message = "zone must belong to region."
    }
  }
}
