output "otel_collector_url" {
  description = "URL pública (HTTPS) del OTel Collector en Cloud Run (endpoint OTLP gRPC vía h2c)."
  value       = google_cloud_run_v2_service.otel_collector_grpc.uri
}

output "otel_collector_service_account" {
  description = "Service Account usada por el Collector para leer la configuración desde Secret Manager."
  value       = google_service_account.otel_collector_sa.email
}

output "artifact_registry_repo" {
  description = "Repositorio de Artifact Registry para las imágenes de service-a/service-b."
  value       = google_artifact_registry_repository.otel_repo.name
}

output "gke_backends_cluster" {
  description = "Nombre del clúster GKE Autopilot para Jaeger/Prometheus/Grafana (si enable_gke_backends=true)."
  value       = var.enable_gke_backends ? google_container_cluster.otel_backends[0].name : null
}
