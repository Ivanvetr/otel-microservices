# ---------------------------------------------------------------------------
# Módulo A: GCP Cloud SQL (Postgres) para data-service.
#
# Gated por enable_data_service_databases: en la entrega de este laboratorio se trabajó
# 100% local (ver ../docker-compose.yml, contenedor `postgres`) porque no se aplicó
# Terraform contra un proyecto real de GCP (mismo criterio documentado en ../README.md
# para el resto del stack). Este archivo sí queda listo para `terraform apply` en un
# proyecto real: solo requiere poner enable_data_service_databases = true.
# ---------------------------------------------------------------------------

resource "google_sql_database_instance" "data_service_cloudsql" {
  count = var.enable_data_service_databases ? 1 : 0

  project             = var.project_id
  name                = "data-service-cloudsql"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = false

  settings {
    tier = var.cloudsql_tier

    ip_configuration {
      ipv4_enabled = true
    }

    backup_configuration {
      enabled = true
    }

    # Golden signal de seguridad (Módulo C): registra intentos de conexión/autenticación
    # fallidos en Cloud Logging para el dashboard de seguridad.
    database_flags {
      name  = "log_connections"
      value = "on"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "otel_demo" {
  count    = var.enable_data_service_databases ? 1 : 0
  project  = var.project_id
  name     = "otel_demo"
  instance = google_sql_database_instance.data_service_cloudsql[0].name
}

resource "google_sql_user" "otel_app_user" {
  count    = var.enable_data_service_databases ? 1 : 0
  project  = var.project_id
  name     = "otel"
  instance = google_sql_database_instance.data_service_cloudsql[0].name
  password = var.cloudsql_db_password
}
