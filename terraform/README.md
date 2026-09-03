# IaC (Terraform) — OTel Collector, data-service (Cloud SQL/RDS), service mesh, AIOps y Network/Security en GCP + AWS

> **Nota de alcance**: este código no fue aplicado contra un proyecto real de GCP/cuenta de
> AWS (el entorno de desarrollo no tenía credenciales de nube disponibles). Es código
> Terraform válido y completo, listo para `terraform init/plan/apply` una vez se
> cuente con un proyecto de GCP y credenciales (`gcloud auth application-default login`
> o una Service Account con los roles `roles/run.admin`, `roles/iam.serviceAccountAdmin`,
> `roles/secretmanager.admin`, `roles/artifactregistry.admin` y, si `enable_gke_backends
> = true`, `roles/container.admin`) y credenciales de AWS (`aws configure` / variables
> `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`). La evidencia funcional de los módulos B-D
> de la actividad se generó 100% en local con Docker (ver README raíz y las carpetas
> `aiops/`, `security/`, `chaos/`).

## Qué provisiona

1. **Fase 2 (`main.tf`)**: habilita APIs, sube la config del Collector a Secret Manager,
   despliega el Collector en Cloud Run v2 y (opcional) un clúster GKE Autopilot para los
   backends con estado (ver `../helm`).
2. **Módulo A — `cloudsql.tf` / `rds.tf`**: Cloud SQL Postgres (GCP) y RDS Postgres (AWS)
   para `data-service`, gated por `enable_data_service_databases` (default `false`; el
   equivalente local son los contenedores `postgres`/`postgres-aws` en `../docker-compose.yml`).
3. **Módulo A — `service_mesh.tf`**: habilitación de Cloud Service Mesh (GCP, sobre el
   clúster GKE opcional) y un `aws_appmesh_mesh` (AWS). La observabilidad L7 equivalente y
   verificable en este entorno son los sidecars Envoy locales (`../envoy/*.yaml`).
4. **Módulo B — `aiops.tf`**: política de Cloud Monitoring Anomaly Detection (MQL,
   error_rate + latencia) y AWS DevOps Guru, gated por `enable_aiops`. El equivalente
   local funcional es `../aiops/anomaly_detector.py`.
5. **Módulo C — `network_security.tf`**: VPC + Flow Logs (GCP), alerta de tráfico E-W
   anómalo, VPC Flow Logs a CloudWatch (AWS), Security Hub (AWS) y notificación de
   Security Command Center (GCP), gated por `enable_network_security`. El equivalente
   local funcional está en `../security/`.

## Uso

```bash
cp terraform.tfvars.example terraform.tfvars
# editar project_id, region, aws_region, y los enable_* según lo que se vaya a aplicar

terraform init
terraform plan
terraform apply
```

Los flags `enable_data_service_databases`, `enable_network_security` y `enable_aiops`
están en `false` por defecto para que `terraform plan` no intente crear recursos con costo
en una cuenta real sin decisión explícita del equipo.


## Decisiones de diseño relevantes para el informe técnico

- **Cloud Run para el Collector, GKE para los backends**: el Collector no guarda estado
  entre requests (es un pipeline de transformación), por lo que Cloud Run (stateless,
  scale-to-zero, sin gestión de nodos) es la opción de menor costo y operación. Jaeger,
  Prometheus y Grafana sí requieren `PersistentVolumeClaim`s (traces, series temporales,
  dashboards), un patrón que Cloud Run no soporta de forma nativa — de ahí GKE Autopilot.
- **Configuración vía Secret Manager, no `--set-env-vars`**: el YAML del Collector es
  demasiado grande y sensible (puede incluir endpoints internos) para pasarlo como
  variable de entorno plana; Secret Manager permite auditoría de acceso y rotación.
- **`allow_unauthenticated = false` por defecto**: en producción, los servicios que
  envían OTLP al Collector deberían autenticarse vía IAM (identidad de servicio a
  servicio), no exponer el receiver públicamente.
