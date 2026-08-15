# IaC (Terraform) — OTel Collector en GCP Cloud Run

> **Nota de alcance**: este código no fue aplicado contra un proyecto real de GCP
> (el entorno de desarrollo no tenía credenciales de nube disponibles). Es código
> Terraform válido y completo, listo para `terraform init/plan/apply` una vez se
> cuente con un proyecto de GCP y credenciales (`gcloud auth application-default login`
> o una Service Account con los roles `roles/run.admin`, `roles/iam.serviceAccountAdmin`,
> `roles/secretmanager.admin`, `roles/artifactregistry.admin` y, si `enable_gke_backends
> = true`, `roles/container.admin`).

## Qué provisiona

1. Habilita las APIs necesarias (`run`, `secretmanager`, `artifactregistry`, `container`).
2. Sube `../otel-collector/otel-collector-config.yaml` a Secret Manager.
3. Crea una Service Account dedicada para el Collector con acceso de solo lectura al secreto.
4. Despliega el OTel Collector (`otel/opentelemetry-collector-contrib`) en **Cloud Run v2**,
   con el receiver OTLP gRPC como puerto de ingreso.
5. (Opcional, `enable_gke_backends = true`) Crea un clúster **GKE Autopilot** donde se
   despliegan Jaeger, Prometheus y Grafana vía Helm (ver `../helm`).

## Uso

```bash
cp terraform.tfvars.example terraform.tfvars
# editar project_id, region, etc.

terraform init
terraform plan
terraform apply
```

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
