# ---------------------------------------------------------------------------
# Módulo C: Network & Security Observability — VPC Flow Logs (GCP/AWS) + Security Hub/SCC.
# Gated por enable_network_security (default false); el equivalente local funcional es
# el dashboard "Golden Signals de Seguridad" (../grafana/.../security-golden-signals.json)
# alimentado por los contadores auth_failed/auth_success de data-service y las métricas
# N-S/E-W de los sidecars Envoy.
# ---------------------------------------------------------------------------

# --- GCP: VPC + subred con Flow Logs habilitados ---
resource "google_compute_network" "otel_vpc" {
  count                   = var.enable_network_security ? 1 : 0
  project                 = var.project_id
  name                    = var.vpc_network_name
  auto_create_subnetworks = false

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "otel_subnet" {
  count         = var.enable_network_security ? 1 : 0
  project       = var.project_id
  name          = "${var.vpc_network_name}-subnet"
  region        = var.region
  network       = google_compute_network.otel_vpc[0].id
  ip_cidr_range = "10.10.0.0/20"

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Alerta sobre tráfico anómalo entre servicios (basada en los Flow Logs exportados a
# Cloud Logging -> métrica basada en logs -> política de alerta de Cloud Monitoring).
resource "google_logging_metric" "anomalous_east_west_traffic" {
  count       = var.enable_network_security ? 1 : 0
  project     = var.project_id
  name        = "anomalous-east-west-traffic"
  description = "Conexiones internas (E-W) rechazadas por firewall, candidatas a tráfico anómalo entre microservicios."
  filter      = "resource.type=\"gce_subnetwork\" AND jsonPayload.disposition=\"DENIED\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_monitoring_alert_policy" "anomalous_traffic_alert" {
  count        = var.enable_network_security ? 1 : 0
  project      = var.project_id
  display_name = "Tráfico E-W anómalo entre microservicios (VPC Flow Logs)"
  combiner     = "OR"

  conditions {
    display_name = "Denegaciones de firewall > 10 en 5 min"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.anomalous_east_west_traffic[0].name}\" AND resource.type=\"gce_subnetwork\""
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      duration        = "300s"
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = var.enable_aiops ? [google_monitoring_notification_channel.email[0].id] : []
}

# --- AWS: VPC Flow Logs hacia CloudWatch Logs ---
resource "aws_flow_log" "vpc_flow_logs" {
  count                = var.enable_network_security ? 1 : 0
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  iam_role_arn         = aws_iam_role.vpc_flow_logs_role[0].arn
  vpc_id               = data.aws_vpc.default[0].id
  traffic_type         = "ALL"
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count             = var.enable_network_security ? 1 : 0
  name              = "/otel-observability/vpc-flow-logs"
  retention_in_days = 30
}

resource "aws_iam_role" "vpc_flow_logs_role" {
  count = var.enable_network_security ? 1 : 0
  name  = "vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "vpc_flow_logs_policy" {
  count = var.enable_network_security ? 1 : 0
  name  = "vpc-flow-logs-policy"
  role  = aws_iam_role.vpc_flow_logs_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
      ]
      Resource = "*"
    }]
  })
}

# --- Security Hub (AWS) — observabilidad de seguridad básica ---
resource "aws_securityhub_account" "this" {
  count = var.enable_network_security ? 1 : 0
}

# --- Security Command Center (GCP) — notificación de findings de seguridad ---
# Nota: SCC es un recurso a nivel de organización; requiere permisos de Org Admin, por lo
# que aquí solo se documenta el recurso de notificación (asume que SCC ya está activado
# a nivel de organización, típicamente por el equipo de seguridad central).
resource "google_scc_notification_config" "security_findings" {
  count        = var.enable_network_security ? 1 : 0
  config_id    = "otel-observability-findings"
  organization = "ORGANIZATION_ID" # reemplazar por el ID real de la organización de GCP
  description  = "Notifica findings de Security Command Center relevantes al proyecto de observabilidad"
  pubsub_topic = "projects/${var.project_id}/topics/scc-findings"

  streaming_config {
    filter = "state = \"ACTIVE\""
  }
}
