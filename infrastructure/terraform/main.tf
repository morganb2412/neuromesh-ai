terraform {
  required_version = ">= 1.14"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 8.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
  }
}

variable "project_id" {
  type    = string
  default = "moesautomationweekly"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "deploy_app" {
  type        = bool
  default     = false
  description = "Second-stage switch; first create the data and image repository, then deploy a built image."
}

variable "image" {
  type        = string
  default     = ""
  description = "Immutable Artifact Registry image URI, required when deploy_app is true."
  validation {
    condition     = !var.deploy_app || length(var.image) > 0
    error_message = "Set image to a built Artifact Registry image before deploy_app=true."
  }
}

variable "enable_adk" {
  type    = bool
  default = false
}

variable "model_id" {
  type    = string
  default = ""
  validation {
    condition     = !var.enable_adk || length(var.model_id) > 0
    error_message = "Provide a verified Vertex model_id before enabling ADK."
  }
}

variable "model_location" {
  type        = string
  default     = "global"
  description = "Vertex AI model endpoint location; regional Cloud Run and SQL remain in region."
}

variable "enable_cloud_tts" {
  type    = bool
  default = false
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "neuromesh"
  format        = "DOCKER"
  description   = "NeuroMesh application images"
}

resource "google_artifact_registry_repository_iam_member" "cloudbuild_writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "neuromesh-runtime"
  display_name = "NeuroMesh Cloud Run runtime"
}

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "random_password" "operator" {
  length  = 48
  special = false
}

resource "google_secret_manager_secret" "database" {
  project   = var.project_id
  secret_id = "neuromesh-db-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "operator" {
  project   = var.project_id
  secret_id = "neuromesh-operator-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database" {
  secret      = google_secret_manager_secret.database.id
  secret_data = random_password.database.result
}

resource "google_secret_manager_secret_version" "operator" {
  secret      = google_secret_manager_secret.operator.id
  secret_data = random_password.operator.result
}

resource "google_secret_manager_secret_iam_member" "database_runtime" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.database.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "operator_runtime" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.operator.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "cloudsql_runtime" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "vertex_runtime" {
  count   = var.enable_adk ? 1 : 0
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_sql_database_instance" "database" {
  project             = var.project_id
  name                = "neuromesh-db"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = true
  settings {
    edition                     = "ENTERPRISE"
    tier                        = "db-f1-micro"
    availability_type           = "ZONAL"
    disk_type                   = "PD_SSD"
    disk_size                   = 10
    disk_autoresize             = false
    deletion_protection_enabled = true
    backup_configuration {
      enabled    = true
      start_time = "08:00"
    }
    ip_configuration { ipv4_enabled = true }
  }
}

resource "google_sql_database" "database" {
  project  = var.project_id
  instance = google_sql_database_instance.database.name
  name     = "neuromesh"
}

resource "google_sql_user" "app" {
  project  = var.project_id
  instance = google_sql_database_instance.database.name
  name     = "neuromesh_app"
  password = random_password.database.result
}

resource "google_cloud_run_v2_service" "app" {
  count                = var.deploy_app ? 1 : 0
  project              = var.project_id
  location             = var.region
  name                 = "neuromesh-observatory"
  ingress              = "INGRESS_TRAFFIC_ALL"
  invoker_iam_disabled = true

  template {
    service_account = google_service_account.runtime.email
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    timeout = "120s"
    containers {
      image = var.image
      ports { container_port = 8080 }
      resources { limits = { cpu = "1", memory = "1Gi" } }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      env {
        name  = "NEUROMESH_DB_HOST"
        value = "/cloudsql/${google_sql_database_instance.database.connection_name}"
      }
      env {
        name  = "NEUROMESH_DB_NAME"
        value = google_sql_database.database.name
      }
      env {
        name  = "NEUROMESH_DB_USER"
        value = google_sql_user.app.name
      }
      env {
        name  = "NEUROMESH_SEED_DEMO"
        value = "false"
      }
      env {
        name  = "NEUROMESH_ENABLE_ADK"
        value = tostring(var.enable_adk)
      }
      env {
        name  = "NEUROMESH_ENABLE_CLOUD_TTS"
        value = tostring(var.enable_cloud_tts)
      }
      env {
        name  = "NEUROMESH_VOICE_NAME"
        value = "en-US-Standard-J"
      }
      env {
        name  = "NEUROMESH_MODEL"
        value = var.model_id
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.model_location
      }
      env {
        name  = "NEUROMESH_ADK_DAILY_LIMIT"
        value = "20"
      }
      env {
        name  = "NEUROMESH_TTS_DAILY_CHAR_LIMIT"
        value = "20000"
      }
      env {
        name = "NEUROMESH_DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "NEUROMESH_ADMIN_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.operator.secret_id
            version = "latest"
          }
        }
      }
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.database.connection_name]
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.database_runtime,
    google_secret_manager_secret_iam_member.operator_runtime,
  google_project_iam_member.cloudsql_runtime]
}

output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
output "database_connection_name" {
  value = google_sql_database_instance.database.connection_name
}
output "app_url" {
  value = var.deploy_app ? google_cloud_run_v2_service.app[0].uri : null
}
output "operator_token" {
  value     = random_password.operator.result
  sensitive = true
}
