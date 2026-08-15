# Observabilidad end-to-end con OpenTelemetry — service-a / service-b

Proyecto de la Maestría en Arquitectura de Software (Universidad de La Sabana) — curso
*Observabilidad en ambientes productivos*. Instrumenta dos microservicios (Python/FastAPI)
con dependencia HTTP + acceso a base de datos usando el SDK de OpenTelemetry, despliega un
OTel Collector, y correlaciona trazas, métricas y logs en Jaeger/Prometheus/Grafana/Loki.

📄 **Informe técnico completo**: [`docs/Informe_Tecnico_Observabilidad_OTel.pdf`](docs/Informe_Tecnico_Observabilidad_OTel.pdf)
(arquitectura, decisiones de diseño, evidencia de propagación W3C TraceContext y análisis de
overhead con datos reales de benchmark).

## Estructura del repositorio

```
service-a/            Orquestador de transferencias (FastAPI + OTel SDK)
service-b/             Lógica de cuentas + PostgreSQL (FastAPI + SQLAlchemy + OTel SDK)
otel-collector/        Configuración del OTel Collector, Prometheus y Loki
grafana/provisioning/  Datasources (Prometheus/Jaeger/Loki) y dashboard de 6 paneles
docker-compose.yml      Stack completo local (Postgres, Collector, Jaeger, Prometheus, Grafana, Loki)
terraform/              IaC para desplegar el Collector en GCP Cloud Run
helm/                   Charts/values para desplegar Jaeger, Prometheus y Grafana en GKE
k6/                     Script de carga (Fase 4)
benchmark/              Versiones sin instrumentar (baseline) + resultados del benchmark
screenshots/            Capturas reales de Jaeger UI y Prometheus
docs/                   Informe técnico PDF + evidencia de correlación trace_id
```

## Cómo levantar el stack (Docker)

Requiere Docker y Docker Compose. Todas las imágenes son públicas (Docker Hub).

```bash
docker compose up -d --build
```

Servicios expuestos:

| Servicio         | URL                              |
|------------------|-----------------------------------|
| service-a        | http://localhost:8001              |
| service-b        | http://localhost:8002              |
| Jaeger UI        | http://localhost:16686             |
| Prometheus       | http://localhost:9090              |
| Grafana          | http://localhost:3000 (anónimo, rol Admin) |
| Loki             | http://localhost:3100              |
| OTel Collector   | :4317 (OTLP gRPC), :4318 (OTLP HTTP), :8888/:8889 (métricas) |

Generar tráfico de prueba:

```bash
curl -X POST http://localhost:8001/transfer \
  -H "Content-Type: application/json" \
  -d '{"from_account":"acc-001","to_account":"acc-002","amount":150.50}'
```

El dashboard de Grafana se auto-provisiona (carpeta **Observabilidad**, 6 paneles) al primer
arranque. Para explorar la correlación logs↔trazas: **Explore → Loki**, filtrar por
`{service_name="service-a"}` y hacer clic en el link "TraceID" que aparece junto a cada línea
que contenga un `trace_id`.

## Benchmark de overhead (Fase 4)

```bash
cd k6
TARGET_URL=http://localhost:8001 k6 run --summary-export=resultado.json transfer-load-test.js
```

Los resultados completos de la comparación con/sin instrumentación están en
[`benchmark/results/overhead_comparison.md`](benchmark/results/overhead_comparison.md).

## Despliegue en la nube

Ver [`terraform/README.md`](terraform/README.md) (OTel Collector en Cloud Run) y
[`helm/README.md`](helm/README.md) (Jaeger/Prometheus/Grafana en GKE vía Helm). Este código
no fue aplicado contra un proyecto real de GCP — ver la sección 7 del informe técnico para el
detalle de por qué y cómo se validó igualmente el pipeline completo con datos reales.

## Notas de reproducibilidad

Todas las trazas, logs, métricas, capturas de pantalla y resultados de benchmark incluidos en
el informe técnico y en `benchmark/results/` provienen de una ejecución real de este stack
(no son datos ilustrativos). El detalle de cómo se generaron está en la sección 7 del informe.
