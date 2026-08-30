# Módulo E — Reporte de Madurez de Observabilidad

Autoevaluación de este proyecto contra el **Observability Foundation Blueprint** (8 dominios),
escala de madurez 1 (inicial) – 5 (optimizado). Elaborado por el equipo: Leonardo Pérez Ramírez,
Ivan Felipe Vera Triana, Juan Felipe Gonzalez Ortiz.

## Escala de referencia

| Nivel | Descripción |
|---|---|
| 1 — Inicial | Ad-hoc, reactivo, sin instrumentación sistemática. |
| 2 — Repetible | Instrumentación básica presente pero manual/parcial, sin estandarización. |
| 3 — Definido | Prácticas estandarizadas y documentadas, aplicadas de forma consistente. |
| 4 — Gestionado | Medido cuantitativamente, con SLOs/alertas accionables y automatización. |
| 5 — Optimizado | Mejora continua automatizada, AIOps maduro, integrado en el ciclo de vida completo. |

## Autoevaluación por dominio

| # | Dominio | Nivel (1-5) | Evidencia |
|---|---|---|---|
| 1 | **Tres pilares (traces/metrics/logs)** | **4** | Los 3 microservicios (service-a, service-b, data-service) están instrumentados con el SDK de OTel; trazas correlacionadas end-to-end (W3C TraceContext), métricas custom de negocio, logs JSON con `trace_id`/`span_id` correlacionados en Loki↔Jaeger. Falta: sampling adaptativo y SLO-based sampling para producción a escala. |
| 2 | **OpenTelemetry / instrumentación** | **4** | Auto-instrumentación (FastAPI, httpx, SQLAlchemy) + spans manuales de negocio + atributos de OTel DB Semantic Conventions (`db.system`, `db.operation`) y atributos de nube (`cloud.provider`, `cloud.platform`) en `data-service`. Falta: propagación de baggage y semantic conventions de mensajería/colas (no aplica aún, no hay async messaging en la arquitectura). |
| 3 | **AIOps (detección de anomalías)** | **3** | `aiops/anomaly_detector.py` implementa baseline móvil + 2σ con correlación de `trace_id`, y se comparó cuantitativamente contra una regla de umbral estático en una ejecución real (2026-08-30): **7 alertas correlacionadas vs. 21 de umbral estático**, una **reducción de ruido del 66.7%** (`aiops/results/comparison_summary.json`), con `trace_id` real verificado en Jaeger para cada alerta. Limitación: el algoritmo (media+2σ) es más simple que los modelos de Cloud Monitoring Anomaly Detection / DevOps Guru (ARIMA, detección estacional); no hay modelos entrenados sobre series históricas largas. |
| 4 | **Network Observability** | **2** | Observabilidad L7 real vía sidecars Envoy (métricas de requests, retries, latencia, tráfico N-S/E-W) 100% funcional en local. VPC Flow Logs de GCP/AWS solo quedaron documentados en Terraform (`network_security.tf`, `enable_network_security=false`) porque no se aprovisionó un proyecto/cuenta real. |
| 5 | **Security Observability** | **2** | Golden signals de seguridad (auth fallidos, tráfico N-S/E-W, CVEs vía Trivy+Pushgateway) funcionan localmente con datos reales. Security Command Center / Security Hub quedaron solo como IaC documentado (requieren organización GCP y cuenta AWS activas con permisos elevados). |
| 6 | **DataOps** (pipelines de datos de observabilidad) | **3** | Pipeline único y estandarizado: OTLP → OTel Collector (batch, memory_limiter, resource enrichment) → Jaeger/Prometheus/Loki, igual para los 3 microservicios y para las métricas de Envoy/Trivy. Falta: versionado/schema registry de métricas custom, y políticas de retención/tiering diferenciadas por costo. |
| 7 | **SRE (SLOs / error budgets / MTTD)** | **3** | SLOs explícitos (`p99 < 300ms`, `error_rate < 8%`) con reglas de alerta dedicadas, validadas empíricamente el 2026-08-30 con `chaos/run_chaos_experiment.py`: MTTD de **26.7s** para el experimento de latencia (cumple el objetivo de 120s con amplio margen) pero **139.3s** para el de error rate (no cumple, por bajo volumen de tráfico hacia `data-service`). Este hallazgo real es valioso: revela que el MTTD depende del tráfico del servicio, no solo de la config. de alertas. Falta: error budget policy formal (qué acción se dispara automáticamente al agotarse el budget) y burn-rate alerting multiventana (1h/6h) en vez de umbral simple. |
| 8 | **Cultura/Procesos (runbooks, on-call, colaboración)** | **2** | Documentación técnica extensa (READMEs por módulo, informe técnico previo) y alertas con contexto accionable (trace_id, jaeger_url). Falta: runbooks formales por alerta, rotación on-call, postmortems sin culpa y game days recurrentes (los 2 experimentos de este módulo son un primer game day, no un proceso recurrente). |

**Madurez promedio actual: 2.9 / 5** (dominios técnicos de instrumentación más maduros que los
de gobierno/proceso y observabilidad de red/seguridad en la nube real).

## Roadmap de mejora — próximos 3 meses

| Mes | Objetivo | Acciones concretas |
|---|---|---|
| **Mes 1** | Cerrar la brecha de MTTD encontrada en el experimento de error rate (139.3s > 120s) | Reducir la ventana de `rate()` de 1m a 30s para servicios de bajo tráfico como `data-service`, o generar tráfico sintético continuo hacia sus endpoints (no solo el derivado de `/transfer`), y re-validar con `chaos/run_chaos_experiment.py`. |
| **Mes 1** | Elevar Network & Security Observability de 2→3 | Aprovisionar un proyecto GCP y cuenta AWS de sandbox reales; aplicar `terraform/network_security.tf` con `enable_network_security=true`; validar VPC Flow Logs y Security Hub con tráfico real generado por k6. |
| **Mes 1** | Elevar Cultura/Procesos de 2→3 | Escribir runbooks por cada alerta activa (`TransferLatencySLOBreach`, `DataServiceErrorRateSLOBreach`, `AnomalyCorrelatedErrorRateLatency`); definir rotación on-call simulada dentro del equipo. |
| **Mes 2** | Elevar AIOps de 3→4 | Reemplazar el baseline media+2σ por un modelo con estacionalidad (p. ej. Holt-Winters o STL) sobre series históricas de ≥30 días; aplicar `terraform/aiops.tf` en GCP real para comparar contra Cloud Monitoring Anomaly Detection. |
| **Mes 2** | Elevar SRE de 3→4 | Implementar burn-rate alerting multiventana (Google SRE workbook: 1h+5m y 6h+30m) y una política formal de error budget (congelar despliegues si el budget mensual cae bajo 10%). |
| **Mes 3** | Elevar DataOps de 3→4 | Versionar el esquema de métricas custom (naming convention + CI check), añadir retención diferenciada (traces de error 30 días, traces exitosos 3 días) y exportar métricas de costo del pipeline de observabilidad. |
| **Mes 3** | Consolidar Tres Pilares / OTel en 4→5 | Sampling basado en cola (tail-based sampling) en el Collector, priorizando trazas con error o latencia alta; añadir `db.system.name` y convenciones de nubes actualizadas conforme evolucione el semconv de OTel. |

## Conclusión

El proyecto demuestra una arquitectura observable sólida y coherente en los tres pilares y en
OpenTelemetry (nivel 4), con AIOps y SRE en un nivel intermedio (definido, nivel 3) gracias a
la implementación funcional local. Los dominios de observabilidad de red/seguridad en la nube
real y de cultura/procesos son los que requieren mayor inversión en los próximos 3 meses, ya
que dependen de acceso a proyectos GCP/AWS reales y de la adopción de procesos organizacionales
(runbooks, on-call, postmortems) que van más allá de la herramienta.
