# Despliegue de los backends de observabilidad (Fase 2/3) vía Helm en GKE

Este directorio complementa `../terraform` (que aprovisiona el clúster GKE Autopilot
opcional vía `enable_gke_backends = true`, además del OTel Collector en Cloud Run).
Aquí se despliegan los componentes **con estado** (Jaeger, Prometheus, Grafana) usando
los charts públicos oficiales, sobreescribiendo únicamente los `values.yaml` con la
configuración equivalente a la usada en `../docker-compose.yml` para desarrollo local.

## Prerrequisitos

```bash
gcloud container clusters get-credentials otel-observability-backends --region <region>
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

## 1. Jaeger

```bash
helm upgrade --install jaeger jaegertracing/jaeger \
  --namespace observability --create-namespace \
  -f values-jaeger.yaml
```

`values-jaeger.yaml` despliega Jaeger en modo *all-in-one* con almacenamiento Badger
respaldado por un `PersistentVolumeClaim` (suficiente para una demo/entrega académica;
para producción real se recomienda Elasticsearch u otro backend soportado). Expone:
- `4317`/`4318` (OTLP gRPC/HTTP) como destino del exporter `otlp/jaeger` del Collector.
- `16686` (Jaeger UI) vía `Service` tipo `LoadBalancer` o `Ingress`.

## 2. Prometheus

```bash
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace observability \
  -f values-prometheus.yaml
```

`values-prometheus.yaml` agrega un `scrape_config` adicional apuntando a la URL pública
de Cloud Run del OTel Collector (salida `otel_collector_url` de Terraform), vía HTTPS.

## 3. Grafana

```bash
helm upgrade --install grafana grafana/grafana \
  --namespace observability \
  -f values-grafana.yaml
```

`values-grafana.yaml` provisiona automáticamente los mismos datasources
(Prometheus, Jaeger, Loki) y el dashboard de 6 paneles definidos en
`../grafana/provisioning`, usando `dashboardsConfigMaps`/`datasources` del chart.

## Conectar el Collector (Cloud Run) con Jaeger (GKE)

Como el Collector corre en Cloud Run y Jaeger en GKE, hay dos opciones:

1. **Más simple (demo)**: exponer el `Service` de Jaeger OTLP (`4317`) con un
   `LoadBalancer` de IP pública y actualizar el exporter `otlp/jaeger` del
   `otel-collector-config.yaml` (subido a Secret Manager por Terraform) con esa IP.
2. **Recomendada (producción)**: usar un [Serverless VPC Connector] + IP interna del
   `Service` de Jaeger, para que el tráfico entre Cloud Run y GKE no salga a Internet.

[Serverless VPC Connector]: https://cloud.google.com/run/docs/configuring/vpc-connectors
