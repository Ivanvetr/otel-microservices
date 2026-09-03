# Observabilidad end-to-end con AIOps y resiliencia — GCP y AWS

Proyecto de la Maestría en Arquitectura de Software (Universidad de La Sabana) — curso
*Observabilidad en ambientes productivos*. Laboratorio integrador (Actividad 3) que extiende
el laboratorio anterior (2.2, dos microservicios) hacia un sistema observable de nivel
producción con **tres microservicios**, **AIOps**, **observabilidad de red y seguridad**,
**chaos engineering** y **reporte de madurez**, sobre GCP y AWS.

Equipo: Leonardo Pérez Ramírez, Ivan Felipe Vera Triana, Juan Felipe Gonzalez Ortiz.

📄 **Reporte ejecutivo (Actividad 3)**: [`docs/Reporte_Ejecutivo_Actividad3.pdf`](docs/Reporte_Ejecutivo_Actividad3.pdf)
(arquitectura completa, evidencia real de los 5 módulos y análisis de madurez). Generado con
`python3 docs/build_executive_report.py` a partir de los datos y capturas reales del proyecto.

📄 **Informe técnico previo (laboratorio 2.2)**: [`docs/Informe_Tecnico_Observabilidad_OTel.pdf`](docs/Informe_Tecnico_Observabilidad_OTel.pdf).

> **Alcance real vs. documentado**: todo lo que requiere una cuenta de nube activa (Cloud SQL,
> RDS, service mesh gestionado, Cloud Monitoring Anomaly Detection, DevOps Guru, VPC Flow
> Logs, Security Command Center, Security Hub) quedó **completamente implementado como IaC en
> `terraform/`** pero sin aplicar contra un proyecto/cuenta real. La evidencia funcional y
> verificable de cada módulo se generó **100% en local con Docker**, con el mismo código de
> instrumentación y los mismos algoritmos que se aplicarían en la nube real (ver la tabla de
> equivalencias en cada README de módulo).

## Arquitectura (resumen por módulo de la actividad)

| Módulo | Qué se implementó | Dónde |
|---|---|---|
| A — Arquitectura observable completa | 3er microservicio `data-service` (Cloud SQL + RDS simulados), OTel DB Semantic Conventions, service mesh L7 (sidecars Envoy) | `data-service/`, `envoy/`, `terraform/cloudsql.tf`, `terraform/rds.tf`, `terraform/service_mesh.tf` |
| B — AIOps | Detección de anomalías (baseline móvil + 2σ) con correlación de `trace_id`, comparación vs. umbrales estáticos | `aiops/`, `terraform/aiops.tf` |
| C — Network & Security Observability | Golden signals de seguridad (auth fallidos, tráfico N-S/E-W, CVEs), VPC Flow Logs/SCC/Security Hub (IaC) | `security/`, `terraform/network_security.tf`, dashboard `security-golden-signals.json` |
| D — Chaos Engineering | 2 experimentos (latencia +200ms en service-b, error rate 10% en data-service) + medición de MTTD | `chaos/` |
| E — Reporte de madurez | Autoevaluación 8 dominios (1-5) + roadmap 3 meses | `docs/madurez_observabilidad.md` |

## Estructura del repositorio

```
service-a/              Orquestador de transferencias (FastAPI + OTel SDK)
service-b/               Lógica de cuentas + PostgreSQL (FastAPI + SQLAlchemy + OTel SDK)
data-service/            3er microservicio (Módulo A): audit log en Cloud SQL/RDS simulados, auth, chaos toggle
envoy/                   Configuración de los sidecars Envoy (service mesh L7 local)
aiops/                   Detector de anomalías + correlación con trace_id (Módulo B)
security/                Scripts de evidencia de seguridad: Trivy->Pushgateway, tráfico de auth (Módulo C)
chaos/                   Script y metodología de los experimentos de caos + medición de MTTD (Módulo D)
otel-collector/          Config del Collector, Prometheus, reglas de alerta y Alertmanager, Loki
grafana/provisioning/    Datasources + dashboards (Observabilidad, Golden Signals de Seguridad)
docker-compose.yml       Stack completo local (todos los servicios de arriba)
terraform/               IaC completo GCP+AWS (Collector, Cloud SQL/RDS, service mesh, AIOps, network/security)
helm/                    Charts/values para desplegar Jaeger, Prometheus y Grafana en GKE
k6/                      Script de carga
benchmark/               Versiones sin instrumentar (baseline) + resultados del benchmark
screenshots/             Capturas reales de Jaeger UI y Prometheus
docs/                    Informe técnico previo + reporte de madurez de observabilidad
```

## Cómo levantar el stack (Docker)

Requiere Docker y Docker Compose.

```bash
docker compose up -d --build
```

Servicios expuestos:

| Servicio | URL |
|---|---|
| service-a | http://localhost:8001 |
| service-b | http://localhost:8002 |
| data-service | http://localhost:8003 |
| Envoy (sidecar service-b) | http://localhost:8102 (admin/stats: 9911) |
| Envoy (sidecar data-service) | http://localhost:8103 (admin/stats: 9912) |
| aiops-anomaly-detector | http://localhost:8500 (`/summary`) |
| Jaeger UI | http://localhost:16686 |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Pushgateway | http://localhost:9091 |
| Grafana | http://localhost:3000 (anónimo, rol Admin) |
| Loki | http://localhost:3100 |
| OTel Collector | :4317 (OTLP gRPC), :4318 (OTLP HTTP), :8888/:8889 (métricas) |

Generar tráfico de prueba (transferencia completa a través de los 3 microservicios):

```bash
curl -X POST http://localhost:8001/transfer \
  -H "Content-Type: application/json" \
  -d '{"from_account":"acc-001","to_account":"acc-002","amount":150.50}'
```

El dashboard de Grafana se auto-provisiona (carpeta **Observabilidad**, dashboards
"Observabilidad OTel" y "Golden Signals de Seguridad") al primer arranque. Para explorar la
correlación logs↔trazas: **Explore → Loki**, filtrar por `{service_name="service-a"}` y hacer
clic en el link "TraceID" que aparece junto a cada línea que contenga un `trace_id`.

## Módulo B — AIOps

```bash
curl http://localhost:8500/summary
```

Muestra el conteo de alertas correlacionadas (baseline+2σ + SLO) vs. alertas de umbral
estático, y el `noise_reduction_pct` calculado. Detalle en [`aiops/README.md`](aiops/README.md).

## Módulo C — Network & Security Observability

```bash
python security/simulate_auth_traffic.py --requests 200 --fail-rate 0.4
python security/scan_images.py   # requiere Trivy instalado
```

Ver dashboard "Golden Signals de Seguridad" en Grafana. Detalle en
[`security/README.md`](security/README.md).

## Módulo D — Chaos Engineering

```bash
pip install -r chaos/requirements.txt
python chaos/run_chaos_experiment.py latency --duration 180
python chaos/run_chaos_experiment.py error-rate --duration 180
```

Metodología completa y análisis de SLO/error budget en
[`chaos/chaos_experiments.md`](chaos/chaos_experiments.md).

## Módulo E — Reporte de madurez

Ver [`docs/madurez_observabilidad.md`](docs/madurez_observabilidad.md).

## Evidencia visual (capturas reales, stack corriendo el 2026-08-30)

| Captura | Contenido |
|---|---|
| [`screenshots/11_grafana_observabilidad_dashboard.png`](screenshots/11_grafana_observabilidad_dashboard.png) | Dashboard principal de observabilidad (SLIs) |
| [`screenshots/12_grafana_security_golden_signals.png`](screenshots/12_grafana_security_golden_signals.png) | Golden Signals de Seguridad (Módulo C) con datos reales |
| [`screenshots/13_jaeger_trace_transfer_3_servicios.png`](screenshots/13_jaeger_trace_transfer_3_servicios.png) | Trazas con los 3 microservicios (`service-a`, `service-b`, `data-service`) |
| [`screenshots/14_jaeger_trace_correlacionada_aiops.png`](screenshots/14_jaeger_trace_correlacionada_aiops.png) | Traza con error correlacionada por `aiops-anomaly-detector` (Módulo B) |
| [`screenshots/15_alertmanager_alertas.png`](screenshots/15_alertmanager_alertas.png) | Alertmanager (sin alertas activas tras finalizar los experimentos) |
| [`screenshots/16_prometheus_alerting_rules.png`](screenshots/16_prometheus_alerting_rules.png) | Reglas de alerta de SLO/umbral estático cargadas (Módulos B/D) |
| [`screenshots/17_prometheus_targets_actualizado.png`](screenshots/17_prometheus_targets_actualizado.png) | Targets scrapeados: sidecars Envoy, Collector, Pushgateway |
| [`screenshots/18_grafana_security_cves_completo.png`](screenshots/18_grafana_security_cves_completo.png) | Golden Signals de Seguridad completo: auth, tráfico N-S/E-W del mesh y CVEs activos (Trivy real) |

## Benchmark de overhead (laboratorio 2.2, se conserva como base)

```bash
cd k6
TARGET_URL=http://localhost:8001 k6 run --summary-export=resultado.json transfer-load-test.js
```

Resultados completos en [`benchmark/results/overhead_comparison.md`](benchmark/results/overhead_comparison.md).

## Despliegue en la nube

Ver [`terraform/README.md`](terraform/README.md) (Collector, Cloud SQL/RDS, service mesh,
AIOps, network/security en GCP+AWS) y [`helm/README.md`](helm/README.md) (Jaeger/Prometheus/
Grafana en GKE vía Helm). Este código no fue aplicado contra proyectos/cuentas reales — ver
la nota de alcance al inicio de este README y la sección 7 del informe técnico previo
(laboratorio 2.2) para el detalle de por qué y cómo se validó igualmente el pipeline completo
con datos reales del stack local.

## Notas de reproducibilidad

Los resultados numéricos de los experimentos de caos (`chaos/results/`) y de la comparación
AIOps vs. umbrales estáticos (`aiops/results/comparison_summary.json`) deben generarse
ejecutando el stack local y los scripts correspondientes — no están pre-rellenados con datos
inventados. El detalle de cómo se generaron las trazas/logs/métricas del laboratorio 2.2 está
en la sección 7 del informe técnico previo ([`docs/Informe_Tecnico_Observabilidad_OTel.pdf`](docs/Informe_Tecnico_Observabilidad_OTel.pdf)).
