# ---------------------------------------------------------------------------
# Fase 2: OTel Collector en GCP Cloud Run
#
# Decisión de diseño: el Collector es un componente STATELESS de puro paso de
# datos (recibe OTLP, procesa, reenvía) -> encaja perfectamente en Cloud Run
# (escala a cero, cobra por uso, sin gestión de nodos). Jaeger/Prometheus/
# Grafana SÍ requieren almacenamiento persistente (traces, TSDB, dashboards),
# por lo que se modelan como cargas STATEFUL desplegadas vía Helm sobre GKE
# Autopilot (ver ../helm) en lugar de forzarlas también a Cloud Run.
# ---------------------------------------------------------------------------

locals {
  required_apis = [
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "container.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.required_apis)
  project  = var.project_id
  service  = each.value

  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Artifact Registry: repositorio para imágenes propias (service-a/service-b)
# si se decide desplegarlas también en Cloud Run en una siguiente iteración.
# ---------------------------------------------------------------------------
resource "google_artifact_registry_repository" "otel_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "otel-observability"
  description   = "Imágenes de service-a, service-b y OTel Collector"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Secret Manager: configuración del Collector (receivers/processors/exporters)
# ---------------------------------------------------------------------------
resource "google_secret_manager_secret" "otel_collector_config" {
  project   = var.project_id
  secret_id = "otel-collector-config"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "otel_collector_config_v1" {
  secret      = google_secret_manager_secret.otel_collector_config.id
  secret_data = file(var.otel_collector_config_path)
}

# ---------------------------------------------------------------------------
# Service Account dedicada al Collector (principio de mínimo privilegio)
# ---------------------------------------------------------------------------
resource "google_service_account" "otel_collector_sa" {
  project      = var.project_id
  account_id   = "otel-collector-run"
  display_name = "OTel Collector (Cloud Run)"
}

resource "google_secret_manager_secret_iam_member" "collector_secret_access" {
  secret_id = google_secret_manager_secret.otel_collector_config.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.otel_collector_sa.email}"
}

# ---------------------------------------------------------------------------
# Cloud Run v2: OTel Collector (receiver OTLP gRPC)
#
# Nota: Cloud Run v2 expone un único puerto de ingreso por servicio. El
# receiver OTLP gRPC (4317) se usa como puerto principal porque es el
# protocolo por defecto de los SDKs de OTel. Para exponer también OTLP/HTTP
# (4318) se replica el mismo contenedor en un segundo servicio idéntico
# cambiando únicamente el puerto de ingreso.
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "otel_collector_grpc" {
  project  = var.project_id
  name     = "otel-collector-grpc"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.otel_collector_sa.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.otel_collector_image
      args  = ["--config=/etc/otel/otel-collector-config.yaml"]

      ports {
        name           = "h2c" # requerido para gRPC sin TLS entre Cloud Run y el cliente
        container_port = 4317
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      volume_mounts {
        name       = "collector-config"
        mount_path = "/etc/otel"
      }

      startup_probe {
        http_get {
          path = "/"
          port = 13133
        }
        initial_delay_seconds = 5
        period_seconds         = 5
        failure_threshold       = 5
      }
    }

    volumes {
      name = "collector-config"
      secret {
        secret = google_secret_manager_secret.otel_collector_config.secret_id
        items {
          version = "latest"
          path    = "otel-collector-config.yaml"
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_secret_manager_secret_version.otel_collector_config_v1]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.otel_collector_grpc.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------------------------------------------------------------------------
# GKE Autopilot (opcional): aloja Jaeger + Prometheus + Grafana vía Helm
# (ver ../helm/README.md para los charts y values.yaml correspondientes)
# ---------------------------------------------------------------------------
resource "google_container_cluster" "otel_backends" {
  count    = var.enable_gke_backends ? 1 : 0
  project  = var.project_id
  name     = "otel-observability-backends"
  location = var.region

  enable_autopilot = true

  release_channel {
    channel = "REGULAR"
  }

  depends_on = [google_project_service.apis]
}
