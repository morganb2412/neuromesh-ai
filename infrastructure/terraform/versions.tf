terraform {
  required_version = ">= 1.7"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}

variable "project_id" { type = string }
variable "region" { type = string default = "us-central1" }
variable "image" { type = string description = "Prebuilt backend container image URI" }

provider "google" {
  project = var.project_id
  region  = var.region
}

# Prototype API only. The SQLite store is ephemeral in Cloud Run; do not use this
# module for retained research data or provider-backed public workloads.
resource "google_cloud_run_v2_service" "api_preview" {
  name     = "neuromesh-api-preview"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  template {
    scaling { min_instance_count = 0 max_instance_count = 1 }
    containers {
      image = var.image
      resources { limits = { cpu = "1", memory = "512Mi" } }
      env { name = "NEUROMESH_ENABLE_ADK" value = "false" }
    }
  }
}

output "api_uri" { value = google_cloud_run_v2_service.api_preview.uri }
