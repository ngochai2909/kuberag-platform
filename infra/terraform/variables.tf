variable "project_id" {
  description = "Google Cloud project ID that owns the KubeRAG resources."
  type        = string

  validation {
    condition     = length(trimspace(var.project_id)) > 0
    error_message = "project_id must not be empty."
  }
}

variable "region" {
  description = "Google Cloud region for regional resources."
  type        = string
  default     = "asia-southeast1"
}

variable "zone" {
  description = "Google Cloud zone for the VM and persistent disk."
  type        = string
  default     = "asia-southeast1-b"
}

variable "environment" {
  description = "Environment label attached to billable resources."
  type        = string
  default     = "demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,62}$", var.environment))
    error_message = "environment must start with a lowercase letter and contain only lowercase letters, digits, or hyphens."
  }
}

variable "name_prefix" {
  description = "Prefix for GCP resource names."
  type        = string
  default     = "kuberag"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,30}[a-z0-9]$", var.name_prefix))
    error_message = "name_prefix must be 2-32 characters using lowercase letters, digits, or hyphens."
  }
}

variable "subnet_cidr" {
  description = "IPv4 CIDR used by the private KubeRAG subnet."
  type        = string
  default     = "10.42.0.0/24"

  validation {
    condition     = can(cidrnetmask(var.subnet_cidr))
    error_message = "subnet_cidr must be a valid IPv4 CIDR."
  }
}

variable "admin_source_cidr" {
  description = "Single administrator IPv4 CIDR allowed to use SSH and the Kubernetes API. Use YOUR_PUBLIC_IP/32."
  type        = string

  validation {
    condition = (
      can(cidrnetmask(var.admin_source_cidr)) &&
      var.admin_source_cidr != "0.0.0.0/0"
    )
    error_message = "admin_source_cidr must be a valid restricted IPv4 CIDR; 0.0.0.0/0 is forbidden."
  }
}

variable "gateway_source_cidrs" {
  description = "IPv4 CIDRs allowed to reach Envoy. An empty list restricts access to admin_source_cidr."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for cidr in var.gateway_source_cidrs : can(cidrnetmask(cidr))])
    error_message = "Every gateway_source_cidrs item must be a valid IPv4 CIDR."
  }
}

variable "gateway_port" {
  description = "Host port exposed for the Envoy Gateway data plane."
  type        = number
  default     = 8080

  validation {
    condition     = var.gateway_port >= 1 && var.gateway_port <= 65535
    error_message = "gateway_port must be between 1 and 65535."
  }
}

variable "ssh_username" {
  description = "Linux account name associated with the instance SSH key."
  type        = string
  default     = "kuberag"

  validation {
    condition     = can(regex("^[a-z_][a-z0-9_-]{0,31}$", var.ssh_username))
    error_message = "ssh_username must be a valid lowercase Linux account name."
  }
}

variable "ssh_public_key" {
  description = "OpenSSH public key installed for ssh_username. Public keys are not secrets, but keep machine-specific values out of Git."
  type        = string

  validation {
    condition = anytrue([
      startswith(trimspace(var.ssh_public_key), "ssh-ed25519 "),
      startswith(trimspace(var.ssh_public_key), "ssh-rsa "),
      startswith(trimspace(var.ssh_public_key), "ecdsa-sha2-")
    ])
    error_message = "ssh_public_key must be a complete OpenSSH public key."
  }
}

variable "machine_type" {
  description = "Compute Engine machine type for the temporary all-in-one k3s node."
  type        = string
  default     = "e2-custom-8-16384"
}

variable "boot_disk_size_gb" {
  description = "Boot disk size in GiB."
  type        = number
  default     = 30

  validation {
    condition     = var.boot_disk_size_gb >= 20
    error_message = "boot_disk_size_gb must be at least 20 GiB."
  }
}

variable "data_disk_size_gb" {
  description = "Persistent data disk size in GiB for models and Kubernetes persistent volumes."
  type        = number
  default     = 150

  validation {
    condition     = var.data_disk_size_gb >= 50
    error_message = "data_disk_size_gb must be at least 50 GiB."
  }
}

variable "disk_type" {
  description = "Compute Engine disk type used for boot and data disks."
  type        = string
  default     = "pd-balanced"

  validation {
    condition     = contains(["pd-balanced", "pd-ssd", "pd-standard"], var.disk_type)
    error_message = "disk_type must be pd-balanced, pd-ssd, or pd-standard."
  }
}
