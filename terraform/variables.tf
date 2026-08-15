variable "project_id" {
  description = "ID del proyecto de GCP donde se despliega el OTel Collector."
  type        = string
}

variable "region" {
  description = "Región de despliegue (Cloud Run + Artifact Registry)."
  type        = string
  default     = "us-central1"
}

variable "otel_collector_image" {
  description = "Imagen del OTel Collector Contrib a desplegar en Cloud Run."
  type        = string
  default     = "otel/opentelemetry-collector-contrib:0.110.0"
}

variable "otel_collector_config_path" {
  description = "Ruta local al archivo otel-collector-config.yaml que se sube a Secret Manager."
  type        = string
  default     = "../otel-collector/otel-collector-config.yaml"
}

variable "min_instances" {
  description = "Instancias mínimas del Collector en Cloud Run (0 = scale-to-zero)."
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Instancias máximas del Collector en Cloud Run."
  type        = number
  default     = 5
}

variable "cpu_limit" {
  description = "Límite de CPU por instancia del Collector."
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Límite de memoria por instancia del Collector (debe ser > memory_limiter del Collector)."
  type        = string
  default     = "512Mi"
}

variable "allow_unauthenticated" {
  description = <<-EOT
    Si es true, expone el endpoint OTLP del Collector públicamente (solo recomendable
    para pruebas). En producción, usar autenticación IAM entre servicios (Direct VPC
    egress + service-to-service auth) y dejar esto en false.
  EOT
  type    = bool
  default = false
}

variable "enable_gke_backends" {
  description = "Si es true, provisiona un clúster GKE Autopilot para alojar Jaeger/Prometheus/Grafana (ver ../helm)."
  type        = bool
  default     = false
}
