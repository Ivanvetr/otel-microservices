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

# ---------------------------------------------------------------------------
# Módulo A — data-service: Cloud SQL (GCP) + RDS (AWS)
# ---------------------------------------------------------------------------
variable "aws_region" {
  description = "Región de AWS donde se despliega RDS/VPC Flow Logs/Security Hub."
  type        = string
  default     = "us-east-1"
}

variable "enable_data_service_databases" {
  description = "Si es true, aprovisiona las instancias reales de Cloud SQL (GCP) y RDS (AWS) para data-service. En false, se documenta el IaC pero se sigue trabajando localmente contra los Postgres de docker-compose."
  type        = bool
  default     = false
}

variable "cloudsql_tier" {
  description = "Tier de la instancia de Cloud SQL para Postgres (data-service)."
  type        = string
  default     = "db-f1-micro"
}

variable "cloudsql_db_password" {
  description = "Password del usuario de aplicación en Cloud SQL."
  type        = string
  sensitive   = true
  default     = "changeme-cloudsql"
}

variable "rds_instance_class" {
  description = "Clase de instancia de RDS Postgres (data-service)."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_db_password" {
  description = "Password del usuario de aplicación en RDS."
  type        = string
  sensitive   = true
  default     = "changeme-rds"
}

# ---------------------------------------------------------------------------
# Módulo C — Network & Security Observability
# ---------------------------------------------------------------------------
variable "enable_network_security" {
  description = "Si es true, aprovisiona VPC Flow Logs (GCP/AWS) y Security Hub/SCC. En false, solo queda documentado el IaC."
  type        = bool
  default     = false
}

variable "vpc_network_name" {
  description = "Nombre de la VPC de GCP donde se habilitan los Flow Logs."
  type        = string
  default     = "otel-observability-vpc"
}

# ---------------------------------------------------------------------------
# Módulo B — AIOps: Anomaly Detection (GCP) / DevOps Guru (AWS)
# ---------------------------------------------------------------------------
variable "enable_aiops" {
  description = "Si es true, aprovisiona la política de Cloud Monitoring Anomaly Detection y habilita DevOps Guru. En false, solo queda documentado el IaC (el equivalente funcional local es aiops/anomaly_detector.py)."
  type        = bool
  default     = false
}

variable "notification_channel_email" {
  description = "Email al que se notifican las alertas de Cloud Monitoring (Módulo B)."
  type        = string
  default     = "observability-team@example.com"
}
