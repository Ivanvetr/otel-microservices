# ---------------------------------------------------------------------------
# Módulo A: AWS RDS (Postgres) para data-service — segunda nube requerida por la actividad.
#
# Igual que cloudsql.tf: gated por enable_data_service_databases (default false). El
# equivalente funcional local es el contenedor `postgres-aws` en ../docker-compose.yml.
# ---------------------------------------------------------------------------

resource "aws_db_subnet_group" "data_service" {
  count      = var.enable_data_service_databases ? 1 : 0
  name       = "data-service-rds-subnet-group"
  subnet_ids = data.aws_subnets.default[0].ids
}

# Compartidos con network_security.tf (VPC Flow Logs) -> gated por cualquiera de los dos flags.
data "aws_vpc" "default" {
  count   = (var.enable_data_service_databases || var.enable_network_security) ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = (var.enable_data_service_databases || var.enable_network_security) ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

resource "aws_security_group" "rds_data_service" {
  count       = var.enable_data_service_databases ? 1 : 0
  name        = "data-service-rds-sg"
  description = "Acceso Postgres desde data-service (Módulo A)"
  vpc_id      = data.aws_vpc.default[0].id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"] # restringir a la VPC/mesh en un despliegue real
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "data_service_rds" {
  count      = var.enable_data_service_databases ? 1 : 0
  identifier = "data-service-rds"

  engine         = "postgres"
  engine_version = "16.4"
  instance_class = var.rds_instance_class

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = "rds_demo"
  username = "otel"
  password = var.rds_db_password

  db_subnet_group_name   = aws_db_subnet_group.data_service[0].name
  vpc_security_group_ids = [aws_security_group.rds_data_service[0].id]

  # Golden signal de seguridad (Módulo C): habilita exportación de logs de Postgres
  # (incluye intentos de conexión fallidos) hacia CloudWatch Logs.
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  skip_final_snapshot = true
  publicly_accessible  = false
  deletion_protection  = false
}
