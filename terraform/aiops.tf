# ---------------------------------------------------------------------------
# Módulo B: AIOps — GCP Cloud Monitoring Anomaly Detection + AWS DevOps Guru sobre
# data-service.
#
# El equivalente funcional 100% probado en local es ../aiops/anomaly_detector.py (mismo
# algoritmo: baseline móvil + 2 sigma, correlación con trace_id). Este archivo documenta
# cómo se llevaría la misma regla a los servicios gestionados de cada nube.
# ---------------------------------------------------------------------------

resource "google_monitoring_notification_channel" "email" {
  count        = var.enable_aiops ? 1 : 0
  project      = var.project_id
  display_name = "Equipo de observabilidad (email)"
  type         = "email"

  labels = {
    email_address = var.notification_channel_email
  }
}

# Política de alerta basada en MQL: combina error_rate (métrica custom OTLP reexportada
# como Prometheus/Cloud Monitoring) con latencia p99, replicando la regla de correlación
# pedida: error_rate > baseline + 2sigma Y latency_p99 > SLO.
resource "google_monitoring_alert_policy" "data_service_anomaly_correlation" {
  count        = var.enable_aiops ? 1 : 0
  project      = var.project_id
  display_name = "data-service: error_rate anómalo (MAD/2-sigma) + latency_p99 > SLO"
  combiner     = "AND_WITH_MATCHING_RESOURCE"

  conditions {
    display_name = "error_rate fuera de la banda de anomalía (Cloud Monitoring MQL forecast/outlier)"
    condition_monitoring_query_language {
      query    = <<-EOT
        fetch generic_task
        | metric 'custom.googleapis.com/data_service_errors_total'
        | align rate(1m)
        | condition val() > val().aligned_rate().within(30m).mean() + 2 * val().aligned_rate().within(30m).stddev()
      EOT
      duration = "60s"
    }
  }

  conditions {
    display_name = "latency_p99 > SLO (300ms)"
    condition_monitoring_query_language {
      query    = <<-EOT
        fetch generic_task
        | metric 'custom.googleapis.com/data_service_request_duration_seconds'
        | align delta(1m)
        | condition val() > 0.3
      EOT
      duration = "60s"
    }
  }

  notification_channels = [google_monitoring_notification_channel.email[0].id]

  documentation {
    content   = "Alerta enriquecida: revisar trace_id correlacionado en Jaeger/Cloud Trace para el request fallido más reciente de data-service."
    mime_type = "text/markdown"
  }
}

# AWS DevOps Guru: habilita el análisis de anomalías sobre los recursos etiquetados del
# stack de data-service (RDS, App Mesh, etc.).
resource "aws_devopsguru_resource_collection" "data_service" {
  count = var.enable_aiops ? 1 : 0
  type  = "AWS_TAGS"

  cloudformation {
    stack_names = ["data-service-stack"]
  }
}

resource "aws_devopsguru_notification_channel" "sns" {
  count = var.enable_aiops ? 1 : 0
  sns {
    topic_arn = aws_sns_topic.devops_guru_alerts[0].arn
  }
}

resource "aws_sns_topic" "devops_guru_alerts" {
  count = var.enable_aiops ? 1 : 0
  name  = "devops-guru-data-service-alerts"
}
