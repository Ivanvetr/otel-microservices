# ---------------------------------------------------------------------------
# Módulo A: Service mesh básico para observabilidad L7 (Cloud Service Mesh en GCP /
# AWS App Mesh en AWS).
#
# Decisión de diseño: desplegar un mesh completo (Anthos Service Mesh / App Mesh con
# Envoy inyectado por sidecar-injector, control plane, mTLS, etc.) requiere un clúster
# GKE/EKS reales y credenciales de nube activas, fuera del alcance verificable de este
# laboratorio. Por eso:
#   1) Aquí se documenta el IaC de habilitación del mesh a nivel de plataforma (gated,
#      no aplicado por defecto).
#   2) La observabilidad L7 equivalente (métricas de request/latencia/retries por
#      Envoy, access logs estructurados) se demuestra 100% funcional en local con los
#      sidecars Envoy de ../docker-compose.yml (envoy-service-b, envoy-data-service) +
#      ../envoy/*.yaml, scrapeados por Prometheus (job "envoy-service-mesh").
# ---------------------------------------------------------------------------

# GCP: habilita la API de Cloud Service Mesh (Anthos Service Mesh administrado) sobre el
# clúster GKE Autopilot opcional definido en main.tf (enable_gke_backends).
resource "google_gke_hub_feature" "service_mesh" {
  count    = var.enable_gke_backends ? 1 : 0
  project  = var.project_id
  location = "global"
  name     = "servicemesh"

  depends_on = [google_project_service.apis]
}

resource "google_gke_hub_membership" "otel_backends_membership" {
  count         = var.enable_gke_backends ? 1 : 0
  project       = var.project_id
  membership_id = "otel-observability-backends"

  endpoint {
    gke_cluster {
      resource_link = "//container.googleapis.com/${google_container_cluster.otel_backends[0].id}"
    }
  }
}

# AWS: App Mesh — un solo "mesh" lógico agrupando los virtual nodes de service-b y
# data-service (equivalente a los sidecars Envoy locales, pero con control plane gestionado).
resource "aws_appmesh_mesh" "otel_observability_mesh" {
  count = var.enable_data_service_databases ? 1 : 0
  name  = "otel-observability-mesh"

  spec {
    egress_filter {
      type = "ALLOW_ALL"
    }
  }
}
