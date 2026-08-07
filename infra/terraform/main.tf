locals {
  instance_name = "${var.name_prefix}-server"
  resource_labels = {
    application = "kuberag"
    environment = var.environment
    managed-by  = "terraform"
    topology    = "single-node"
  }
  gateway_source_ranges = length(var.gateway_source_cidrs) == 0 ? [var.admin_source_cidr] : var.gateway_source_cidrs
  worker_nodes = {
    observability = {
      machine_type = var.observability_worker_machine_type
      private_ip   = var.worker_private_ips.observability
      role         = "observability"
    }
    application = {
      machine_type = var.application_worker_machine_type
      private_ip   = var.worker_private_ips.application
      role         = "application"
    }
  }
}

resource "google_project_service" "iap" {
  project = var.project_id
  service = "iap.googleapis.com"

  disable_on_destroy = false
}

# Artifact Registry must be enabled before Terraform can create the regional
# Docker repository. Keeping this API activation in state makes a clean apply
# reproducible without a manual Console step.
resource "google_project_service" "artifact_registry" {
  project = var.project_id
  service = "artifactregistry.googleapis.com"

  disable_on_destroy = false
}

# GitHub Actions exchanges its OIDC identity for short-lived credentials of the
# Artifact Registry writer service account. Docker's gcloud credential helper
# requires this API for that impersonation step.
resource "google_project_service" "iam_credentials" {
  project = var.project_id
  service = "iamcredentials.googleapis.com"

  disable_on_destroy = false
}

# Regional immutable registry for the three KubeRAG custom images.
resource "google_artifact_registry_repository" "kuberag" {
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "Immutable KubeRAG release images"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]

  docker_config {
    immutable_tags = true
  }

  # CI runs Trivy image scans. Do not inherit Artifact Registry/Container
  # Analysis automatic vulnerability scanning, which can add paid scope.
  vulnerability_scanning_config {
    enablement_config = "DISABLED"
  }

  cleanup_policies {
    id     = "keep-two-newest-release-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 2
    }
  }

  cleanup_policies {
    id     = "delete-old-tagged-versions"
    action = "DELETE"
    condition {
      tag_state  = "TAGGED"
      older_than = "604800s"
    }
  }

  cleanup_policies {
    id     = "delete-untagged-after-seven-days"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s"
    }
  }
}

resource "google_service_account" "node" {
  # Google caps account_id at 30 characters while name_prefix permits 32.
  account_id   = "${substr(var.name_prefix, 0, 25)}-node"
  display_name = "KubeRAG single-node Artifact Registry reader"
}

resource "google_project_iam_member" "node_artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.node.email}"
}

# GitHub Actions uses OIDC federation, never a downloaded service-account key.
resource "google_service_account" "github_release" {
  account_id   = "${substr(var.name_prefix, 0, 15)}-github-release"
  display_name = "KubeRAG GitHub Actions Artifact Registry writer"
}

resource "google_project_iam_member" "github_release_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_release.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${var.name_prefix}-github"
  display_name              = "KubeRAG GitHub Actions"
  description               = "OIDC identities from the KubeRAG GitHub repository"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub Actions OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/main'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_release_workload_identity_user" {
  service_account_id = google_service_account.github_release.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
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

# Private workers need outbound access for Ubuntu packages, the pinned k3s
# binary, Artifact Registry, and the model/bootstrap downloads. Cloud NAT is
# egress-only: it creates no public address on a worker and no inbound rule.
resource "google_compute_router" "kuberag" {
  name    = "${var.name_prefix}-router"
  region  = var.region
  network = google_compute_network.kuberag.id

  bgp {
    asn = 64514
  }
}

resource "google_compute_router_nat" "kuberag" {
  name                               = "${var.name_prefix}-nat"
  router                             = google_compute_router.kuberag.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.kuberag.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  log_config {
    enable = false
    filter = "ERRORS_ONLY"
  }
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

# The temporary demo exposes Envoy on this reserved IP. The gateway firewall
# restricts it to gateway_source_cidrs/admin_source_cidr; observability remains
# ClusterIP/IAP-only. This exception is documented in SECURITY_EXCEPTIONS.md.
# trivy:ignore:GCP-0031
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

  service_account {
    email = google_service_account.node.email
    # OAuth scope is required for the VM to use its narrowly scoped IAM role.
    # Applying this may require a controlled VM stop/start.
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
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
    # `gcloud compute ssh` may add a short-lived operator key to this metadata
    # value. Do not remove that access while adding workers; key rotation is a
    # separately reviewed security operation.
    ignore_changes = [metadata["ssh-keys"]]

    precondition {
      condition     = startswith(var.zone, "${var.region}-")
      error_message = "zone must belong to region."
    }
  }
}

# Workers have no external IP. Operators reach them through the existing server
# (or IAP), while the k3s control plane and Pod network use the private subnet.
resource "google_compute_disk" "worker_data" {
  for_each = local.worker_nodes

  name = "${var.name_prefix}-worker-${each.key}-data"
  type = var.disk_type
  zone = var.zone
  size = var.worker_data_disk_size_gb

  labels = merge(local.resource_labels, {
    topology = "three-node"
    role     = each.value.role
  })
}

resource "google_compute_instance" "worker" {
  for_each = local.worker_nodes

  name         = "${var.name_prefix}-worker-${each.key}"
  machine_type = each.value.machine_type
  zone         = var.zone

  # Compute Engine must stop a VM before changing its machine type. The
  # observability worker is not being resized in this operation.
  allow_stopping_for_update = each.key == "application"
  deletion_protection       = false

  tags = ["${var.name_prefix}-node"]
  labels = merge(local.resource_labels, {
    topology = "three-node"
    role     = each.value.role
  })

  boot_disk {
    auto_delete = true

    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2404-lts-amd64"
      size  = var.worker_boot_disk_size_gb
      type  = var.disk_type
    }
  }

  attached_disk {
    source      = google_compute_disk.worker_data[each.key].id
    device_name = "${var.name_prefix}-worker-${each.key}-data"
    mode        = "READ_WRITE"
  }

  network_interface {
    subnetwork = google_compute_subnetwork.kuberag.id
    network_ip = each.value.private_ip
  }

  metadata = {
    block-project-ssh-keys = "TRUE"
    enable-oslogin         = "FALSE"
    ssh-keys               = "${var.ssh_username}:${trimspace(var.ssh_public_key)}"
  }

  service_account {
    email  = google_service_account.node.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
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
    # `gcloud compute ssh` may add a short-lived operator key to this metadata
    # value. Do not remove that access while resizing workers; key rotation is
    # a separately reviewed security operation.
    ignore_changes = [metadata["ssh-keys"]]

    precondition {
      condition     = startswith(var.zone, "${var.region}-")
      error_message = "zone must belong to region."
    }
  }
}
