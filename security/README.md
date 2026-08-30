# Módulo C — Network & Security Observability

Este directorio contiene la evidencia funcional local de observabilidad de seguridad,
equivalente al VPC Flow Logs + Security Command Center (GCP) / Security Hub (AWS) que
se documenta (sin aplicar) en `../terraform/network_security.tf`.

## Golden Signals de Seguridad (dashboard Grafana)

Panel provisionado automáticamente: **Grafana → carpeta Observabilidad → "Golden Signals
de Seguridad"** (`../grafana/provisioning/dashboards/json/security-golden-signals.json`).

| Golden signal | Fuente real (local) | Equivalente en la nube |
|---|---|---|
| Intentos de autenticación fallidos | `data_service_auth_failed_total` / `data_service_auth_success_total` (contadores OTel expuestos por `data-service`) | Cloud Audit Logs (GCP) / CloudTrail + GuardDuty (AWS) |
| Tráfico N-S / E-W | Métricas nativas de los sidecars Envoy (`envoy_http_downstream_rq_total`, `envoy_cluster_upstream_rq_completed`) | Cloud Service Mesh telemetry / AWS App Mesh + VPC Flow Logs |
| CVEs activos | Escaneo Trivy de las imágenes propias, publicado en Prometheus Pushgateway (`image_active_cves`) | Security Command Center (GCP) / Security Hub + Inspector (AWS) |

## Cómo generar evidencia

1. Con el stack levantado (`docker compose up -d --build`), generar intentos de login:
   ```bash
   python security/simulate_auth_traffic.py --target http://localhost:8003 --requests 200 --fail-rate 0.4
   ```
2. Generar tráfico normal con k6 (`../k6/transfer-load-test.js`) para poblar las métricas
   N-S/E-W de Envoy (el tráfico de `service-a` hacia `service-b`/`data-service` pasa por los
   sidecars `envoy-service-b`/`envoy-data-service`, ver `SERVICE_B_URL`/`DATA_SERVICE_URL` en
   `../docker-compose.yml`).
3. Escanear las imágenes con Trivy (requiere tenerlo instalado) y publicar CVEs activos:
   ```bash
   python security/scan_images.py
   ```
4. Abrir Grafana → Observabilidad → "Golden Signals de Seguridad".

Evidencia real capturada el 2026-08-30 (ver `../screenshots/18_grafana_security_cves_completo.png`):
los 5 paneles con datos reales — auth fallidos/exitosos, tráfico N-S/E-W del mesh, 5xx y CVEs
activos por imagen (3 CRITICAL, 22 HIGH, 68 MEDIUM, 77 LOW por cada una de las 3 imágenes
propias, todas basadas en `python:3.11-slim`).

## Por qué no se aplicó contra GCP/AWS reales

Igual que el resto del repositorio (ver `../README.md` y `../terraform/README.md`), VPC
Flow Logs, Security Command Center y Security Hub requieren un proyecto GCP/cuenta AWS
activos con permisos de organización (SCC) que no fueron aprovisionados para esta entrega.
El IaC completo queda en `../terraform/network_security.tf`, gated por
`enable_network_security = true`.
